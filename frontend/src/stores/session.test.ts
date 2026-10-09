import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, resetCsrfToken } from "../api/client";
import {
  json,
  mockFetch,
  noContent,
  problem,
  sessionBody,
  setCsrfCookie,
} from "../testing/http";
import { SANDBOX_EXPIRED_MESSAGE, useSessionStore } from "./session";

beforeEach(() => {
  setActivePinia(createPinia());
  resetCsrfToken();
  setCsrfCookie("token");
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("session store", () => {
  it("calls /auth/me only once", async () => {
    const calls = mockFetch(() => json(200, sessionBody()));
    const session = useSessionStore();

    const [first, second] = await Promise.all([session.load(), session.load()]);
    await session.load();

    expect(first?.user.email).toBe("anna@example.com");
    expect(second).toBe(first);
    expect(calls).toHaveLength(1);
    expect(session.role).toBe("accountant");
    expect(session.isSandbox).toBe(false);
    expect(session.hoursLeft).toBeNull();
  });

  it("treats 401 as signed out and remembers an expired sandbox", async () => {
    mockFetch(() => problem(401, "SANDBOX_EXPIRED", SANDBOX_EXPIRED_MESSAGE));
    const session = useSessionStore();

    expect(await session.load()).toBeNull();
    expect(session.loaded).toBe(true);
    expect(session.notice).toBe(SANDBOX_EXPIRED_MESSAGE);
    expect(session.takeNotice()).toBe(SANDBOX_EXPIRED_MESSAGE);
    expect(session.notice).toBeNull();
  });

  it("throws other errors and tries again on the next load", async () => {
    const responses = [problem(500, "INTERNAL"), json(200, sessionBody())];
    mockFetch(() => responses.shift() ?? noContent());
    const session = useSessionStore();

    await expect(session.load()).rejects.toBeInstanceOf(ApiError);
    expect(session.loaded).toBe(false);
    expect(await session.load()).not.toBeNull();
  });

  it("signs in and out", async () => {
    const calls = mockFetch(({ path }) =>
      path === "/api/v1/auth/logout" ? noContent() : json(200, sessionBody()),
    );
    const session = useSessionStore();

    await session.signIn("anna@example.com", "secret");
    expect(session.me?.user.name).toBe("Anna");
    expect(JSON.parse(calls[0]?.body ?? "{}")).toEqual({
      email: "anna@example.com",
      password: "secret",
    });

    await session.signOut();
    expect(session.me).toBeNull();
    expect(session.loaded).toBe(true);
  });

  it("surfaces INVALID_CREDENTIALS as an ApiError", async () => {
    mockFetch(() =>
      problem(
        400,
        "INVALID_CREDENTIALS",
        "The email address or password is not correct.",
      ),
    );
    const session = useSessionStore();

    await expect(
      session.signIn("anna@example.com", "wrong"),
    ).rejects.toMatchObject({
      code: "INVALID_CREDENTIALS",
      detail: "The email address or password is not correct.",
    });
    expect(session.me).toBeNull();
  });

  it("opens a sandbox and counts the hours left", async () => {
    vi.useFakeTimers({
      now: new Date("2026-10-10T10:00:00Z"),
      toFake: ["Date"],
    });
    mockFetch(() =>
      json(
        201,
        sessionBody({ kind: "sandbox", expires_at: "2026-10-11T08:30:00Z" }),
      ),
    );
    const session = useSessionStore();

    await session.openSandbox();

    expect(session.isSandbox).toBe(true);
    expect(session.hoursLeft).toBe(23);
  });

  it("surfaces SANDBOX_LIMIT with its detail", async () => {
    mockFetch(() =>
      problem(429, "SANDBOX_LIMIT", "Too many sandboxes were opened recently."),
    );
    const session = useSessionStore();

    await expect(session.openSandbox()).rejects.toMatchObject({
      status: 429,
      code: "SANDBOX_LIMIT",
      detail: "Too many sandboxes were opened recently.",
    });
    expect(session.me).toBeNull();
  });
});
