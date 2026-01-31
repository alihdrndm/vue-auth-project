# Error codes

Every non-2xx response from the API is `application/problem+json` (RFC 9457):

```json
{
  "type": "https://github.com/alihdrndm/eingang/blob/main/docs/ERRORS.md#validation_failed",
  "title": "Validation failed",
  "status": 422,
  "detail": "One or more fields are invalid.",
  "code": "VALIDATION_FAILED",
  "instance": "0192f1c4-…",
  "errors": [{ "path": "email", "code": "invalid", "message": "Enter a valid email address." }]
}
```

`instance` is the request id (also sent as the `x-request-id` response header); quote it when reporting a problem. `errors` appears only on `VALIDATION_FAILED`. Some codes add extension members, listed below.

Each code has its own section, so `type` links straight to it.

## General

### VALIDATION_FAILED
`422`. The request body or query parameters failed validation. `errors` has one entry per field problem; `path` uses dots for nesting and `[n]` for list positions.

### MALFORMED_REQUEST
`400`. The request body could not be parsed (for example invalid JSON).

### NOT_FOUND
`404`. No resource exists at this path, or it belongs to another organisation (the API does not reveal which).

### METHOD_NOT_ALLOWED
`405`. The path exists but does not accept this HTTP method.

### NOT_ACCEPTABLE
`406`. The `Accept` header asks for a format the endpoint cannot produce.

### UNSUPPORTED_MEDIA_TYPE
`415`. The request body's `Content-Type` is not accepted by the endpoint (for example form data where JSON is expected). Uploaded files of the wrong kind get `UNSUPPORTED_FILE` instead.

### RATE_LIMITED
`429`. Too many requests from this client. The `Retry-After` header says how many seconds to wait.

### INTERNAL
`500`. An unexpected error on the server. The response never contains internal details; the request id in `instance` lets the operator find the log line.

### NOT_READY
`503`, from `GET /readyz` only. The database or Temporal did not answer within 2 seconds. Extension member `checks`: `{"database": "ok" | "unreachable", "temporal": "ok" | "unreachable"}`.

## Authentication and permissions

### NOT_AUTHENTICATED
`401`. The request needs a signed-in session.

### INVALID_CREDENTIALS
`400`, from `POST /api/v1/auth/login`. The email and password do not match an active user.

### SANDBOX_EXPIRED
`401`. The sandbox this session belongs to has expired and been signed out. Open a new sandbox.

### FORBIDDEN_ROLE
`403`. The signed-in user's role does not allow this action.

### SANDBOX_RESTRICTED
`403`. The action is not available in a sandbox (for example managing members).

### FOUR_EYES
`403`. The organisation requires four-eyes approval and this user reviewed the invoice, so someone else must decide.

## Uploads

### UNSUPPORTED_FILE
`415`. The file is neither a PDF nor a well-formed UBL or CII XML invoice (decided by content, never by file name), or the XML contains a DOCTYPE.

### FILE_TOO_LARGE
`413`. A file exceeds the upload limit (4 MB by default).

### TOO_MANY_FILES
`400`. More than 10 files in one upload request.

### SANDBOX_UPLOAD_LIMIT
`429`. The sandbox has reached its upload limit, or all sandboxes together have used their storage budget.

### SANDBOX_LIMIT
`429`, from `POST /api/v1/sandbox`. Too many sandboxes were opened recently, from this address or in total today.

## Documents and workflow

### INVALID_TRANSITION
`409`. The document's current status does not allow this action.

### BLOCKING_CHECKS
`409`, from `mark-reviewed`. Unresolved blocking checks remain; they are listed in the response.

### CHECK_NOT_RESOLVABLE
`409`. The check is information only, or it is already resolved.

### ALREADY_EXPORTED
`409`. An exported document cannot be deleted.

### NOTHING_TO_EXPORT
`409`. No approved, not-yet-exported invoices match the export request.

### NOT_AVAILABLE
`404`. The document has no such representation (visualisation, XML or extracted text).

### TEMPORAL_UNAVAILABLE
`503`. The upload was stored, but processing could not be started because Temporal is unreachable. It starts automatically when Temporal is back.
