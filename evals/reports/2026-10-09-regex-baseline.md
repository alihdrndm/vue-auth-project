# Extraction accuracy: `regex-baseline`

Run of 2026-10-09 19:34 UTC on the dataset `zugferd-corpus-hybrid-cii` (104 documents, corpus commit `d891458e9822`); 104 documents scored.

## Headline

| System | Critical fields correct (95% CI) | Cost | Per document | Latency p50 | Latency p95 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `regex-baseline` | 21.2% (13.5% to 28.8%) | $0.0000 | $0.000000 | 3 ms | 6 ms |

A document's critical fields are correct when its invoice number, issue date, gross total and (if the invoice has one) payee IBAN are all correct. The interval is a 95% bootstrap confidence interval.

## Per field

| Field | Accuracy | Hallucination | Abstention |
| --- | ---: | ---: | ---: |
| `invoice_number` | 33.7% | n/a | 33.7% |
| `issue_date` | 75.0% | n/a | 20.2% |
| `due_date` | 8.8% | 4.3% | 88.2% |
| `currency` | 99.0% | n/a | 1.0% |
| `seller.name` | 31.7% | n/a | 0.0% |
| `seller.vat_id` | 89.2% | 100.0% | 2.9% |
| `payee_iban` | 91.4% | 14.5% | 2.9% |
| `buyer.name` | 25.0% | n/a | 75.0% |
| `net_total` | 83.7% | n/a | 14.4% |
| `tax_total` | 87.5% | n/a | 0.0% |
| `gross_total` | 93.3% | n/a | 4.8% |
| `payable_amount` | 93.3% | n/a | 6.7% |

Accuracy counts the documents whose truth has the field; hallucination, a value read where the truth has none; abstention, no value where the truth has one. `n/a`: the rate has no documents to count.

## Validation parity

| Validation parity |  |
| --- | ---: |
| Files compared | 176 |
| Excluded | 64 |
| Verdict agreement | 100.0% |
| Fatal rule set agreement | 100.0% |

## Method

Dataset, scoring rules, statistics and limits: [docs/EVALS.md](../../docs/EVALS.md).
