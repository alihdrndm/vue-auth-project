// The check list of the review screen (HANDOFF "Business checks", design "CheckCard"):
// open checks first, worst first; resolving needs a note of 5–500 characters; whether a
// check can be resolved, and why not, comes from the API, never from the browser.
import type { components } from "../../api/schema";

export type Check = components["schemas"]["Check"];
export type Severity = Check["severity"];

export const NOTE_MIN = 5;
export const NOTE_MAX = 500;

const SEVERITY_ORDER: Record<Severity, number> = { block: 0, warn: 1, info: 2 };

export const SEVERITY_TEXT: Record<Severity, string> = {
  block: "Block",
  warn: "Warning",
  info: "Info",
};

export function isOpen(check: Check): boolean {
  return !check.resolved_at;
}

/** Open before resolved; within each, block before warn before info, then by check ID. */
export function sortChecks(checks: readonly Check[]): Check[] {
  return [...checks].sort(
    (a, b) =>
      Number(!isOpen(a)) - Number(!isOpen(b)) ||
      SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity] ||
      a.check_id.localeCompare(b.check_id),
  );
}

export function openBlocking(checks: readonly Check[]): number {
  return checks.filter((check) => isOpen(check) && check.severity === "block")
    .length;
}

/** The inline error for a resolution note, or null when it can be sent. */
export function noteError(note: string): string | null {
  const length = note.trim().length;
  if (length < NOTE_MIN || length > NOTE_MAX) {
    return `Write ${NOTE_MIN} to ${NOTE_MAX} characters.`;
  }
  return null;
}

/** "12 / 500": the counter under the note field (announced politely). */
export function noteCounter(note: string): string {
  return `${note.trim().length} / ${NOTE_MAX}`;
}

export interface ResolveState {
  canResolve: boolean;
  /** Why the resolve button is disabled, shown as visible text (design rule 9). */
  reason: string | null;
  /** Information-only checks have no resolve button at all. */
  showButton: boolean;
}

export function resolveState(check: Check): ResolveState {
  if (!isOpen(check) || check.severity === "info") {
    return { canResolve: false, reason: null, showButton: false };
  }
  if (check.resolve.enabled)
    return { canResolve: true, reason: null, showButton: true };
  return {
    canResolve: false,
    reason: check.resolve.reason ?? null,
    showButton: true,
  };
}

/** C15 is the failed validation: resolving it means "accept anyway" (design). */
export function resolveLabel(check: Check): string {
  return check.check_id === "C15" ? "Accept anyway…" : "Resolve…";
}
