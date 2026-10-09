import { describe, expect, it } from "vitest";

import {
  draftFrom,
  lockReason,
  meterLevel,
  meterPercent,
  type Organization,
  patchFrom,
  validateDraft,
} from "./settings";

const ORG: Organization = {
  id: "o-1",
  name: "Holzwerk Brandt GmbH",
  slug: "holzwerk-brandt",
  kind: "standard",
  vat_id: "DE143826055",
  four_eyes: true,
  duplicate_window_days: 30,
  reminder_after_days: 3,
};

describe("settings form", () => {
  it("sends only what changed and clears an emptied VAT ID", () => {
    const draft = { ...draftFrom(ORG), vat_id: " ", reminder_after_days: "7" };
    expect(patchFrom(ORG, draft)).toEqual({
      vat_id: null,
      reminder_after_days: 7,
    });
    expect(patchFrom(ORG, draftFrom(ORG))).toEqual({});
  });

  it("checks the name and the two windows", () => {
    const draft = {
      ...draftFrom(ORG),
      name: "",
      duplicate_window_days: "400",
      reminder_after_days: "2.5",
    };
    expect(Object.keys(validateDraft(draft)).sort()).toEqual([
      "duplicate_window_days",
      "name",
      "reminder_after_days",
    ]);
    expect(validateDraft(draftFrom(ORG))).toEqual({});
  });

  it("locks everything for non-admins and all but the name in a sandbox", () => {
    expect(lockReason("name", "accountant", false)).toBe(
      "Only admins can change settings.",
    );
    expect(lockReason("name", "admin", true)).toBeNull();
    expect(lockReason("four_eyes", "admin", true)).toBe(
      "Not available in the sandbox.",
    );
    expect(lockReason("four_eyes", "admin", false)).toBeNull();
  });

  it("reads the meter as under, near the limit, or reached", () => {
    expect(meterPercent("0.42", "2.00")).toBe(21);
    expect(meterPercent("3.00", "2.00")).toBe(100);
    expect(meterPercent("0.00", "0.00")).toBe(0);
    expect(meterLevel(21)).toBe("under");
    expect(meterLevel(85)).toBe("near");
    expect(meterLevel(100)).toBe("reached");
  });
});
