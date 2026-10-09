// What one row of the Approvals screen shows (design "Eingang App Screens", ?screen=approvals).
// Which decisions exist and whether this user may make them comes from `allowed_actions`.
import type { components } from "../../api/schema";
import { plural } from "../review-screen/format";

type DocumentSummary = components["schemas"]["DocumentSummary"];
type AllowedAction = components["schemas"]["AllowedAction"];

export type Decision = "approve" | "reject";

/** The decision actions of a row, in the design's order (Reject…, Approve). */
export function decisionActions(doc: DocumentSummary): AllowedAction[] {
  return (["reject", "approve"] as const).flatMap((name) => {
    const entry = doc.allowed_actions.find((item) => item.action === name);
    return entry ? [entry] : [];
  });
}

/** The distinct reasons of the row's disabled decisions, shown as text under the row. */
export function disabledReasons(doc: DocumentSummary): string[] {
  const reasons = decisionActions(doc)
    .filter((entry) => !entry.enabled)
    .map((entry) => entry.reason ?? "Not available.");
  return [...new Set(reasons)];
}

/** "None", "1 warning", "2 warnings"; open blocking checks are named too. */
export function warningsText(doc: DocumentSummary): string {
  const parts: string[] = [];
  if (doc.open_block_checks > 0)
    parts.push(plural(doc.open_block_checks, "blocking check"));
  if (doc.open_warn_checks > 0)
    parts.push(plural(doc.open_warn_checks, "warning"));
  return parts.length > 0 ? parts.join(", ") : "None";
}

/** The invoice number, or the file name before one is known. */
export function documentNumber(doc: DocumentSummary): string {
  return doc.invoice_number ?? doc.original_filename;
}
