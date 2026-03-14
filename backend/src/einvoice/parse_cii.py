"""UN/CEFACT CII (D16B) → CanonicalInvoice (XPath table in HANDOFF section 2)."""

from datetime import date
from decimal import Decimal

from lxml import etree

from einvoice import namespaces as ns
from einvoice.errors import InvoiceParseError, UnsupportedFileError
from einvoice.fields import (
    compact_upper,
    decimal_at,
    required_text,
    text,
    to_date,
    to_decimal,
    to_int,
)
from einvoice.model import CanonicalInvoice, Line, Party, TaxBreakdown
from einvoice.xmlsafe import parse_xml

NS = ns.CII_NS
DOCUMENT = "rsm:ExchangedDocument"
TRANSACTION = "rsm:SupplyChainTradeTransaction"
AGREEMENT = f"{TRANSACTION}/ram:ApplicableHeaderTradeAgreement"
SETTLEMENT = f"{TRANSACTION}/ram:ApplicableHeaderTradeSettlement"
SUMMATION = f"{SETTLEMENT}/ram:SpecifiedTradeSettlementHeaderMonetarySummation"
MEANS = f"{SETTLEMENT}/ram:SpecifiedTradeSettlementPaymentMeans"
TERMS = f"{SETTLEMENT}/ram:SpecifiedTradePaymentTerms"
# Format 102 is the only date format EN 16931 allows in CII.
DATE_102 = "%Y%m%d"


def _date(root: etree._Element, path: str, field: str) -> date | None:
    return to_date(text(root, path, NS), DATE_102, field, path)


def _party(root: etree._Element, base: str) -> Party:
    vat_id = None
    tax_number = None
    for registration in root.findall(f"{base}/ram:SpecifiedTaxRegistration/ram:ID", namespaces=NS):
        value = registration.text.strip() if registration.text else None
        if registration.get("schemeID") == "VA":
            vat_id = vat_id or value
        elif registration.get("schemeID") == "FC":
            tax_number = tax_number or value
    address = f"{base}/ram:PostalTradeAddress"
    return Party(
        name=text(root, f"{base}/ram:Name", NS),
        vat_id=compact_upper(vat_id),
        tax_number=tax_number or None,
        street=text(root, f"{address}/ram:LineOne", NS),
        postcode=text(root, f"{address}/ram:PostcodeCode", NS),
        city=text(root, f"{address}/ram:CityName", NS),
        country_code=text(root, f"{address}/ram:CountryID", NS),
        email=text(
            root,
            f"{base}/ram:DefinedTradeContact/ram:EmailURIUniversalCommunication/ram:URIID",
            NS,
        ),
    )


def _tax_total(root: etree._Element, currency: str) -> Decimal | None:
    # BT-110 carries the document currency; a second TaxTotalAmount may carry BT-111.
    path = f"{SUMMATION}/ram:TaxTotalAmount"
    for amount in root.findall(path, namespaces=NS):
        if amount.get("currencyID") in (None, currency):
            return to_decimal(amount.text.strip() if amount.text else None, "tax_total", path)
    return None


def _tax_breakdown(root: etree._Element) -> list[TaxBreakdown]:
    return [
        TaxBreakdown(
            category=text(tax, "ram:CategoryCode", NS),
            rate=decimal_at(tax, "ram:RateApplicablePercent", NS, "tax_breakdown"),
            taxable_amount=decimal_at(tax, "ram:BasisAmount", NS, "tax_breakdown"),
            tax_amount=decimal_at(tax, "ram:CalculatedAmount", NS, "tax_breakdown"),
        )
        for tax in root.findall(f"{SETTLEMENT}/ram:ApplicableTradeTax", namespaces=NS)
    ]


