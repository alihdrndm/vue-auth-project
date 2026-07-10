"""`GET /rules/{rule_id}` (HANDOFF "HTTP API", section 7)."""

from collections.abc import Callable

import pytest

from invoices.models import RuleExplanation
from tests.conftest import ApiClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def br_de_15() -> RuleExplanation:
    return RuleExplanation.objects.create(
        rule_id="BR-DE-15",
        plain_text="The buyer reference (BT-10) is missing.",
        fix_hint="Ask the supplier to resend the invoice with your buyer reference.",
        source=RuleExplanation.Source.CURATED,
    )


@pytest.mark.parametrize("role", ["admin", "accountant", "approver", "viewer"])
def test_rules_explanation_is_returned_to_every_role(
    role: str, signed_in: Callable[[str], ApiClient], br_de_15: RuleExplanation
) -> None:
    response = signed_in(role).get("/api/v1/rules/BR-DE-15")
    assert response.status_code == 200
    assert response.json() == {
        "rule_id": "BR-DE-15",
        "plain_text": "The buyer reference (BT-10) is missing.",
        "fix_hint": "Ask the supplier to resend the invoice with your buyer reference.",
        "source": "curated",
    }


def test_rules_llm_explanation_says_its_source(signed_in: Callable[[str], ApiClient]) -> None:
    RuleExplanation.objects.create(
        rule_id="PEPPOL-EN16931-R001",
        plain_text="Text.",
        fix_hint="Hint.",
        source=RuleExplanation.Source.LLM,
        prompt_version="v1",
    )
    body = signed_in("viewer").get("/api/v1/rules/PEPPOL-EN16931-R001").json()
    assert body["source"] == "llm"
    assert "prompt_version" not in body


def test_rules_unknown_rule_is_NOT_FOUND(signed_in: Callable[[str], ApiClient]) -> None:
    response = signed_in("viewer").get("/api/v1/rules/BR-99")
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


@pytest.mark.parametrize("rule_id", ["BR%20DE%2015", "BR-DE-15%3B", "BR+DE", "%C3%A4"])
def test_rules_id_with_other_characters_is_NOT_FOUND(
    rule_id: str, signed_in: Callable[[str], ApiClient], br_de_15: RuleExplanation
) -> None:
    response = signed_in("viewer").get(f"/api/v1/rules/{rule_id}")
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_rules_id_with_dots_and_underscores_is_looked_up(
    signed_in: Callable[[str], ApiClient],
) -> None:
    RuleExplanation.objects.create(
        rule_id="UBL-CR_1.2", plain_text="Text.", fix_hint="Hint.", source="curated"
    )
    assert signed_in("viewer").get("/api/v1/rules/UBL-CR_1.2").status_code == 200


def test_rules_need_a_session_NOT_AUTHENTICATED(api: ApiClient, br_de_15: RuleExplanation) -> None:
    response = api.get("/api/v1/rules/BR-DE-15")
    assert response.status_code == 401
    assert response.json()["code"] == "NOT_AUTHENTICATED"
