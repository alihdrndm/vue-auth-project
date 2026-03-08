"""XML namespaces and root element names of the two EN 16931 syntaxes."""

UBL_INVOICE = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
UBL_CREDIT_NOTE = "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2"
CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"

RSM = "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
RAM = "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
UDT = "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100"
QDT = "urn:un:unece:uncefact:data:standard:QualifiedDataType:100"

# The root element of a ZUGFeRD 1.0 invoice lives in this namespace.
ZUGFERD1 = "urn:ferd:CrossIndustryDocument:invoice:1p0"

UBL_INVOICE_ROOT = f"{{{UBL_INVOICE}}}Invoice"
UBL_CREDIT_NOTE_ROOT = f"{{{UBL_CREDIT_NOTE}}}CreditNote"
CII_ROOT = f"{{{RSM}}}CrossIndustryInvoice"

UBL_NS = {"cbc": CBC, "cac": CAC}
CII_NS = {"rsm": RSM, "ram": RAM, "udt": UDT, "qdt": QDT}
