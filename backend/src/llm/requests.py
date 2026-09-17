"""The three LLM requests of Eingang (HANDOFF sections 5-7), built in one place.

The activities, the smoke call and the sample precompute build their requests here, so an
identical input gives an identical request (and the response cache can serve it again).
"""

from accounts.models import Organization
from llm import prompts
from llm.client import Request
from llm.schemas import ComparedValues, ExtractedInvoice, RuleExplanationOut

EXTRACT_MAX_OUTPUT_TOKENS = 2500
COMPARE_MAX_OUTPUT_TOKENS = 600
EXPLAIN_MAX_OUTPUT_TOKENS = 400


def extraction_request(
    text: str, organization: Organization | None = None
) -> Request[ExtractedInvoice]:
    """Read the invoice fields from the (already cut) text of a plain PDF."""
    return Request(
        purpose="extract",
        prompt=prompts.load("extract_invoice", 1),
        data=prompts.fenced("document", text),
        output=ExtractedInvoice,
        max_output_tokens=EXTRACT_MAX_OUTPUT_TOKENS,
        organization=organization,
    )


def comparison_request(
    text: str, organization: Organization | None = None
) -> Request[ComparedValues]:
    """Read five values from the (already cut) visible text of a hybrid PDF."""
    return Request(
        purpose="compare",
        prompt=prompts.load("compare_pdf_xml", 1),
        data=prompts.fenced("document", text),
        output=ComparedValues,
        max_output_tokens=COMPARE_MAX_OUTPUT_TOKENS,
        organization=organization,
    )


def explanation_request(
    rule_id: str, message: str, source: str, organization: Organization | None = None
) -> Request[RuleExplanationOut]:
    """Explain one validation rule from its ID, official message and source."""
    rule = "\n".join([f"Rule ID: {rule_id}", f"Official message: {message}", f"Source: {source}"])
    return Request(
        purpose="explain",
        prompt=prompts.load("explain_rule", 1),
        data=prompts.fenced("rule", rule),
        output=RuleExplanationOut,
        max_output_tokens=EXPLAIN_MAX_OUTPUT_TOKENS,
        organization=organization,
    )
