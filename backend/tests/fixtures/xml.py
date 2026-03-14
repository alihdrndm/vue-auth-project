"""Small hand-made XML documents for detection tests."""

from einvoice import namespaces as ns

XRECHNUNG_3 = "urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0"


def ubl(spec_id: str | None = XRECHNUNG_3, *, credit_note: bool = False) -> bytes:
    root, namespace = (
        ("CreditNote", ns.UBL_CREDIT_NOTE) if credit_note else ("Invoice", ns.UBL_INVOICE)
    )
    customization = f"<cbc:CustomizationID>{spec_id}</cbc:CustomizationID>" if spec_id else ""
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<{root} xmlns="{namespace}" xmlns:cbc="{ns.CBC}" xmlns:cac="{ns.CAC}">'
        f"{customization}<cbc:ID>RE-1</cbc:ID></{root}>"
    ).encode()


def cii(spec_id: str | None = XRECHNUNG_3) -> bytes:
    context = (
        "<rsm:ExchangedDocumentContext><ram:GuidelineSpecifiedDocumentContextParameter>"
        f"<ram:ID>{spec_id}</ram:ID>"
        "</ram:GuidelineSpecifiedDocumentContextParameter></rsm:ExchangedDocumentContext>"
        if spec_id
        else ""
    )
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<rsm:CrossIndustryInvoice xmlns:rsm="{ns.RSM}" xmlns:ram="{ns.RAM}" xmlns:udt="{ns.UDT}">'
        f"{context}</rsm:CrossIndustryInvoice>"
    ).encode()


def zugferd1() -> bytes:
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<rsm:CrossIndustryDocument xmlns:rsm="{ns.ZUGFERD1}"/>'
    ).encode()
