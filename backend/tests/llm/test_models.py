from decimal import Decimal

import pytest

from accounts.models import Organization
from llm.models import LlmCall


@pytest.mark.django_db
def test_deleting_an_organization_keeps_its_llm_ledger_rows() -> None:
    organization = Organization.objects.create(name="Sandbox", slug="sb", kind="sandbox")
    call = LlmCall.objects.create(
        organization=organization,
        purpose="extract_invoice",
        model="test-model",
        prompt_version="v1",
        input_tokens=1200,
        output_tokens=300,
        cost=Decimal("0.000420"),
        latency_ms=850,
        status=LlmCall.Status.OK,
    )

    organization.delete()

    call.refresh_from_db()
    assert call.organization is None
    assert call.cost == Decimal("0.000420")
