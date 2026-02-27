# Decisions and deviations

Dated record of every place the implementation differs from, or fills a gap in, `HANDOFF.md` (OP5, OP7). Newest last.

## 2026-10-09 — M0

### Temporal image pinned to `temporalio/temporal:1.9.1`
- **Spec:** pin the official `temporalio/temporal` image by version tag and record the tag.
- **Did:** `1.9.1`, the latest stable tag on Docker Hub when checked. `1.9.1`, `latest` and `release` shared one digest, pushed 2026-09-14, matching the `temporalio/cli` v1.9.1 GitHub release.
- **Why:** reproducible local and demo servers.

### Error codes for generic HTTP errors
- **Spec:** every non-2xx response is problem+json with a documented `code`. It names no codes for malformed JSON, a wrong method, a wrong `Accept` or `Content-Type` header, or `/readyz` failing.
- **Did:** added `MALFORMED_REQUEST` (400), `METHOD_NOT_ALLOWED` (405), `NOT_ACCEPTABLE` (406), `UNSUPPORTED_MEDIA_TYPE` (415) and `NOT_READY` (503). All are documented in `docs/ERRORS.md`. `/readyz`'s 503 carries the extension member `checks`, which says which dependency failed.
- **Why:** these responses must still be problem+json, and each code must be documented.

### `/readyz` checks run one after the other
- **Spec:** the database and Temporal are each checked with a 2-second timeout.
- **Did:** the checks run in sequence, each with its own 2-second limit. The worst case is therefore about 4 seconds. The database check runs on a separate thread and connection, so a hung connection attempt can't block the request beyond the timeout.

### Request id from the client is validated
- **Spec:** read `x-request-id` if present.
- **Did:** a client-supplied id is used only if it matches `[A-Za-z0-9._-]{1,128}`. Otherwise a new UUID v7 is generated.
- **Why:** the id is echoed in a header and written to every log line, so arbitrary input would allow header or log injection.

### Development API server
- **Spec:** `pnpm dev` runs the API with hot reload. The server's own access log is turned off.
- **Did:** in development the API runs on Django's `runserver` on port 8010, and its `django.server` access logger is silenced. The app's own request log line replaces it. Production uses gunicorn exactly as specified.
- **Why:** gunicorn does not run on Windows, and `uvicorn` is not an allowed dependency.

### Poe tasks put `src` on `PYTHONPATH`
- **Did:** the `lint-imports` and `worker` tasks set `PYTHONPATH=src`.
- **Why:** `backend/` is a virtual uv project (no build system), so `src/` is not installed into the environment. `manage.py` and pytest add it themselves.

### Worker with nothing registered
- **Did:** until the first activities (M2) and workflows (M4) exist, `python -m eingang.worker` logs that nothing is registered and exits with status 0.
- **Why:** the Temporal SDK refuses to start a worker with no workflows and no activities. `pnpm dev` still starts the worker process, so the wiring is already in place.

### Import-linter contracts arrive with their modules
- **Did:** `einvoice-is-pure` and `workflows-are-deterministic` are active now. `api-stays-light` and `one-llm-door`, plus the Django-app entries of the first two, are added once the modules they name exist (M3–M5). Until then import-linter rejects contracts that name missing packages.

### Coverage thresholds per package arrive with the packages
- **Did:** M0 enforces the "everything else" threshold, 75% of lines with branch measurement, over `src/`. The stricter thresholds for `einvoice` (M1) and `invoices` (M4) are added once those packages contain code.

### Authentication classes empty until M3
- **Did:** DRF's default authentication and permission classes are empty in M0. The only endpoints are the public health checks and the schema. The session authentication subclass and the role permissions come with M3.

### LF line endings enforced with `.gitattributes`
- **Did:** `* text=auto eol=lf`.
- **Why:** this repository is developed on Windows with `core.autocrlf`. `.editorconfig` requires LF, and the generated files (`openapi.json`, `schema.d.ts`) must be byte-identical on every OS for the CI freshness checks.

