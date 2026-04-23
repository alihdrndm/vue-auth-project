# Architecture

This file grows with each milestone. It covers the component map, the request flow, the workflow diagrams, and where each rule of the specification is implemented.

## Component map

```mermaid
flowchart LR
    browser[Browser] --> web["Vue SPA<br/>(Vite dev server / Vercel)"]
    web -- "/api proxy" --> api["api<br/>Django + DRF"]
    api -- "start workflow / signal" --> temporal[(Temporal<br/>dev server)]
    worker["worker<br/>Temporal activities"] -- "polls eingang-main" --> temporal
    api --> db[(PostgreSQL)]
    worker --> db
    api --> files[(File storage<br/>local / Supabase S3)]
    worker --> files
    worker -. "budget-gated" .-> openai[OpenAI API]
```

| Component | Code | Runs as |
|-----------|------|---------|
| `einvoice` | `backend/src/einvoice/` | Library with no framework imports, used by the worker and the tools |
| API | `backend/src/eingang/` (project) plus Django apps | `manage.py runserver` (development), gunicorn (production) |
| Worker | `backend/src/eingang/worker.py` | `python -m eingang.worker` |
| Workflows | `backend/src/eingang/workflows/` | Inside the worker; imports only the standard library, `temporalio` and the contracts module |
| Frontend | `frontend/` | Vite dev server on 3110; static build on Vercel |
| Backing services | `compose.yaml` | Docker: `db` (PostgreSQL 17, port 5452), `temporal` (gRPC 7233, UI 8233) |

## Request flow (API)

1. `eingang.middleware.RequestContextMiddleware` takes the request id from `x-request-id`, or generates a UUID v7. It stores the id in a context variable that every log line reads, and echoes it in the response.
2. Django's security, session, CSRF and authentication middleware run.
3. The DRF view runs. Any error goes through `eingang.problem.exception_handler` and becomes `application/problem+json`.
4. Unknown routes (404) and unhandled exceptions (500) are turned into problem+json by the same middleware. No internal detail reaches the client.
5. The middleware writes one log line: method, path without the query string, status, duration, request id.

## Where the rules live

| Rule (HANDOFF.md) | Implemented in |
|-------------------|----------------|
| Configuration read once, invalid configuration exits with status 1 | `backend/src/eingang/config.py` |
| Errors are problem+json with documented codes | `backend/src/eingang/problem.py`, `docs/ERRORS.md` |
| Request id, request log line without query string | `backend/src/eingang/middleware.py`, `backend/src/eingang/log.py` |
| `/healthz`, `/readyz` (database and Temporal, 2-second timeouts) | `backend/src/eingang/health.py`, `backend/src/eingang/temporal_client.py` |
| Security headers | `backend/src/eingang/settings.py` |
| OpenAPI at `/api/schema/` and `/docs`, committed `openapi.json` | `backend/src/eingang/urls.py`, `backend/tools/export_openapi.py` |
| Import boundaries | `backend/.importlinter` |
| Format detection D1–D5, profile from BT-24, format label | `backend/src/einvoice/detect.py` |
| Embedded XML and text layer of PDFs | `backend/src/einvoice/pdf.py` |
| XML safety (no DOCTYPE, no entities, no network) | `backend/src/einvoice/xmlsafe.py`, `pdf.py` (attachments refused before factur-x parses them) |
| Canonical invoice model and its precisions | `backend/src/einvoice/model.py` |
| XPath mapping UBL / CII → canonical | `backend/src/einvoice/parse_ubl.py`, `parse_cii.py`, `fields.py` |
| Writing UBL / CII | `backend/src/einvoice/write.py` |
| Coverage thresholds per package | `backend/tools/check_coverage.py` |
| Vendored KoSIT rules, pinned by SHA-256 | `backend/tools/fetch_rules.py`, `backend/vendor/rules.lock.json`, `backend/vendor/` |
| Validation steps 1–5 (XSD, EN 16931, XRechnung, SVRL, status) | `backend/src/einvoice/validate.py`, `svrl.py` |
| KoSIT scenario custom levels | `backend/src/einvoice/scenarios.py` |
| SaxonC on one thread, stylesheets compiled once | `backend/src/einvoice/saxon.py`; warm-up in `backend/src/eingang/worker.py` |
| Visualisation (UBL/CII → XR → static HTML) | `backend/src/einvoice/visualize.py` |
| Sandbox sample set, manifest and precomputed data | `backend/tools/sample_data.py`, `backend/tools/build_samples.py`, `samples/` |

## The `einvoice` package

A plain Python library with no framework imports (import-linter contract `einvoice-is-pure`). The data flows like this:

```mermaid
flowchart LR
    bytes[file bytes] --> detect["detect()<br/>D1–D5"]
    detect -->|PDF| pdf["pdf.embedded_invoice_xml()<br/>pdf.extract_text()"]
    detect -->|XML / hybrid| xml["xmlsafe.parse_xml()"]
    xml --> parse["parse_ubl() / parse_cii()"]
    parse --> model[CanonicalInvoice]
    model --> write["to_ubl() / to_cii()"]
    xml --> validate["validate()<br/>XSD → EN 16931 → XRechnung<br/>+ KoSIT custom levels"]
    xml --> visualize["visualize()<br/>→ XR → static HTML"]
```

Validation and visualisation run SaxonC-HE. Its native runtime is bound to one thread, so `einvoice.saxon` runs every transformation on a single dedicated thread and caches the compiled stylesheets there. Callers on any worker thread submit a job and wait for the result.
