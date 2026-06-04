"""Creating a sandbox: a temporary demo organisation for one website visitor (section 12).

It makes no LLM call and starts no workflow. The sample documents are added by the seed
(M4); this module creates the organisation, the visitor and the two sample people.
"""

import json
from dataclasses import dataclass
from datetime import timedelta
from functools import cache
from pathlib import Path

from django.conf import settings
from django.db import transaction

from accounts.models import Organization, User
from eingang import clock
from eingang.config import get_settings

SAMPLE_PEOPLE = (
    ("anna-weber", "Anna Weber (sample)", User.Role.ACCOUNTANT),
    ("jonas-brandt", "Jonas Brandt (sample)", User.Role.APPROVER),
)


@dataclass(frozen=True)
class SampleBuyer:
    name: str
    vat_id: str


@cache
def sample_buyer() -> SampleBuyer:
    manifest_path: Path = settings.SAMPLES_DIR / "manifest.json"
    buyer = json.loads(manifest_path.read_text(encoding="utf-8"))["buyer"]
    return SampleBuyer(name=str(buyer["name"]), vat_id=str(buyer["vat_id"]))


def sandboxes_created_last_day() -> int:
    # Read through expires_at (creation time + TTL, set from the injected clock) rather
    # than created_at, which Django fills from the real clock.
    ttl = timedelta(hours=get_settings().SANDBOX_TTL_HOURS)
    created_since = clock.now() - timedelta(days=1)
    return Organization.objects.filter(
        kind=Organization.Kind.SANDBOX, expires_at__gte=created_since + ttl
    ).count()


@transaction.atomic
def create_sandbox() -> User:
    """The new sandbox's visitor (role admin, no usable password)."""
    config = get_settings()
    buyer = sample_buyer()
    organization = Organization.objects.create(
        name=buyer.name,
        slug="sandbox-pending",
        kind=Organization.Kind.SANDBOX,
        vat_id=buyer.vat_id,
        four_eyes=False,
        expires_at=clock.now() + timedelta(hours=config.SANDBOX_TTL_HOURS),
    )
    organization.slug = f"sandbox-{organization.id.hex}"
    organization.save(update_fields=["slug"])
    visitor = User.objects.create_user(
        f"sandbox-{organization.id.hex}@example.invalid",
        None,
        organization=organization,
        role=User.Role.ADMIN,
        name="Sandbox visitor",
    )
    for handle, name, role in SAMPLE_PEOPLE:
        # Inactive, so they appear in the history but can never sign in.
        User.objects.create_user(
            f"{handle}-{organization.id.hex}@example.invalid",
            None,
            organization=organization,
            role=role,
            name=name,
            is_active=False,
        )
    return visitor
