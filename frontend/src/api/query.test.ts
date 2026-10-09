import { describe, expect, it } from "vitest";

import { ApiError } from "./client";
import { createQueryClient, queryKeys, shouldRetry } from "./query";

describe("query defaults", () => {
  it("never retries client errors", () => {
    const error = ApiError.fromBody(404, {
      code: "NOT_FOUND",
      title: "Not found",
      status: 404,
    });
    expect(shouldRetry(0, error)).toBe(false);
  });

  it("retries network failures and server errors once", () => {
    const serverError = ApiError.fromBody(503, {
      code: "TEMPORAL_UNAVAILABLE",
      status: 503,
    });
    expect(shouldRetry(0, serverError)).toBe(true);
    expect(shouldRetry(1, serverError)).toBe(false);
    expect(shouldRetry(0, new TypeError("Failed to fetch"))).toBe(true);
    expect(shouldRetry(1, new TypeError("Failed to fetch"))).toBe(false);
  });

  it("stops polling while the tab is hidden", () => {
    const options = createQueryClient().getDefaultOptions().queries;
    expect(options?.refetchIntervalInBackground).toBe(false);
  });

  it("nests keys so a group can be invalidated at once", () => {
    expect(queryKeys.documents.list({ status: "approved" })).toEqual([
      "documents",
      "list",
      { status: "approved" },
    ]);
    expect(queryKeys.documents.detail("d1").slice(0, 1)).toEqual(
      queryKeys.documents.all(),
    );
    expect(queryKeys.rule("BR-DE-15")).toEqual(["rules", "BR-DE-15"]);
  });
});
