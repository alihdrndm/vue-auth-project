// The Settings screen's organisation form (HANDOFF `PATCH /organization`: admins only; in a
// sandbox only the name), and how the AI budget reads (design "MeterBar": "$0.42 of $2.00").
import type { components } from "../../api/schema";

export type Organization = components["schemas"]["Organization"];
export type OrganizationPatch =
  components["schemas"]["PatchedOrganizationUpdate"];
export type Role = components["schemas"]["RoleEnum"];

export const SANDBOX_REASON = "Not available in the sandbox.";
export const ADMIN_REASON = "Only admins can change settings.";

export const LIMITS = {
  duplicate_window_days: { min: 1, max: 365 },
  reminder_after_days: { min: 1, max: 60 },
} as const;

/** What the form edits; numbers are kept as typed text. */
export interface OrgDraft {
  name: string;
  vat_id: string;
  four_eyes: boolean;
  duplicate_window_days: string;
  reminder_after_days: string;
}

export type DraftErrors = Partial<Record<keyof OrgDraft, string>>;

export function draftFrom(org: Organization): OrgDraft {
  // Coerced, so an unexpected body can't break the form.
  return {
    name: String(org.name ?? ""),
    vat_id: String(org.vat_id ?? ""),
    four_eyes: org.four_eyes === true,
    duplicate_window_days: String(org.duplicate_window_days ?? ""),
    reminder_after_days: String(org.reminder_after_days ?? ""),
  };
}

/** Why a field can't be changed by this viewer, or null when it can. */
export function lockReason(
  field: keyof OrgDraft,
  role: Role | null,
  sandbox: boolean,
): string | null {
  if (role !== "admin") return ADMIN_REASON;
  if (sandbox && field !== "name") return SANDBOX_REASON;
  return null;
}

function days(raw: string, field: keyof typeof LIMITS): string | undefined {
  const { min, max } = LIMITS[field];
  const text = raw.trim();
  const value = Number(text);
  if (!/^\d+$/.test(text) || value < min || value > max)
    return `Enter a whole number from ${min} to ${max}.`;
  return undefined;
}

export function validateDraft(draft: OrgDraft): DraftErrors {
  const errors: DraftErrors = {};
  const name = draft.name.trim();
  if (name === "") errors.name = "Enter the organisation’s name.";
  else if (name.length > 200) errors.name = "Use at most 200 characters.";
  if (draft.vat_id.trim().length > 32)
    errors.vat_id = "Use at most 32 characters.";
  errors.duplicate_window_days = days(
    draft.duplicate_window_days,
    "duplicate_window_days",
  );
  errors.reminder_after_days = days(
    draft.reminder_after_days,
    "reminder_after_days",
  );
  return Object.fromEntries(
    Object.entries(errors).filter(([, message]) => message !== undefined),
  ) as DraftErrors;
}

/** The PATCH body: only what changed. An empty VAT ID clears it (`null`). */
export function patchFrom(
  org: Organization,
  draft: OrgDraft,
): OrganizationPatch {
  const body: OrganizationPatch = {};
  const name = draft.name.trim();
  if (name !== org.name) body.name = name;
  const vat = draft.vat_id.trim();
  if (vat !== (org.vat_id ?? "")) body.vat_id = vat === "" ? null : vat;
  if (draft.four_eyes !== org.four_eyes) body.four_eyes = draft.four_eyes;
  const dup = Number(draft.duplicate_window_days.trim());
  if (dup !== org.duplicate_window_days) body.duplicate_window_days = dup;
  const rem = Number(draft.reminder_after_days.trim());
  if (rem !== org.reminder_after_days) body.reminder_after_days = rem;
  return body;
}

/** "0.42" → "$0.42". */
export function formatUsd(value: string | number): string {
  const amount = Number(value);
  return Number.isFinite(amount) ? `$${amount.toFixed(2)}` : `$${value}`;
}

export type MeterLevel = "under" | "near" | "reached";

/** Spent as a share of the budget, 0–100 (whole percent). */
export function meterPercent(spent: string, budget: string): number {
  const used = Number(spent);
  const total = Number(budget);
  if (!Number.isFinite(used) || !Number.isFinite(total) || total <= 0)
    return used > 0 ? 100 : 0;
  return Math.min(100, Math.max(0, Math.round((used / total) * 100)));
}

/** Near the limit from 80 %; reached at 100 %. */
export function meterLevel(percent: number): MeterLevel {
  if (percent >= 100) return "reached";
  if (percent >= 80) return "near";
  return "under";
}
