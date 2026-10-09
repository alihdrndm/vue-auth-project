// The Validation section's words: the chip (design "ValidationChip") and the line under the title.
import type { components } from "../../api/schema";
import type { IconName } from "../../components/ui/icons";
import { plural } from "./format";

type DocumentDetail = components["schemas"]["DocumentDetail"];
type Issue = components["schemas"]["Issue"];
export type IssueSeverity = Issue["severity"];

export interface ValidationLook {
  label: string;
  icon: IconName;
  tone: "ok" | "warn" | "block" | "neutral";
}

/** The chip: "Valid", "Valid with warnings", "Invalid · 1 error", "Not applicable — plain PDF". */
export function validationLook(
  document: DocumentDetail,
): ValidationLook | null {
  const validation = document.validation;
  if (!validation) return null;
  switch (validation.status) {
    case "valid":
      return { label: "Valid", icon: "circle-check", tone: "ok" };
    case "warnings":
      return { label: "Valid with warnings", icon: "triangle", tone: "warn" };
    case "invalid":
      return {
        label: `Invalid · ${plural(validation.fatal_count, "error")}`,
        icon: "octagon",
        tone: "block",
      };
    case "not_applicable": {
      const format = document.format_label;
      const plainPdf =
        format !== undefined && /^(Plain|Scanned) PDF/.test(format);
      return {
        label: plainPdf
          ? `Not applicable — ${format.charAt(0).toLowerCase()}${format.slice(1)}`
          : "Not applicable",
        icon: "minus",
        tone: "neutral",
      };
    }
  }
}

/** "xrechnung-config 2026-01-31; CEN …" → "2026-01-31". */
export function configRelease(engine: string): string | null {
  return /xrechnung-config\s+([^;\s]+)/.exec(engine)?.[1] ?? null;
}

/** The sentence under the title: which rules checked it, and what came out. */
export function validationText(document: DocumentDetail): string {
  const validation = document.validation;
  if (!validation) {
    return document.status === "received" || document.status === "processing"
      ? "Not checked yet. The rules run while the invoice is processed."
      : "This invoice was not checked against the e-invoice rules.";
  }
  if (validation.status === "not_applicable") {
    if (document.kind === "xml" || document.kind === "hybrid_pdf") {
      return "The e-invoice rules don't apply to this format, so it was not checked against them.";
    }
    return document.invoice?.extraction_method === "llm"
      ? "A plain PDF has no structured data to check against the e-invoice rules. AI read the fields below; check them before you mark it reviewed."
      : "A plain PDF has no structured data to check against the e-invoice rules.";
  }
  const rules = rulesLine(document, validation.engine);
  const errors = validation.fatal_count;
  const warnings = validation.warning_count;
  let result: string;
  if (errors > 0) {
    result =
      warnings > 0
        ? `${plural(errors, "error")}, ${plural(warnings, "warning")}.`
        : `${plural(errors, "error")}.`;
  } else if (warnings > 0) {
    result = `No errors, ${plural(warnings, "warning")}.`;
  } else {
    result = "No errors, no warnings.";
  }
  return `${rules} ${result}`;
}

/** XRechnung 1.x/2.x: the specification identifier of the older KoSIT standards. */
const LEGACY_XRECHNUNG =
  /xoev-de:kosit:standard:xrechnung|xrechnung_[12](?:\.|$)/;

/**
 * Which rules ran (HANDOFF section 3, E3 and E5): only XRechnung 3 invoices are checked with
 * the XRechnung rules; XRechnung 1.x/2.x and the other profiles with EN 16931 rules only.
 */
export function rulesLine(
  document: Pick<DocumentDetail, "profile" | "invoice">,
  engine: string,
): string {
  if (document.profile !== "XRECHNUNG")
    return "Checked against EN 16931 rules only.";
  if (LEGACY_XRECHNUNG.test(document.invoice?.spec_id ?? "")) {
    return "XRechnung 2.x: checked against EN 16931 rules only.";
  }
  const release = configRelease(engine);
  return release
    ? `Checked with the official XRechnung rules (KoSIT ${release}).`
    : `Checked with ${engine}.`;
}

export const SEVERITY_ORDER: IssueSeverity[] = [
  "fatal",
  "warning",
  "information",
];

export const GROUP_TITLES: Record<IssueSeverity, string> = {
  fatal: "Errors",
  warning: "Warnings",
  information: "Information",
};

/** Issues grouped by severity, worst first; empty groups are left out. */
export function issueGroups(
  issues: readonly Issue[],
): { severity: IssueSeverity; title: string; issues: Issue[] }[] {
  return SEVERITY_ORDER.map((severity) => ({
    severity,
    title: GROUP_TITLES[severity],
    issues: issues.filter((issue) => issue.severity === severity),
  })).filter((group) => group.issues.length > 0);
}

/** Where the official message comes from (design: "Official message, from the XRechnung rule files"). */
export function officialSource(issue: Issue): string {
  if (issue.source === "xrechnung")
    return "Official message, from the XRechnung rule files";
  if (issue.source === "en16931")
    return "Official message, from the EN 16931 rule files";
  return "Official message, from the XML schema check";
}

/** XRechnung's own rules are written in German. */
export function messageLang(issue: Issue): string | undefined {
  return issue.source === "xrechnung" ? "de" : undefined;
}
