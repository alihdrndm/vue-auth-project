// Test fixtures for the review screen: a document detail and list rows with sensible defaults.
import type { components } from "../../api/schema";

type DocumentDetail = components["schemas"]["DocumentDetail"];
type DocumentSummary = components["schemas"]["DocumentSummary"];

export const DOC_ID = "00000000-0000-0000-0000-0000000000d1";

export function detail(
  overrides: Partial<DocumentDetail> = {},
): DocumentDetail {
  return {
    id: DOC_ID,
    original_filename: "rechnung.pdf",
    kind: "pdf_text",
    format_label: "Plain PDF",
    status: "needs_review",
    received_at: "2026-10-06T15:44:00Z",
    invoice_number: "2026-1043",
    supplier_name: "Druckerei Sommer GmbH",
    gross_total: "1547.00",
    currency: "EUR",
    due_date: "2026-10-20",
    is_einvoice: false,
    validation_status: "not_applicable",
    open_block_checks: 0,
    open_warn_checks: 0,
    allowed_actions: [],
    source: "upload",
    size_bytes: 1000,
    text_truncated: false,
    lines: [],
    checks: [],
    approvals: [],
    events: [],
    ...overrides,
  };
}

export function summary(id: string): DocumentSummary {
  return {
    id,
    original_filename: `${id}.pdf`,
    status: "needs_review",
    received_at: "2026-10-06T15:44:00Z",
    invoice_number: `NR-${id}`,
    supplier_name: `Supplier ${id}`,
    open_block_checks: 0,
    open_warn_checks: 0,
    allowed_actions: [],
  };
}
