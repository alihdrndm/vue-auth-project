// How the published evaluation (`GET /accuracy`, evals/latest.json) reads on the Accuracy pages.
// Every number comes from the API; nothing here is a sample value.
import type { components } from "../../api/schema";

export type AccuracyReportData = components["schemas"]["AccuracyReport"];
export type SystemResult = components["schemas"]["SystemResult"];
export type FieldScore = components["schemas"]["FieldScore"];

export const EVALS_URL =
  "https://github.com/alihdrndm/eingang/blob/main/docs/EVALS.md";

/** The scored fields in reading order, with the design's names. */
export const FIELD_LABELS: Record<string, string> = {
  invoice_number: "Invoice number",
  issue_date: "Invoice date",
  due_date: "Due date",
  currency: "Currency",
  "seller.name": "Supplier name",
  "seller.vat_id": "VAT ID",
  payee_iban: "IBAN",
  "buyer.name": "Buyer name",
  net_total: "Net",
  tax_total: "VAT",
  gross_total: "Gross",
  payable_amount: "Amount due",
};

const ORDER = Object.keys(FIELD_LABELS);

export function fieldLabel(key: string): string {
  return FIELD_LABELS[key] ?? key;
}

/** Every field any system was scored on, known fields first in reading order. */
export function fieldKeys(systems: readonly SystemResult[]): string[] {
  const keys = new Set(systems.flatMap((system) => Object.keys(system.fields)));
  return [...keys].sort((a, b) => {
    const ia = ORDER.indexOf(a);
    const ib = ORDER.indexOf(b);
    if (ia >= 0 && ib >= 0) return ia - ib;
    if (ia >= 0) return -1;
    if (ib >= 0) return 1;
    return a.localeCompare(b);
  });
}

export function isBaseline(system: SystemResult): boolean {
  return system.id.includes("baseline");
}

/** "Regex baseline (no AI)", "AI reader (gpt-…)" or the id as given. */
export function systemName(system: SystemResult): string {
  if (system.id === "regex-baseline") return "Regex baseline (no AI)";
  if (system.id.startsWith("llm"))
    return system.model ? `AI reader (${system.model})` : "AI reader";
  return system.id;
}

/** The system the per-field table details: the first one that is not a baseline. */
export function primarySystem(
  systems: readonly SystemResult[],
): SystemResult | null {
  return systems.find((system) => !isBaseline(system)) ?? systems[0] ?? null;
}

/** 0.2115 → "21.2 %"; absent → "—". */
export function percent(value: number | undefined | null): string {
  if (value === undefined || value === null || !Number.isFinite(value))
    return "—";
  return `${(value * 100).toFixed(1)} %`;
}

/** "95 % confidence interval 13.5–28.8 %". */
export function intervalText(system: SystemResult): string {
  const { ci_low: low, ci_high: high } = system.critical_correct;
  return `95 % confidence interval ${(low * 100).toFixed(1)}–${(high * 100).toFixed(1)} %`;
}

/** "$0.000" per invoice; a cost below a tenth of a cent keeps its first digits. */
export function costPerInvoice(system: SystemResult): string {
  const value = Number(system.usd_per_doc);
  if (!Number.isFinite(value)) return "—";
  if (value > 0 && value < 0.001) return `$${value.toPrecision(2)}`;
  return `$${value.toFixed(3)}`;
}

/** "9 Oct 2026". */
export function reportDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(date);
}
