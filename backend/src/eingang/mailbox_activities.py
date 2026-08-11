"""Activity of MailboxPollWorkflow: the optional IMAP intake (HANDOFF "Temporal workflows").

`fetch_mail` reads the unseen messages of the configured mailbox and stores every PDF or XML
attachment as a document of the organisation `MAILBOX_ORG_SLUG`, with the same checks as an
upload (size limit, type by content, DOCTYPE refused, exact duplicates skipped). A message is
fetched with BODY.PEEK[] and marked seen only after its attachments are stored, so a crash in
between leaves it unseen for the next poll, where its stored files are skipped as duplicates.
Logs carry counts and document IDs only, never addresses, subjects, file names or contents.
"""

import email
import hashlib
import imaplib
import logging
from collections.abc import Callable, Iterator
from email import policy
from email.message import EmailMessage
from email.utils import parseaddr
from uuid import UUID

from django.db import close_old_connections, transaction
from temporalio import activity

from accounts.models import Organization
from eingang.config import Settings, get_settings
from eingang.problem import ProblemError
from eingang.temporal_errors import PermanentError
from eingang.workflows import contracts as c
from invoices.models import Document
from invoices.uploads import file_type, is_duplicate, store_document

logger = logging.getLogger(__name__)

MAILBOX = "INBOX"
SEEN = "\\Seen"
# Seconds a single IMAP socket operation may block.
IMAP_TIMEOUT = 30
# Messages handled per poll, so one run stays well inside its activity timeout; the rest
# wait for the next poll five minutes later.
MAX_MESSAGES_PER_POLL = 20
# A message larger than this cannot hold a usable attachment within the upload limit plus
# its base64 encoding and the other parts; it is marked seen without being downloaded.
MESSAGE_SIZE_FACTOR = 2
MESSAGE_OVERHEAD_BYTES = 256 * 1024


def _organization(settings: Settings) -> Organization:
    if not settings.MAILBOX_ENABLED:
        raise PermanentError("The mailbox intake is disabled (MAILBOX_ENABLED=false).")
    organization = Organization.objects.filter(slug=settings.MAILBOX_ORG_SLUG).first()
    if organization is None:
        raise PermanentError("No organisation has the slug set in MAILBOX_ORG_SLUG.")
    return organization


def _check(status: str, what: str) -> None:
    if status != "OK":
        raise imaplib.IMAP4.error(f"IMAP {what} failed")


def _unseen(imap: imaplib.IMAP4) -> list[str]:
    status, data = imap.uid("SEARCH", "UNSEEN")
    _check(status, "search")
    return [uid.decode("ascii") for uid in (data[0] or b"").split() if uid]


def _message_size(imap: imaplib.IMAP4, uid: str) -> int:
    status, data = imap.uid("FETCH", uid, "(RFC822.SIZE)")
    _check(status, "size fetch")
    first = data[0]
    line = first[0] if isinstance(first, tuple) else first
    text = line.decode("ascii", "replace") if isinstance(line, bytes) else str(line)
    marker = "RFC822.SIZE "
    if marker not in text:
        return 0
    digits = text.split(marker, 1)[1].split(")", 1)[0].split()[0]
    return int(digits) if digits.isdigit() else 0


def _message(imap: imaplib.IMAP4, uid: str) -> EmailMessage:
    # PEEK leaves the message unseen until its attachments are stored.
    status, data = imap.uid("FETCH", uid, "(BODY.PEEK[])")
    _check(status, "fetch")
    raw = next((part[1] for part in data if isinstance(part, tuple)), b"")
    message = email.message_from_bytes(raw, policy=policy.default)
    if not isinstance(message, EmailMessage):  # policy.default always builds EmailMessage
        raise TypeError("unexpected message class")
    return message


def _mark_seen(imap: imaplib.IMAP4, uid: str) -> None:
    status, _data = imap.uid("STORE", uid, "+FLAGS", f"({SEEN})")
    _check(status, "store")


