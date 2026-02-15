# Eingang

Eingang is an inbox for supplier invoices that tells a small German business whether each invoice is a valid e-invoice, turns every invoice (XRechnung XML, ZUGFeRD/Factur-X PDF or plain PDF) into the same clean data, catches duplicates and changed bank details, routes it for approval and exports it for the accountant.

**Live demo:** not deployed yet. The link is added when the project is deployed.

<!-- Screenshot strip: three images from docs/media/, added once recorded. -->

## The problem

Since 1 January 2025, every German business must be able to **receive** structured e-invoices that follow EN 16931. From 1 January 2027, businesses with more than €800,000 turnover may no longer **issue** paper or unstructured PDF invoices. From 1 January 2028 this applies to all domestic business-to-business invoices, except small-amount invoices up to €250 ([European Commission, "eInvoicing in Germany"](https://ec.europa.eu/digital-building-blocks/sites/spaces/DIGITAL/pages/467108886/eInvoicing+in+Germany)). Accepted formats include XRechnung (UBL or UN/CEFACT CII XML) and ZUGFeRD, a PDF with the invoice XML embedded. According to the BMF letter of 15 October 2024, the ZUGFeRD profiles MINIMUM and BASIC-WL do not count as e-invoices, and in a hybrid file the XML is the authoritative part ([ELO summary of the BMF letter](https://www.elo.com/de-de/blog/e-rechnungspflicht-bmf-schreiben-und-faq.html)). In a Bitkom survey of 1,103 German companies published in December 2024, only 45% could receive e-invoices ([vendor summary by Insiders Technologies](https://insiders-technologies.com/en/blog/e-invoicing-study-bitkom)). So for years a small company will receive a mix of valid XRechnung files, ZUGFeRD PDFs of varying quality, and plain PDFs. Someone has to check each one, type in the data, and notice when the same invoice arrives twice or a supplier's bank account suddenly changes, which is a common fraud pattern. Then the invoice needs approval and has to go to the tax advisor.

Eingang is not tax or legal advice. It checks published technical rules (EN 16931, XRechnung) and simple bookkeeping consistency.

## What it does

- Detects the format of each incoming file: XRechnung (UBL or CII), ZUGFeRD/Factur-X with its profile, plain PDF, or scan.
- Validates structured invoices against the official XSD and Schematron rules and explains each finding in plain language.
- Turns every invoice into the same fields. Values come from the XML where there is one, and from the PDF text with an AI model where there isn't, with the evidence for each value.
- Runs business checks: duplicates, changed bank details, arithmetic, an invoice addressed to someone else, and more.
- Routes invoices through review and four-eyes approval, and exports CSV/ZIP files for the tax advisor.

## How well it works

The extraction evaluation and the validation-parity check have not been run yet. Their results will appear here, with a link to `docs/EVALS.md`.

## Architecture

```mermaid
flowchart LR
    browser[Browser] --> web[Vue SPA]
    web -- "/api" --> api[Django API]
    api --> temporal[(Temporal)]
    worker[Temporal worker] --> temporal
    api --> db[(PostgreSQL)]
    worker --> db
    worker -. budget-gated .-> llm[OpenAI API]
```

The Vue app talks only to its own origin, which proxies `/api` to the Django API. The API stores uploads and starts one Temporal workflow per document. The worker does the heavy work: format detection, validation with SaxonC, PDF text extraction, and the budget-gated AI calls. It then waits durably for review and approval signals. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Run it locally

Prerequisites: Docker with Compose v2, Node 24 with Corepack, and [uv](https://docs.astral.sh/uv/).

```sh
corepack enable
pnpm install
cd backend && uv sync && cd ..
pnpm dev
```

`pnpm dev` starts PostgreSQL and Temporal in Docker, then the API (http://localhost:8010), the worker and the web app (http://localhost:3110). The Temporal UI is at http://localhost:8233. `pnpm verify` runs every check.

## Costs

See `docs/COSTS.md` (written at deployment, from measured numbers).

## Data and licences

- Design export in `design/export/`: the owner's own work, MIT.
- Third-party artefacts are listed with their licences in [NOTICE](NOTICE).

## Verified vs assumed

Statements that were not verified against a real system are listed in [docs/ASSUMPTIONS.md](docs/ASSUMPTIONS.md).

## Roadmap

- DATEV export (EXTF format).
- PDF/A-3 conformance checks for hybrid PDFs.

## License

MIT. See [LICENSE](LICENSE).
