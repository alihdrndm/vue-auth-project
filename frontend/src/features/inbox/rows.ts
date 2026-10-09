// How one document summary reads in the inbox (design "Eingang App Inbox"): amounts in German
// notation with credit notes negative, due dates with the overdue marker, e-invoice and
// validation chips, open checks and the live processing step.
import type { components } from "../../api/schema";
import type { IconName } from "../../components/ui/icons";

export type DocumentSummary = components["schemas"]["DocumentSummary"];

export type Tone = "ok" | "warn" | "block" | "neutral" | "info";

export interface ChipLook {
  label: string;
  icon: IconName;
  tone: Tone;
}

/** UNTDID 1001 type code of a credit note. */
export const CREDIT_NOTE_TYPE_CODE = 381;

const MINUS = "−";

/** "1.190,00 €"; credit notes (type code 381) as "−58,31 €"; "—" when unknown. */
export function formatGross(doc: DocumentSummary): string {
  if (doc.gross_total === undefined) return "—";
  const value = Number(doc.gross_total);
  if (!Number.isFinite(value)) return "—";
  const signed =
    doc.type_code === CREDIT_NOTE_TYPE_CODE ? -Math.abs(value) : value;
  const text = new Intl.NumberFormat("de-DE", {
    style: "currency",
    currency: doc.currency ?? "EUR",
  }).format(Math.abs(signed));
  return signed < 0 ? `${MINUS}${text}` : text;
}

const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

/** "2026-10-23" → "23 Oct 2026"; "—" when unknown. */
export function formatDue(date: string | undefined): string {
  const match = date ? /^(\d{4})-(\d{2})-(\d{2})$/.exec(date) : null;
  if (!match) return "—";
  const [, year, month, day] = match;
  return `${day} ${MONTHS[Number(month) - 1] ?? month} ${year}`;
}

/** The local calendar date as YYYY-MM-DD. */
export function today(now: Date = new Date()): string {
  const pad = (value: number): string => String(value).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

/** Past due and still waiting on someone (needs review or awaiting approval). */
export function isOverdue(doc: DocumentSummary, todayIso: string): boolean {
  return (
    doc.due_date !== undefined &&
    doc.due_date < todayIso &&
    (doc.status === "needs_review" || doc.status === "awaiting_approval")
  );
}

export function einvoiceLook(doc: DocumentSummary): ChipLook | null {
  if (doc.is_einvoice === undefined) return null;
  return doc.is_einvoice
    ? { label: "E-invoice", icon: "check", tone: "ok" }
    : { label: "Not an e-invoice", icon: "info", tone: "neutral" };
}

const VALIDATION: Record<string, ChipLook> = {
  valid: { label: "Valid", icon: "circle-check", tone: "ok" },
  warnings: { label: "Valid with warnings", icon: "triangle", tone: "warn" },
  invalid: { label: "Invalid", icon: "octagon", tone: "block" },
  not_applicable: { label: "Not applicable", icon: "minus", tone: "neutral" },
};

export function validationLook(doc: DocumentSummary): ChipLook | null {
  return doc.validation_status
    ? (VALIDATION[doc.validation_status] ?? null)
    : null;
}

/** How often the list refreshes while a row is still being processed. */
export const PROCESSING_POLL_MS = 2_000;

export function isProcessing(doc: DocumentSummary): boolean {
  return doc.status === "received" || doc.status === "processing";
}

/** The four processing steps and how the design words the running one. */
export const STEPS = [
  { key: "detect", now: "detecting the format" },
  { key: "validate", now: "checking the e-invoice rules" },
  { key: "extract", now: "reading with AI" },
  { key: "check", now: "running checks" },
] as const;

/** "Step 2 of 4: checking the e-invoice rules", or null when nothing runs. */
export function stepText(doc: DocumentSummary): string | null {
  if (!isProcessing(doc)) return null;
  if (doc.processing_step === "done") return "Finishing";
  const index = STEPS.findIndex((step) => step.key === doc.processing_step);
  if (index < 0) return doc.status === "processing" ? "Starting" : null;
  return `Step ${index + 1} of ${STEPS.length}: ${STEPS[index]?.now ?? ""}`;
}

/** Labels shown first in the format filter: every label the API gives a supported file. */
export const KNOWN_FORMATS = [
  "XRechnung · UBL",
  "XRechnung · CII",
  "EN 16931 · UBL",
  "EN 16931 · CII",
  "ZUGFeRD · EN 16931",
  "ZUGFeRD · XRECHNUNG",
  "ZUGFeRD · EXTENDED",
  "ZUGFeRD · BASIC",
  "ZUGFeRD · BASIC WL",
  "ZUGFeRD · MINIMUM",
  "ZUGFeRD 1",
  "Hybrid PDF (unsupported)",
  "Plain PDF",
  "Scanned PDF",
];

/** The known labels, then any other label seen in the list (e.g. "… · credit note"), sorted. */
export function formatOptions(seen: Iterable<string>): string[] {
  const extra = [...new Set(seen)]
    .filter((label) => label && !KNOWN_FORMATS.includes(label))
    .sort((a, b) => a.localeCompare(b, "de"));
  return [...KNOWN_FORMATS, ...extra];
}

export interface TextPart {
  text: string;
  match: boolean;
}

/** Splits `text` around the first case-insensitive match of `query`, for `<mark>`. */
export function highlight(text: string, query: string): TextPart[] {
  const needle = query.trim().toLowerCase();
  const index = needle ? text.toLowerCase().indexOf(needle) : -1;
  if (index < 0) return [{ text, match: false }];
  return [
    { text: text.slice(0, index), match: false },
    { text: text.slice(index, index + needle.length), match: true },
    { text: text.slice(index + needle.length), match: false },
  ].filter((part) => part.text !== "");
}
