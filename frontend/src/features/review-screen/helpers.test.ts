import { describe, expect, it } from "vitest";

import { ApiError } from "../../api/client";
import { headerActions, problemMessage, successMessage } from "./actions";
import { formatDate, formatMoney, formatRate } from "./format";
import { serializeFrom } from "../inbox/listParams";
import { decodeFrom, neighbour, stepMessage } from "./navigation";
import { configRelease, issueGroups, validationText } from "./validation";
import { detail, summary } from "./testing";

describe("format", () => {
  it("writes amounts the German way, credit notes with a minus sign", () => {
    expect(formatMoney("1190.00")).toBe("1.190,00 €");
    expect(formatMoney("58.31", "EUR", true)).toBe("−58,31 €");
    expect(formatMoney("-58.31")).toBe("−58,31 €");
    expect(formatMoney("12.5", "USD")).toBe("12,50 USD");
    expect(formatMoney(undefined)).toBe("—");
  });

  it("writes dates and rates as designed", () => {
    expect(formatDate("2026-10-23")).toBe("23 Oct 2026");
    expect(formatRate("19.00")).toBe("19");
    expect(formatRate("7.5")).toBe("7,5");
  });
});

describe("actions", () => {
  it("keeps the design's order and leaves out panel actions", () => {
    const actions = headerActions([
      { action: "delete", enabled: true },
      { action: "edit_fields", enabled: true },
      { action: "reject", enabled: true },
      { action: "approve", enabled: false, reason: "No." },
    ]);
    expect(actions.map((action) => action.action)).toEqual([
      "approve",
      "reject",
      "delete",
    ]);
  });

  it("says how many blocking checks remain", () => {
    const error = ApiError.fromBody(409, {
      code: "BLOCKING_CHECKS",
      title: "Blocking checks remain",
      detail: "Resolve 2 blocking checks first.",
      status: 409,
      checks: ["a", "b"],
    });
    expect(problemMessage(error)).toBe(
      "Blocking checks remain. Resolve 2 blocking checks first.",
    );
    expect(successMessage("approve", "RE-1")).toBe("You approved RE-1.");
  });
});

describe("navigation", () => {
  it("round-trips the inbox list params through ?from=", () => {
    const from = serializeFrom({
      status: "needs_review",
      q: "kessler",
      page: 2,
    });
    expect(decodeFrom(from)).toEqual({
      status: "needs_review",
      q: "kessler",
      page: 2,
    });
    expect(decodeFrom(undefined)).toBeNull();
    expect(decodeFrom("evil=1")).toEqual({});
  });

  it("steps through the list and wraps at the ends", () => {
    const list = [summary("a"), summary("b"), summary("c")];
    expect(neighbour(list, "a", 1)).toMatchObject({
      document: { id: "b" },
      wrapped: false,
    });
    expect(neighbour(list, "c", 1)).toMatchObject({
      document: { id: "a" },
      wrapped: true,
    });
    expect(neighbour(list, "a", -1)).toMatchObject({
      document: { id: "c" },
      wrapped: true,
    });
    expect(neighbour([summary("a")], "a", 1)).toBeNull();
    expect(neighbour(list, "gone", 1)).toMatchObject({ document: { id: "a" } });
  });

  it("names the next invoice in the toast", () => {
    const target = { document: summary("b"), wrapped: false };
    expect(stepMessage(target, 1)).toBe("Next: Supplier b, NR-b");
    expect(stepMessage({ ...target, wrapped: true }, -1)).toBe(
      "Back to the end of the list. Previous: Supplier b, NR-b",
    );
  });
});

describe("validation", () => {
  it("names the rule release and the result", () => {
    const engine = "xrechnung-config 2026-01-31; CEN 1.3.13; saxonche 12.5";
    expect(configRelease(engine)).toBe("2026-01-31");
    const doc = detail({
      validation: {
        status: "invalid",
        engine,
        fatal_count: 1,
        warning_count: 0,
        issues: [],
      },
    });
    expect(validationText(doc)).toBe(
      "Checked with the official XRechnung rules (KoSIT 2026-01-31). 1 error.",
    );
  });

  it("groups issues worst first and leaves out empty groups", () => {
    const issue = (severity: "fatal" | "warning" | "information") => ({
      rule_id: "R",
      severity,
      message: "m",
      location: "/",
      test: "t",
      source: "en16931",
    });
    const groups = issueGroups([
      issue("information"),
      issue("fatal"),
      issue("fatal"),
    ]);
    expect(groups.map((group) => [group.title, group.issues.length])).toEqual([
      ["Errors", 2],
      ["Information", 1],
    ]);
  });
});
