import { vi } from "vitest";

import type { components } from "../api/schema";

export type Session = components["schemas"]["Session"];

/** A JSON response. */
export function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

/** An `application/problem+json` response with the members docs/ERRORS.md describes. */
export function problem(
  status: number,
  code: string,
  detail = "Something went wrong.",
  extra: Record<string, unknown> = {},
): Response {
  return new Response(
    JSON.stringify({
      title: code,
      status,
      detail,
      code,
      instance: "req-1",
      ...extra,
    }),
    { status, headers: { "Content-Type": "application/problem+json" } },
  );
}

export function noContent(): Response {
  return new Response(null, { status: 204 });
}

export function sessionBody(
  overrides: Partial<Session["organization"]> = {},
): Session {
  return {
    user: {
      id: "00000000-0000-0000-0000-000000000001",
      email: "anna@example.com",
      name: "Anna",
    },
    organization: {
      id: "00000000-0000-0000-0000-000000000002",
      name: "Holzwerk Brandt",
      kind: "standard",
      four_eyes: true,
      ...overrides,
    },
    role: "accountant",
  };
}

export interface RecordedRequest {
  method: string;
  path: string;
  headers: Headers;
  body: string;
}

type Handler = (request: RecordedRequest) => Response | Promise<Response>;

/**
 * Replaces `fetch` with `handler` and records every request. The handler sees the method, the path
 * (without origin), the headers and the body text.
 */
export function mockFetch(handler: Handler): RecordedRequest[] {
  const calls: RecordedRequest[] = [];
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const request =
        input instanceof Request
          ? input
          : new Request(new URL(String(input), location.origin), init);
      const recorded: RecordedRequest = {
        method: request.method,
        path: new URL(request.url).pathname,
        headers: request.headers,
        body: request.body ? await request.text() : "",
      };
      calls.push(recorded);
      return handler(recorded);
    },
  );
  vi.stubGlobal("fetch", fetchMock);
  return calls;
}

/** Sets or clears the CSRF cookie in jsdom. */
export function setCsrfCookie(value: string | null): void {
  document.cookie =
    value === null
      ? "csrftoken=; max-age=0; path=/"
      : `csrftoken=${value}; path=/`;
}