def _lines(root: etree._Element) -> list[Line]:
    lines = []
    settlement = "ram:SpecifiedLineTradeSettlement"
    for item in root.findall(f"{TRANSACTION}/ram:IncludedSupplyChainTradeLineItem", NS):
        quantity_path = "ram:SpecifiedLineTradeDelivery/ram:BilledQuantity"
        quantity = item.find(quantity_path, namespaces=NS)
        lines.append(
            Line(
                line_id=text(item, "ram:AssociatedDocumentLineDocument/ram:LineID", NS),
                description=text(item, "ram:SpecifiedTradeProduct/ram:Name", NS),
                quantity=decimal_at(item, quantity_path, NS, "lines.quantity"),
                unit_code=quantity.get("unitCode") if quantity is not None else None,
                unit_price=decimal_at(
                    item,
                    "ram:SpecifiedLineTradeAgreement/ram:NetPriceProductTradePrice/ram:ChargeAmount",
                    NS,
                    "lines.unit_price",
                ),
                net_amount=decimal_at(
                    item,
                    f"{settlement}/ram:SpecifiedTradeSettlementLineMonetarySummation"
                    "/ram:LineTotalAmount",
                    NS,
                    "lines.net_amount",
                ),
                tax_category=text(
                    item, f"{settlement}/ram:ApplicableTradeTax/ram:CategoryCode", NS
                ),
                tax_rate=decimal_at(
                    item,
                    f"{settlement}/ram:ApplicableTradeTax/ram:RateApplicablePercent",
                    NS,
                    "lines.tax_rate",
                ),
            )
        )
    return lines


def _notes(root: etree._Element) -> list[str]:
    notes = []
    for content in root.findall(f"{DOCUMENT}/ram:IncludedNote/ram:Content", namespaces=NS):
        value = (content.text or "").strip()
        if value:
            notes.append(value)
    return notes


def parse_cii_root(root: etree._Element) -> CanonicalInvoice:
    if root.tag != ns.CII_ROOT:
        raise UnsupportedFileError("not a CII invoice")
    currency = required_text(root, f"{SETTLEMENT}/ram:InvoiceCurrencyCode", NS, "currency")
    issue_path = f"{DOCUMENT}/ram:IssueDateTime/udt:DateTimeString"
    issue_date = _date(root, issue_path, "issue_date")
    if issue_date is None:
        raise InvoiceParseError("issue_date", issue_path)
    gross_path = f"{SUMMATION}/ram:GrandTotalAmount"
    gross_total = decimal_at(root, gross_path, NS, "gross_total")
    if gross_total is None:
        raise InvoiceParseError("gross_total", gross_path)
    seller_base = f"{AGREEMENT}/ram:SellerTradeParty"
    seller = _party(root, seller_base)
    if seller.name is None:
        raise InvoiceParseError("seller.name", f"{seller_base}/ram:Name")
    type_path = f"{DOCUMENT}/ram:TypeCode"

    def total(element: str, field: str) -> Decimal | None:
        return decimal_at(root, f"{SUMMATION}/ram:{element}", NS, field)

    return CanonicalInvoice.model_validate(
        {
            "invoice_number": required_text(root, f"{DOCUMENT}/ram:ID", NS, "invoice_number"),
            "type_code": to_int(text(root, type_path, NS), "type_code", type_path),
            "issue_date": issue_date,
            "due_date": _date(root, f"{TERMS}/ram:DueDateDateTime/udt:DateTimeString", "due_date"),
            "currency": currency,
            "buyer_reference": text(root, f"{AGREEMENT}/ram:BuyerReference", NS),
            "order_reference": text(
                root, f"{AGREEMENT}/ram:BuyerOrderReferencedDocument/ram:IssuerAssignedID", NS
            ),
            "seller": seller,
            "buyer": _party(root, f"{AGREEMENT}/ram:BuyerTradeParty"),
            "payee_iban": compact_upper(
                text(root, f"{MEANS}/ram:PayeePartyCreditorFinancialAccount/ram:IBANID", NS)
            ),
            "payee_bic": compact_upper(
                text(root, f"{MEANS}/ram:PayeeSpecifiedCreditorFinancialInstitution/ram:BICID", NS)
            ),
            "payment_terms": text(root, f"{TERMS}/ram:Description", NS),
            "line_total": total("LineTotalAmount", "line_total"),
            "allowance_total": total("AllowanceTotalAmount", "allowance_total"),
            "charge_total": total("ChargeTotalAmount", "charge_total"),
            "net_total": total("TaxBasisTotalAmount", "net_total"),
            "tax_total": _tax_total(root, currency),
            "gross_total": gross_total,
            "prepaid_amount": total("TotalPrepaidAmount", "prepaid_amount"),
            "payable_amount": total("DuePayableAmount", "payable_amount"),
            "tax_breakdown": _tax_breakdown(root),
            "lines": _lines(root),
            "notes": _notes(root),
        }
    )


def parse_cii(xml: bytes) -> CanonicalInvoice:
    return parse_cii_root(parse_xml(xml))
