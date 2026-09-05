"""Output models for the LLM calls, used as Structured Outputs `text_format` (sections 5-7).

Structured Outputs in strict mode needs every property listed in `required` and
`additionalProperties: false` on every object, so no field here has a default: a value
the model cannot find is an explicit null. Array lengths are capped with `maxItems`,
which strict mode supports. String lengths (`maxLength`) are not supported there, so the
rule-explanation limits are applied in code after parsing (`RuleExplanationOut.clipped`).
"""

from pydantic import BaseModel, ConfigDict, Field

MAX_TAX_ROWS = 5
MAX_LINES = 30
PLAIN_TEXT_MAX = 300
FIX_HINT_MAX = 200


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExtractedTaxRow(_Strict):
    category: str | None
    rate: str | None
    taxable_amount: str | None
    tax_amount: str | None


class ExtractedLine(_Strict):
    description: str | None
    quantity: str | None
    unit_price: str | None
    net_amount: str | None
    tax_rate: str | None


class ExtractedInvoice(_Strict):
    """Section 5: flattened header fields, each with the snippet of text it was read from.

    Amounts are decimal strings with a dot, dates `YYYY-MM-DD`; every `<field>_evidence`
    is the shortest verbatim snippet (at most 80 characters) that contains the value.
    """

    invoice_number: str | None
    invoice_number_evidence: str | None
    issue_date: str | None
    issue_date_evidence: str | None
    due_date: str | None
    due_date_evidence: str | None
    currency: str | None
    currency_evidence: str | None
    buyer_reference: str | None
    buyer_reference_evidence: str | None
    order_reference: str | None
    order_reference_evidence: str | None
    seller_name: str | None
    seller_name_evidence: str | None
    seller_vat_id: str | None
    seller_vat_id_evidence: str | None
    seller_tax_number: str | None
    seller_tax_number_evidence: str | None
    seller_street: str | None
    seller_street_evidence: str | None
    seller_postcode: str | None
    seller_postcode_evidence: str | None
    seller_city: str | None
    seller_city_evidence: str | None
    seller_country_code: str | None
    seller_country_code_evidence: str | None
    seller_email: str | None
    seller_email_evidence: str | None
    buyer_name: str | None
    buyer_name_evidence: str | None
    buyer_vat_id: str | None
    buyer_vat_id_evidence: str | None
    payee_iban: str | None
    payee_iban_evidence: str | None
    payee_bic: str | None
    payee_bic_evidence: str | None
    payment_terms: str | None
    payment_terms_evidence: str | None
    line_total: str | None
    line_total_evidence: str | None
    allowance_total: str | None
    allowance_total_evidence: str | None
    charge_total: str | None
    charge_total_evidence: str | None
    net_total: str | None
    net_total_evidence: str | None
    tax_total: str | None
    tax_total_evidence: str | None
    gross_total: str | None
    gross_total_evidence: str | None
    prepaid_amount: str | None
    prepaid_amount_evidence: str | None
    payable_amount: str | None
    payable_amount_evidence: str | None
    tax_breakdown: list[ExtractedTaxRow] = Field(max_length=MAX_TAX_ROWS)
    lines: list[ExtractedLine] = Field(max_length=MAX_LINES)


class ComparedValues(_Strict):
    """Section 6: the values read from the visible text of a hybrid PDF, with evidence."""

    invoice_number: str | None
    invoice_number_evidence: str | None
    issue_date: str | None
    issue_date_evidence: str | None
    gross_total: str | None
    gross_total_evidence: str | None
    payable_amount: str | None
    payable_amount_evidence: str | None
    payee_iban: str | None
    payee_iban_evidence: str | None


class RuleExplanationOut(_Strict):
    """Section 7: a plain-English explanation of a validation rule and how to fix it."""

    plain_text: str
    fix_hint: str

    def clipped(self) -> "RuleExplanationOut":
        """The same texts cut to the stored limits (300 and 200 characters)."""
        return RuleExplanationOut(
            plain_text=_clip(self.plain_text, PLAIN_TEXT_MAX),
            fix_hint=_clip(self.fix_hint, FIX_HINT_MAX),
        )


def _clip(text: str, limit: int) -> str:
    """Collapse whitespace; if still too long, cut at the last word break and add an ellipsis."""
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    cut = collapsed[: limit - 1]
    if " " in cut:
        cut = cut[: cut.rindex(" ")]
    return cut.rstrip(" ,;:.") + "…"
