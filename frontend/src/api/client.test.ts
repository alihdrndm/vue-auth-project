import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  json,
  mockFetch,
  noContent,
  problem,
  sessionBody,
  setCsrfCookie,
} from "../testing/http";
import {
  api,
  ApiError,
  resetCsrfToken,
  setAuthFailureHandler,
  unwrap,
} from "./client";

beforeEach(() => {
  resetCsrfToken();
  setCsrfCookie(null);
  setAuthFailureHandler(null);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("CSRF", () => {
  it("fetches the token once and sends it on unsafe requests only", async () => {
    const calls = mockFetch(({ path }) => {
      if (path === "/api/v1/auth/csrf") {
        setCsrfCookie("token-1");
        return noContent();
      }
      return json(200, sessionBody());
    });

    await api.GET("/api/v1/auth/me");
    await api.POST("/api/v1/auth/login", {
      body: { email: "a@example.com", password: "pw" },
    });
    await api.POST("/api/v1/auth/logout");

    expect(calls.map((call) => call.path)).toEqual([
      "/api/v1/auth/me",
      "/api/v1/auth/csrf",
      "/api/v1/auth/login",
      "/api/v1/auth/logout",
    ]);
    expect(calls[0]?.headers.get("X-CSRFToken")).toBeNull();
    expect(calls[2]?.headers.get("X-CSRFToken")).toBe("token-1");
    expect(calls[2]?.body).toBe(
      JSON.stringify({ email: "a@example.com", password: "pw" }),
    );
    expect(calls[3]?.headers.get("X-CSRFToken")).toBe("token-1");
  });

  it("reads the cookie again after the server rotated it", async () => {
    setCsrfCookie("before");
    const calls = mockFetch(({ path }) => {
      if (path === "/api/v1/auth/login") setCsrfCookie("after");
      return json(200, sessionBody());
    });

    await api.POST("/api/v1/auth/login", {
      body: { email: "a@example.com", password: "pw" },
    });
    await api.POST("/api/v1/sandbox");

    expect(calls.map((call) => call.headers.get("X-CSRFToken"))).toEqual([
      "before",
      "after",
    ]);
  });

  it("refreshes the token and retries once on 403 CSRF_FAILED", async () => {
    setCsrfCookie("stale");
    let attempts = 0;
    const calls = mockFetch(({ path }) => {
      if (path === "/api/v1/auth/csrf") {
        setCsrfCookie("fresh");
        return noContent();
      }
      attempts += 1;
      return attempts === 1
        ? problem(403, "CSRF_FAILED")
        : json(200, sessionBody());
    });

    const result = await api.POST("/api/v1/auth/login", {
      body: { email: "a@example.com", password: "pw" },
    });

    expect(unwrap(result).role).toBe("accountant");
    expect(
      calls.map((call) => [call.path, call.headers.get("X-CSRFToken")]),
    ).toEqual([
      ["/api/v1/auth/login", "stale"],
      ["/api/v1/auth/csrf", null],
      ["/api/v1/auth/login", "fresh"],
    ]);
    expect(calls[2]?.body).toBe(
      JSON.stringify({ email: "a@example.com", password: "pw" }),
    );
  });

  it("retries only once", async () => {
    setCsrfCookie("stale");
    const calls = mockFetch(({ path }) =>
      path === "/api/v1/auth/csrf" ? noContent() : problem(403, "CSRF_FAILED"),
    );

    const result = await api.POST("/api/v1/auth/logout");

    expect(() => unwrap(result)).toThrow(ApiError);
    expect(
      calls.filter((call) => call.path === "/api/v1/auth/logout"),
    ).toHaveLength(2);
  });

  it("does not retry other 403 problems", async () => {
    setCsrfCookie("token");
    const calls = mockFetch(() => problem(403, "FORBIDDEN_ROLE"));

    await api.POST("/api/v1/documents/{document_id}/reopen", {
      params: { path: { document_id: "abc" } },
    });

    expect(calls).toHaveLength(1);
  });
});

describe("problems", () => {
  it("turns a problem+json body into an ApiError with every member", async () => {
    mockFetch(() =>
      problem(422, "VALIDATION_FAILED", "One or more fields are invalid.", {
        title: "Validation failed",
        errors: [
          {
            path: "email",
            code: "invalid",
            message: "Enter a valid email address.",
          },
        ],
        checks: ["c1"],
      }),
    );

    const result = await api.GET("/api/v1/auth/me");
    let error: unknown;
    try {
      unwrap(result);
    } catch (caught) {
      error = caught;
    }

    expect(error).toBeInstanceOf(ApiError);
    const apiError = error as ApiError;
    expect(apiError.status).toBe(422);
    expect(apiError.code).toBe("VALIDATION_FAILED");
    expect(apiError.title).toBe("Validation failed");
    expect(apiError.detail).toBe("One or more fields are invalid.");
    expect(apiError.instance).toBe("req-1");
    expect(apiError.errors).toEqual([
      {
        path: "email",
        code: "invalid",
        message: "Enter a valid email address.",
      },
    ]);
    expect(apiError.extra).toEqual({ checks: ["c1"] });
  });

  it("copes with a body that is not a problem", () => {
    const error = ApiError.fromBody(502, "Bad gateway");
    expect(error.status).toBe(502);
    expect(error.code).toBe("HTTP_502");
    expect(error.detail).toBe("Bad gateway");
    expect(error.errors).toEqual([]);
  });
});

describe("authentication failures", () => {
  it("reports 401 codes to the handler and leaves 403 alone", async () => {
    const handler = vi.fn();
    setAuthFailureHandler(handler);
    setCsrfCookie("token");
    const responses = [
      problem(401, "NOT_AUTHENTICATED"),
      problem(401, "SANDBOX_EXPIRED"),
      problem(403, "FORBIDDEN_ROLE"),
    ];
    mockFetch(() => responses.shift() ?? noContent());

    await api.GET("/api/v1/stats");
    await api.GET("/api/v1/stats");
    await api.GET("/api/v1/stats");

    expect(handler.mock.calls).toEqual([
      ["NOT_AUTHENTICATED"],
      ["SANDBOX_EXPIRED"],
    ]);
  });
});
