"""The sandbox seed: the twelve samples end with exactly the manifest's checks and statuses."""

import json
import shutil
from datetime import timedelta
from pathlib import Path

import pytest
from django.conf import settings
from django.test import override_settings

from accounts.models import Organization, User
from eingang import clock, storage
from eingang.workflows.contracts import NOTE_PDF_NOT_COMPARED
from invoices.models import Approval, Check, Document, Event
from llm.models import LlmCall
from llm.schemas import ComparedValues, ExtractedInvoice
from sandbox.seed import DECISION_DELAY, Sample, manifest
from sandbox.services import create_sandbox

pytestmark = pytest.mark.django_db


@pytest.fixture
def sandbox(fixed_clock: clock.FixedClock) -> Organization:
    return create_sandbox().organization


def by_number(organization: Organization) -> dict[str, Document]:
    """Seeded documents by sample ID (the file name starts with it)."""
    documents = Document.objects.filter(organization=organization)
    return {document.original_filename[:3]: document for document in documents}


@pytest.mark.parametrize("sample", manifest(), ids=[sample.id for sample in manifest()])
def test_seed_gives_each_sample_the_manifests_checks_and_status(
    sandbox: Organization, sample: Sample
) -> None:
    document = by_number(sandbox)[sample.id]
    checks = sorted(Check.objects.filter(document=document).values_list("check_id", flat=True))
    assert checks == sorted(sample.expected_checks)
    assert document.status == sample.expected_status
    assert document.format_label == sample.format_label


def test_seed_makes_twelve_documents_without_workflows_or_llm_calls(
    sandbox: Organization,
) -> None:
    documents = Document.objects.filter(organization=sandbox)
    assert documents.count() == 12
    assert set(documents.values_list("workflow_id", flat=True)) == {""}
    assert set(documents.values_list("source", flat=True)) == {"sample"}
    assert set(documents.values_list("processing_step", flat=True)) == {"done"}
    assert not LlmCall.objects.exists()


def test_seed_receives_each_sample_at_its_offset(sandbox: Organization) -> None:
    documents = by_number(sandbox)
    for sample in manifest():
        received = clock.now() - timedelta(minutes=sample.received_offset_minutes)
        assert documents[sample.id].received_at == received


def test_seed_stores_the_files_the_viewer_needs(sandbox: Organization) -> None:
    documents = by_number(sandbox)
    for document in documents.values():
        assert storage.exists(document.storage_key)

    def derived(sample_id: str, name: storage.DerivedFile) -> bool:
        document = documents[sample_id]
        return storage.exists(storage.derived_key(sandbox.id, document.id, name))

    assert derived("S01", "invoice.xml")
    assert derived("S03", "invoice.xml")  # extracted from the hybrid PDF
    assert derived("S01", "visualization.html")
    assert derived("S08", "text.txt")
    assert documents["S08"].text_storage_key is not None
    assert not derived("S08", "invoice.xml")


def test_seed_records_the_two_sample_decisions(sandbox: Organization) -> None:
    documents = by_number(sandbox)
    jonas = User.objects.get(organization=sandbox, name="Jonas Brandt (sample)")
    approved = Approval.objects.get(document=documents["S11"])
    rejected = Approval.objects.get(document=documents["S12"])
    assert (approved.decision, approved.decided_by) == ("approved", jonas)
    assert (rejected.decision, rejected.decided_by) == ("rejected", jonas)
    assert rejected.comment == "Wrong cost centre, please ask for a corrected invoice."
    assert approved.decided_at == documents["S11"].received_at + DECISION_DELAY


def test_seed_writes_the_history_a_real_run_writes(sandbox: Organization) -> None:
    documents = by_number(sandbox)
    s01 = documents["S01"]
    types = list(
        Event.objects.filter(document=s01).order_by("created_at").values_list("type", flat=True)
    )
    assert types[:3] == ["document.received", "processing.started", "processing.step"]
    assert types[-1] == "processing.completed"
    assert "check.created" in types
    first = Event.objects.filter(document=s01).order_by("created_at").first()
    assert first is not None
    assert first.created_at == s01.received_at
    note = {"note": NOTE_PDF_NOT_COMPARED}
    assert Event.objects.filter(document=documents["S03"], data=note).exists()
    assert not Event.objects.filter(document=documents["S01"], data=note).exists()


def test_seed_matches_suppliers_in_received_order(sandbox: Organization) -> None:
    documents = by_number(sandbox)
    # S11 arrived first from Bürobedarf Nord, so its IBAN is the known one and S07's is new.
    s07 = documents["S07"].invoice
    s11 = documents["S11"].invoice
    assert s07.supplier_id == s11.supplier_id
    assert s07.supplier is not None
    assert s07.supplier.invoice_count == 3


def test_two_sandboxes_get_separate_documents(fixed_clock: clock.FixedClock) -> None:
    first = create_sandbox().organization
    second = create_sandbox().organization
    assert Document.objects.filter(organization=first).count() == 12
    assert Document.objects.filter(organization=second).count() == 12


def test_seed_uses_precomputed_llm_answers_when_present(
    tmp_path: Path, fixed_clock: clock.FixedClock
) -> None:
    samples = tmp_path / "samples"
    shutil.copytree(settings.SAMPLES_DIR, samples)
    s08 = samples / "precomputed" / "S08.json"
    data = json.loads(s08.read_text(encoding="utf-8"))
    answer: dict[str, object] = dict.fromkeys(ExtractedInvoice.model_fields)
    answer.update(
        tax_breakdown=[],
        lines=[],
        invoice_number="2026-1043",
        invoice_number_evidence="Rechnungsnummer: 2026-1043",
        seller_name="Druckerei Sommer GmbH",
        seller_name_evidence="Druckerei Sommer GmbH",
        seller_vat_id="DE360588120",
        seller_vat_id_evidence="USt-IdNr.: DE360588120",
        gross_total="1547.00",
        gross_total_evidence="Brutto: 1.547,00 EUR",
        payee_iban="DE29100100100987654321",
        payee_iban_evidence="Bank: DE29100100100987654321",  # not in the text: graded low
    )
    data["extraction"] = {"prompt_version": "extract_invoice.v1", "answer": answer}
    s08.write_text(json.dumps(data), encoding="utf-8")
    s10 = samples / "precomputed" / "S10.json"
    data = json.loads(s10.read_text(encoding="utf-8"))
    shown: dict[str, object] = dict.fromkeys(ComparedValues.model_fields)
    shown.update(gross_total="1190.00", gross_total_evidence="Brutto: 1.190,00 EUR")
    data["comparison"] = {"prompt_version": "compare_pdf_xml.v1", "answer": shown}
    s10.write_text(json.dumps(data), encoding="utf-8")

    with override_settings(SAMPLES_DIR=samples):
        organization = create_sandbox().organization
    documents = by_number(organization)
    s08_checks = set(
        Check.objects.filter(document=documents["S08"]).values_list("check_id", flat=True)
    )
    assert s08_checks == {"C04", "C11", "C13"}
    assert documents["S08"].invoice.extraction_method == "llm"
    assert documents["S08"].invoice.prompt_version == "extract_invoice.v1"
    assert documents["S08"].status == "needs_review"
    s10_checks = set(
        Check.objects.filter(document=documents["S10"]).values_list("check_id", flat=True)
    )
    assert s10_checks == {"C04", "C09"}
    assert documents["S10"].status == "needs_review"
    note = {"note": NOTE_PDF_NOT_COMPARED}
    assert not Event.objects.filter(document=documents["S10"], data=note).exists()