### TypeScript pinned to 5.9
- **Spec:** latest stable release of every named package.
- **Did:** `typescript ~5.9.3`.
- **Why:** `typescript-eslint` 8.71 supports TypeScript below 6.1, and `openapi-typescript` 7.13 needs TypeScript 5. With 5.9, `pnpm peers check` reports no problems. Upgrade once both support the current TypeScript major.

### `vue-demi` build script disabled
- **Did:** `allowBuilds: { vue-demi: false }` in `pnpm-workspace.yaml`.
- **Why:** pnpm 12 refuses to install a dependency whose build script has not been approved. `vue-demi`, pulled in by `@tanstack/vue-query`, only needs that script to switch to Vue 2, and its default build already targets Vue 3.

### e2e job and `test:e2e` wait for the e2e stack (M8)
- **Did:** the frontend's `test:e2e` script is not added yet. The CI `e2e` job runs, but every step after checkout is guarded with `if: hashFiles('frontend/e2e/smoke.spec.ts') != ''`.
- **Why:** the e2e Compose profile, the Dockerfiles and the Playwright smoke test arrive in M8. GitHub does not allow `hashFiles()` in a job-level `if`, so the guard sits on the steps.

### Temporal container runs as root
- **Spec:** the `temporal` service mounts the named volume `temporal-data` at `/data` and uses `--db-filename /data/temporal.db`.
- **Did:** added `user: "0:0"` to the service.
- **Why:** the `temporalio/temporal:1.9.1` image runs as uid 1000 and does not create `/data`, so a new named volume is owned by root. The server then failed with "unable to open database file (14)". The container has no published ports beyond 7233 and 8233 and is used locally only. Railway volumes are root-owned as well, so the same applies at deploy time (M9).

### Entry points name their settings module
- **Spec:** nothing except `config.py` reads `os.environ`.
- **Did:** `manage.py`, `eingang/wsgi.py`, `eingang/worker.py` and `tools/export_openapi.py` call `os.environ.setdefault("DJANGO_SETTINGS_MODULE", "eingang.settings")`.
- **Why:** this is how Django finds its settings module. It writes a fixed value and reads no configuration, and every configuration value is still read only by `config.py`.

### Every error Django produces itself becomes problem+json
- **Did:** the request middleware replaces any error response (status 400 or higher) that is not already problem+json, for example a disallowed `Host` or an unknown route. Mapping: 404 `NOT_FOUND`, 403 `FORBIDDEN_ROLE`, 405 `METHOD_NOT_ALLOWED`, 5xx `INTERNAL`, anything else 400 `MALFORMED_REQUEST`. CSRF failures get their own documented code, `CSRF_FAILED`, through `CSRF_FAILURE_VIEW`. `APPEND_SLASH` is off, so no redirect is issued in place of a 404.
- **Why:** "every non-2xx response is problem+json", including responses that never reach a DRF view.

### `/docs` loads a pinned Swagger UI with its own CSP
- **Did:** Swagger UI `5.33.1` is loaded from jsdelivr, through drf-spectacular's split view, which serves the init script from the same URL instead of inline. The page's CSP allows scripts only from `'self'` and jsdelivr, and inline styles, which Swagger UI sets at runtime. Every other HTML response from the API gets `default-src 'none'; frame-ancestors 'none'` unless its view sets a policy.
- **Why:** "a restrictive Content-Security-Policy on any HTML the API serves". The browser loads the jsdelivr files only on the developer-facing `/docs` page, never in the app.

### `pnpm seed` and `pnpm db:reset` wait for their commands
- **Did:** both scripts call `manage.py seed_rules` and `manage.py seed_dev` (section "Sandbox" › "Local seed"). Those commands arrive in M3/M4. Until then `pnpm seed` fails with Django's "Unknown command", and `pnpm db:reset` checks that both commands exist before it drops anything, then stops with a message and changes nothing.
