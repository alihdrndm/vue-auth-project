"""The regex baseline reads labelled values from German, English and French text."""

from evals import baseline_regex

GERMAN = """--- page 1 ---
Druckerei Sommer GmbH
USt-IdNr.: DE360588120
Rechnungsnummer: 2026-1043
Rechnungsdatum: 20.02.2026
Netto: 1.300,00 EUR
USt 19 %: 247,00 EUR
Brutto: 1.547,00 EUR
Zahlbetrag: 1.547,00 EUR
IBAN: DE29 1001 0010 0987 6543 21
"""

ENGLISH = """--- page 1 ---
Acme Ltd
Invoice No: INV-778
Invoice date: 2026-02-03
Due date: 2026-03-05
Net total: 1,000.00 GBP
VAT: 200.00
Total amount: 1,200.00
"""

FRENCH = """--- page 1 ---
Atelier Moreau SARL
Facture n° F-2026-118
Date de facture : 12/03/2026
Total HT : 640,00 €
Total TTC : 640,00 €
"""


def test_reads_a_german_invoice() -> None:
    values = baseline_regex.extract(GERMAN)
    assert values["invoice_number"] == "2026-1043"
    assert values["issue_date"] == "2026-02-20"
    assert values["seller.vat_id"] == "DE360588120"
    assert values["net_total"] == "1300.00"
    assert values["tax_total"] == "247.00"
    assert values["gross_total"] == "1547.00"
    assert values["payable_amount"] == "1547.00"
    assert values["payee_iban"] == "DE29100100100987654321"
    assert values["currency"] == "EUR"
    assert values["seller.name"] == "Druckerei Sommer GmbH"
    assert values["buyer.name"] is None  # the baseline never guesses the buyer


def test_reads_an_english_invoice() -> None:
    values = baseline_regex.extract(ENGLISH)
    assert values["invoice_number"] == "INV-778"
    assert values["issue_date"] == "2026-02-03"
    assert values["due_date"] == "2026-03-05"
    assert values["net_total"] == "1000.00"
    assert values["gross_total"] == "1200.00"
    assert values["currency"] == "GBP"


def test_reads_a_french_invoice() -> None:
    values = baseline_regex.extract(FRENCH)
    assert values["invoice_number"] == "F-2026-118"
    assert values["issue_date"] == "2026-03-12"
    assert values["net_total"] == "640.00"
    assert values["gross_total"] == "640.00"
    assert values["currency"] == "EUR"


def test_returns_none_for_what_it_cannot_read() -> None:
    values = baseline_regex.extract("--- page 1 ---\n\nnothing here 31.02.2026")
    assert values["issue_date"] is None
    assert values["invoice_number"] is None
    assert values["seller.name"] == "nothing here 31.02.2026"
