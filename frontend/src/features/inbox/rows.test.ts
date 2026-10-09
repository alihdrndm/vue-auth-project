import { describe, expect, it } from "vitest";

import {
  einvoiceLook,
  formatDue,
  formatGross,
  formatOptions,
  highlight,
  isOverdue,
  KNOWN_FORMATS,
  stepText,
  today,
  validationLook,
  type DocumentSummary,
} from "./rows";

function doc(overrides: Partial<DocumentSummary> = {}): DocumentSummary {
  return {
    id: "d-1",
    original_filename: "a.pdf",
    status: "needs_review",
    received_at: "2026-10-07T14:30:00Z",
    open_block_checks: 0,
    open_warn_checks: 0,
    allowed_actions: [],
    ...overrides,
  };
}

const plain = (text: string): string => text.replace(/ /g, " ");

describe("inbox rows", () => {
  it("formats gross in German notation, credit notes negative", () => {
    expect(plain(formatGross(doc({ gross_total: "1190.00" })))).toBe(
      "1.190,00 €",
    );
    expect(
      plain(formatGross(doc({ gross_total: "58.31", type_code: 381 }))),
    ).toBe("−58,31 €");
    expect(formatGross(doc())).toBe("—");
  });

  it("formats due dates and finds overdue ones", () => {
    expect(formatDue("2026-10-23")).toBe("23 Oct 2026");
    expect(formatDue(undefined)).toBe("—");
    expect(isOverdue(doc({ due_date: "2026-10-01" }), "2026-10-09")).toBe(true);
    expect(
      isOverdue(
        doc({ due_date: "2026-10-01", status: "approved" }),
        "2026-10-09",
      ),
    ).toBe(false);
    expect(today(new Date(2026, 0, 5))).toBe("2026-01-05");
  });

  it("words e-invoice and validation chips", () => {
    expect(einvoiceLook(doc({ is_einvoice: true }))?.label).toBe("E-invoice");
    expect(einvoiceLook(doc({ is_einvoice: false }))?.label).toBe(
      "Not an e-invoice",
    );
    expect(einvoiceLook(doc())).toBeNull();
    expect(validationLook(doc({ validation_status: "warnings" }))?.label).toBe(
      "Valid with warnings",
    );
    expect(validationLook(doc({ validation_status: "invalid" }))?.tone).toBe(
      "block",
    );
  });

  it("describes the processing step", () => {
    expect(
      stepText(doc({ status: "processing", processing_step: "extract" })),
    ).toBe("Step 3 of 4: reading with AI");
    expect(stepText(doc({ status: "processing" }))).toBe("Starting");
    expect(stepText(doc({ status: "received" }))).toBeNull();
    expect(stepText(doc({ processing_step: "check" }))).toBeNull();
  });

  it("lists known formats first, then labels seen in the list", () => {
    const options = formatOptions([
      "Plain PDF",
      "XRechnung · UBL · credit note",
    ]);
    expect(options.slice(0, KNOWN_FORMATS.length)).toEqual(KNOWN_FORMATS);
    expect(options.at(-1)).toBe("XRechnung · UBL · credit note");
    expect(options.filter((label) => label === "Plain PDF")).toHaveLength(1);
  });

  it("splits text around the search match", () => {
    expect(highlight("Elektro Kessler GmbH", "kessler")).toEqual([
      { text: "Elektro ", match: false },
      { text: "Kessler", match: true },
      { text: " GmbH", match: false },
    ]);
    expect(highlight("abc", "")).toEqual([{ text: "abc", match: false }]);
  });
});
