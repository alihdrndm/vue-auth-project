import { describe, expect, it } from "vitest";

import {
  isFiltered,
  listParams,
  parseFrom,
  queryFromState,
  serializeFrom,
  stateFromQuery,
} from "./listParams";

describe("inbox list state", () => {
  it("defaults to Needs review, newest first, page 1", () => {
    expect(stateFromQuery({})).toEqual({
      tab: "needs_review",
      q: "",
      supplier: "",
      format: "",
      ordering: "-received_at",
      page: 1,
    });
  });

  it("drops unknown values from the URL", () => {
    const state = stateFromQuery({
      tab: "nonsense",
      ordering: "supplier",
      page: "-3",
    });
    expect(state.tab).toBe("needs_review");
    expect(state.ordering).toBe("-received_at");
    expect(state.page).toBe(1);
  });

  it("round-trips through the route query, leaving defaults out", () => {
    const state = stateFromQuery({
      tab: "all",
      q: " kessler ",
      supplier: "s-1",
      format: "Plain PDF",
      ordering: "due_date",
      page: "3",
    });
    expect(state.q).toBe("kessler");
    expect(queryFromState(state)).toEqual({
      tab: "all",
      q: "kessler",
      supplier: "s-1",
      format: "Plain PDF",
      ordering: "due_date",
      page: "3",
    });
    expect(queryFromState(stateFromQuery({}))).toEqual({ tab: "needs_review" });
  });

  it("builds the list request; All sends no status", () => {
    expect(listParams(stateFromQuery({ tab: "failed" }))).toEqual({
      status: "failed",
      ordering: "-received_at",
    });
    expect(
      listParams(stateFromQuery({ tab: "all", q: "x", page: "2" })),
    ).toEqual({ q: "x", ordering: "-received_at", page: 2 });
  });

  it("knows when search or filters narrow the list", () => {
    expect(isFiltered(stateFromQuery({ tab: "all" }))).toBe(false);
    expect(isFiltered(stateFromQuery({ format: "Plain PDF" }))).toBe(true);
  });

  it("serializes `from` for the review screen and reads it back", () => {
    const params = listParams(
      stateFromQuery({ tab: "approved", q: "a&b", page: "2" }),
    );
    const from = serializeFrom(params);
    expect(from).toBe("status=approved&q=a%26b&ordering=-received_at&page=2");
    expect(parseFrom(from)).toEqual(params);
    expect(parseFrom("status=bogus&ordering=x&page=0&other=1")).toEqual({});
  });
});
