import { describe, expect, it } from "vitest";

import {
  firstSeenInvoice,
  groupIban,
  maskedIban,
  type SupplierIban,
} from "./iban";

describe("IBAN helpers", () => {
  it("masks and groups IBANs", () => {
    expect(maskedIban("4417")).toBe("•••• 4417");
    expect(maskedIban(undefined)).toBe("—");
    expect(groupIban("DE02120300000000202051")).toBe(
      "DE02 1203 0000 0000 2020 51",
    );
  });

  it("finds the invoice an IBAN was first seen on by its document", () => {
    const entry = {
      iban: "DE02120300000000202051",
      first_seen_invoice_id: "inv-7",
      first_seen_document_id: "doc-7",
      first_seen_at: "2026-10-07T10:05:00Z",
      last_seen_at: "2026-10-07T10:05:00Z",
      trusted: false,
      status: "new",
    } satisfies SupplierIban;
    const invoices = [
      {
        document_id: "doc-2",
        status: "needs_review" as const,
        received_at: "2026-10-09T07:58:00Z",
      },
      {
        document_id: "doc-7",
        status: "needs_review" as const,
        received_at: "2026-10-07T10:05:00.000000Z",
      },
    ];
    expect(
      firstSeenInvoice({ ...entry, first_seen_document_id: "doc-7" }, invoices)
        ?.document_id,
    ).toBe("doc-7");
    expect(
      firstSeenInvoice(
        { ...entry, first_seen_document_id: "doc-7" },
        invoices.slice(0, 1),
      ),
    ).toBeNull();
  });
});
