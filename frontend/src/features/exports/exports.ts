// The export formats as the design words them (design "Eingang App Screens" ?screen=exports),
// and who may export (HANDOFF: `POST /exports` is for admins and accountants).
import type { components } from "../../api/schema";
import { plural } from "../review-screen/format";

export type ExportFormat = components["schemas"]["FormatEnum"];
export type Role = components["schemas"]["RoleEnum"];

export interface FormatLook {
  value: ExportFormat;
  label: string;
  help: string;
}

export const FORMATS: FormatLook[] = [
  {
    value: "csv_invoices",
    label: "CSV, one row per invoice",
    help: "For the tax advisor’s import.",
  },
  {
    value: "csv_lines",
    label: "CSV, one row per invoice line",
    help: "With net, VAT rate and VAT per line.",
  },
  {
    value: "zip_bundle",
    label: "ZIP bundle with originals",
    help: "Both CSVs plus every original XML and PDF.",
  },
];

export function formatLabel(format: ExportFormat): string {
  return FORMATS.find((look) => look.value === format)?.label ?? format;
}

export const ROLE_LABEL: Record<Role, string> = {
  admin: "Admin",
  accountant: "Accountant",
  approver: "Approver",
  viewer: "Viewer",
};

/** Why this role can't export, or null when it can. Mirrors the API's FORBIDDEN_ROLE. */
export function exportBlockedReason(role: Role | null): string | null {
  if (role === "admin" || role === "accountant") return null;
  if (role === null) return "Sign in to export.";
  return `Your role (${ROLE_LABEL[role]}) can't export. Admins and accountants can.`;
}

/** "1 invoice ready", "7 invoices ready", "Nothing ready to export". */
export function readyText(count: number): string {
  return count > 0
    ? `${plural(count, "invoice")} ready`
    : "Nothing ready to export";
}

/** The toast after an export ("Export ready. 1 invoice moved to Exported."). */
export function exportedMessage(rowCount: number): string {
  return `Export ready. ${plural(rowCount, "invoice")} moved to Exported.`;
}
