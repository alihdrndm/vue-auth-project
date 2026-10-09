import { describe, expect, it } from "vitest";

import {
  type Check,
  noteCounter,
  noteError,
  openBlocking,
  resolveLabel,
  resolveState,
  sortChecks,
} from "./checks";

function check(overrides: Partial<Check> = {}): Check {
  return {
    id: overrides.check_id ?? "id",
    check_id: "C05",
    code: "BANK_DETAILS_CHANGED",
    severity: "block",
    message: "The bank account differs.",
    details: {},
    resolve: { enabled: true },
    ...overrides,
  };
}

describe("checks", () => {
  it("sorts open before resolved, then by severity and ID", () => {
    const sorted = sortChecks([
      check({ check_id: "C11", severity: "info" }),
      check({
        check_id: "C05",
        severity: "block",
        resolved_at: "2026-03-01T10:00:00Z",
      }),
      check({ check_id: "C04", severity: "info" }),
      check({ check_id: "C08", severity: "warn" }),
      check({ check_id: "C13", severity: "block" }),
    ]);
    expect(sorted.map((item) => item.check_id)).toEqual([
      "C13",
      "C08",
      "C04",
      "C11",
      "C05",
    ]);
  });

  it("counts only open blocking checks", () => {
    expect(
      openBlocking([
        check(),
        check({ resolved_at: "2026-03-01T10:00:00Z" }),
        check({ severity: "warn" }),
      ]),
    ).toBe(1);
  });

  it("validates the note length after trimming", () => {
    expect(noteError("  ok  ")).toBe("Write at least 5 characters.");
    expect(noteError("Called the supplier.")).toBeNull();
    expect(noteError("x".repeat(501))).toBe("Write at most 500 characters.");
    expect(noteCounter(" hello ")).toBe("5 / 500");
  });

  it("takes whether a check can be resolved from the API", () => {
    expect(resolveState(check())).toEqual({
      canResolve: true,
      reason: null,
      showButton: true,
    });
    expect(
      resolveState(
        check({
          check_id: "C15",
          resolve: {
            enabled: false,
            reason_code: "FORBIDDEN_ROLE",
            reason: "Your role (accountant) can't do this.",
          },
        }),
      ),
    ).toEqual({
      canResolve: false,
      reason: "Your role (accountant) can't do this.",
      showButton: true,
    });
    expect(resolveState(check({ severity: "info" })).showButton).toBe(false);
    expect(
      resolveState(check({ resolved_at: "2026-03-01T10:00:00Z" })).showButton,
    ).toBe(false);
  });

  it("calls resolving a failed validation 'accept anyway'", () => {
    expect(resolveLabel(check({ check_id: "C15" }))).toBe("Accept anyway…");
    expect(resolveLabel(check())).toBe("Resolve…");
  });
});
