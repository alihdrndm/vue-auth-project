import createClient from "openapi-fetch";

import type { paths } from "./schema";

/** One field problem inside a `VALIDATION_FAILED` problem. */
export interface ProblemFieldError {
  path: string;
  code: string;
  message: string;
}

/** An `application/problem+json` body (RFC 9457), as documented in docs/ERRORS.md. */
export interface Problem {
  type?: string;
  title: string;
  status: number;
  detail: string;
  code: string;
  instance?: string;
  errors?: ProblemFieldError[];
  [extension: string]: unknown;
}

const KNOWN_MEMBERS = new Set([
  "type",
  "title",
  "status",
  "detail",
  "code",
  "instance",
  "errors",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function asString(value: unknown, fallback: string): string {
  return typeof value === "string" && value !== "" ? value : fallback;
}

/** A non-2xx API response, carrying the problem's members. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly title: string;
  readonly detail: string;
  readonly instance?: string;
  readonly errors: ProblemFieldError[];
  /** Extension members such as `checks` on `BLOCKING_CHECKS`. */
  readonly extra: Record<string, unknown>;

  constructor(problem: Problem) {
    super(problem.detail || problem.title);
    this.name = "ApiError";
    this.status = problem.status;
    this.code = problem.code;
    this.title = problem.title;
    this.detail = problem.detail;
    this.instance = problem.instance;
    this.errors = problem.errors ?? [];
    this.extra = Object.fromEntries(
      Object.entries(problem).filter(([key]) => !KNOWN_MEMBERS.has(key)),
    );
  }

  /** Builds an error from a status and whatever body came back (problem JSON, text or nothing). */
  static fromBody(status: number, body: unknown): ApiError {
    if (isRecord(body)) {
      const errors = Array.isArray(body.errors)
        ? body.errors.filter(isRecord).map((entry) => ({
            path: asString(entry.path, ""),
            code: asString(entry.code, ""),
            message: asString(entry.message, ""),
          }))
        : undefined;
      return new ApiError({
        ...body,
        type: typeof body.type === "string" ? body.type : undefined,
        instance: typeof body.instance === "string" ? body.instance : undefined,
        status: typeof body.status === "number" ? body.status : status,
        code: asString(body.code, `HTTP_${status}`),
        title: asString(body.title, "Request failed"),
        detail: asString(body.detail, ""),
        errors,
      });
    }
    return new ApiError({
      status,
      code: `HTTP_${status}`,
      title: "Request failed",
      detail: typeof body === "string" ? body.slice(0, 500) : "",
    });
  }
}

/** Returns the `data` of an openapi-fetch result, or throws its problem as an `ApiError`. */
export function unwrap<T>(result: {
  data?: T;
  error?: unknown;
  response: Response;
}): T {
  if (!result.response.ok) {
    throw ApiError.fromBody(result.response.status, result.error);
  }
  return result.data as T;
}

// ---------------------------------------------------------------------------
// Authentication failures

export type AuthFailureCode = "NOT_AUTHENTICATED" | "SANDBOX_EXPIRED";
export type AuthFailureHandler = (code: AuthFailureCode) => void;

let authFailureHandler: AuthFailureHandler | null = null;

/** Registers the one function told about every `401` response. 403 responses never reach it. */
export function setAuthFailureHandler(
  handler: AuthFailureHandler | null,
): void {
  authFailureHandler = handler;
}

async function problemCode(response: Response): Promise<string | undefined> {
  try {
    const body: unknown = await response.clone().json();
    return isRecord(body) && typeof body.code === "string"
      ? body.code
      : undefined;
  } catch {
    return undefined;
  }
}

// ---------------------------------------------------------------------------
// CSRF

export const API_PREFIX = "/api/v1";
const CSRF_COOKIE = "csrftoken";
const CSRF_HEADER = "X-CSRFToken";
const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS", "TRACE"]);

let csrfToken: string | null = null;
let csrfRequest: Promise<string | null> | null = null;

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  for (const part of document.cookie.split(";")) {
    const [key, ...value] = part.trim().split("=");
    if (key === name) return decodeURIComponent(value.join("="));
  }
  return null;
}

function apiOrigin(): string {
  return globalThis.location?.origin ?? "";
}

async function fetchCsrfToken(): Promise<string | null> {
  const response = await globalThis.fetch(
    `${apiOrigin()}${API_PREFIX}/auth/csrf`,
    {
      credentials: "same-origin",
    },
  );
  if (!response.ok)
    throw ApiError.fromBody(response.status, await response.text());
  csrfToken = readCookie(CSRF_COOKIE);
  return csrfToken;
}

/**
 * The current CSRF token. The cookie is read on every call because Django rotates the token at
 * sign-in; `GET /auth/csrf` is only called when no token is known yet, or when `refresh` is set.
 */
export async function currentCsrfToken(
  refresh = false,
): Promise<string | null> {
  if (!refresh) {
    const token = readCookie(CSRF_COOKIE) ?? csrfToken;
    if (token) return token;
  }
  csrfRequest ??= fetchCsrfToken().finally(() => {
    csrfRequest = null;
  });
  return csrfRequest;
}

/** Forgets the cached token. Tests use it; nothing else needs to. */
export function resetCsrfToken(): void {
  csrfToken = null;
  csrfRequest = null;
}

async function withCsrf(request: Request, refresh: boolean): Promise<Request> {
  const token = await currentCsrfToken(refresh);
  const headers = new Headers(request.headers);
  if (token) headers.set(CSRF_HEADER, token);
  return new Request(request, { headers });
}

/**
 * The fetch used by the API client: adds the CSRF header to unsafe requests, refreshes the token
 * and retries once on `403 CSRF_FAILED`, and reports `401` responses to the auth failure handler.
 */
export async function apiFetch(input: Request): Promise<Response> {
  let response: Response;
  if (SAFE_METHODS.has(input.method.toUpperCase())) {
    response = await globalThis.fetch(input);
  } else {
    const spare = input.clone();
    response = await globalThis.fetch(await withCsrf(input, false));
    if (
      response.status === 403 &&
      (await problemCode(response)) === "CSRF_FAILED"
    ) {
      response = await globalThis.fetch(await withCsrf(spare, true));
    }
  }

  if (response.status === 401 && authFailureHandler) {
    const code = await problemCode(response);
    authFailureHandler(
      code === "SANDBOX_EXPIRED" ? "SANDBOX_EXPIRED" : "NOT_AUTHENTICATED",
    );
  }
  return response;
}

/** The typed API client. Paths in the schema already start with `/api/v1`. */
export const api = createClient<paths>({
  baseUrl: apiOrigin(),
  credentials: "same-origin",
  fetch: apiFetch,
});