def _sender(message: EmailMessage) -> str | None:
    address = parseaddr(str(message.get("From", "")))[1].strip()
    if "@" not in address or len(address) > 254:
        return None
    return address


def _attachments(message: EmailMessage) -> Iterator[tuple[str, bytes]]:
    """Every leaf part that is a named or explicit attachment, with its decoded bytes."""
    for part in message.walk():
        if part.is_multipart():
            continue
        name = part.get_filename()
        if not name and part.get_content_disposition() != "attachment":
            continue  # the message text itself
        payload = part.get_payload(decode=True)
        if isinstance(payload, bytes) and payload:
            yield name or "attachment", payload


def _store_attachments(organization: Organization, message: EmailMessage, limit: int) -> list[UUID]:
    sender = _sender(message)
    stored: list[UUID] = []
    with transaction.atomic():
        for name, data in _attachments(message):
            if len(data) > limit:
                logger.info("Mail attachment refused: larger than the upload limit")
                continue
            try:
                kind = file_type(data)
            except ProblemError:
                continue  # neither PDF nor a UBL/CII invoice (or an XML with a DOCTYPE)
            sha256 = hashlib.sha256(data).hexdigest()
            if is_duplicate(organization, sha256):
                logger.info("Mail attachment skipped: the organisation already has this file")
                continue
            document = store_document(
                organization,
                name,
                data,
                kind,
                sha256=sha256,
                source=Document.Source.EMAIL,
                actor=None,
                sender_email=sender,
            )
            stored.append(document.id)
    return stored


def _poll(imap: imaplib.IMAP4, organization: Organization, settings: Settings) -> list[UUID]:
    limit = settings.MAX_UPLOAD_BYTES
    largest_message = limit * MESSAGE_SIZE_FACTOR + MESSAGE_OVERHEAD_BYTES
    document_ids: list[UUID] = []
    for uid in _unseen(imap)[:MAX_MESSAGES_PER_POLL]:
        if _message_size(imap, uid) > largest_message:
            logger.info("Mail message refused: larger than any accepted attachment")
        else:
            document_ids += _store_attachments(organization, _message(imap, uid), limit)
        _mark_seen(imap, uid)
    return document_ids


def _connect(settings: Settings) -> imaplib.IMAP4:
    imap = imaplib.IMAP4_SSL(settings.MAILBOX_HOST, settings.MAILBOX_PORT, timeout=IMAP_TIMEOUT)
    try:
        imap.login(settings.MAILBOX_USER, settings.MAILBOX_PASSWORD)
    except imaplib.IMAP4.error as error:
        _logout(imap)
        # Wrong credentials stay wrong for the retries; the next poll tries again.
        raise PermanentError("The mailbox refused MAILBOX_USER/MAILBOX_PASSWORD.") from error
    try:
        status, _data = imap.select(MAILBOX)
        _check(status, "select")
    except imaplib.IMAP4.error:
        _logout(imap)
        raise
    return imap


def _logout(imap: imaplib.IMAP4) -> None:
    try:
        imap.logout()
    except (imaplib.IMAP4.error, OSError):
        logger.warning("IMAP logout failed")


@activity.defn(name=c.ACT_FETCH_MAIL)
def fetch_mail() -> c.MailboxResult:
    """Store the PDF and XML attachments of unseen messages; returns the new document IDs."""
    close_old_connections()
    settings = get_settings()
    organization = _organization(settings)
    imap = _connect(settings)
    try:
        document_ids = _poll(imap, organization, settings)
    finally:
        _logout(imap)
    if document_ids:
        logger.info(
            "Stored %d mail attachments",
            len(document_ids),
            extra={"document_ids": [str(document_id) for document_id in document_ids]},
        )
    return c.MailboxResult(document_ids=document_ids)


MAILBOX_ACTIVITIES: list[Callable[..., object]] = [fetch_mail]
