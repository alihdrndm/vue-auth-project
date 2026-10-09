// How bank accounts read in Approvals and Suppliers (design "IBAN tag"; design decision 7:
// "Known account" = known, "Confirmed change" = confirmed, "New account" = new).
import type { components } from "../../api/schema";
import type { IconName } from "../../components/ui/icons";

export type IbanStatus = components["schemas"]["IbanStatusEnum"];
export type SupplierIban = components["schemas"]["SupplierIban"];
export type SupplierInvoice = components["schemas"]["SupplierInvoice"];

export interface IbanTagLook {
  label: string;
  icon: IconName;
  tone: "neutral" | "ok" | "block";
}

export const IBAN_TAG: Record<IbanStatus, IbanTagLook> = {
  known: { label: "Known account", icon: "check", tone: "neutral" },
  confirmed: { label: "Confirmed change", icon: "circle-check", tone: "ok" },
  new: { label: "New account", icon: "circle-alert", tone: "block" },
};

/** "•••• 4417", or "—" when the invoice has no IBAN. */
export function maskedIban(last4: string | undefined): string {
  return last4 ? `•••• ${last4}` : "—";
}

/** "DE02120300000000202051" → "DE02 1203 0000 0000 2020 51". */
export function groupIban(iban: string): string {
  return iban
    .replace(/\s+/g, "")
    .replace(/(.{4})/g, "$1 ")
    .trim();
}

/**
 * The supplier invoice an IBAN was first seen on. The API names the invoice by its own id,
 * not the document id the review route needs; the first sighting is recorded with that
 * document's received time, so the invoice is matched by it.
 */
export function firstSeenInvoice(
  entry: SupplierIban,
  invoices: readonly SupplierInvoice[],
): SupplierInvoice | null {
  const seen = Date.parse(entry.first_seen_at);
  if (Number.isNaN(seen)) return null;
  return (
    invoices.find((invoice) => Date.parse(invoice.received_at) === seen) ?? null
  );
}

const DAY = new Intl.DateTimeFormat("en-GB", {
  day: "2-digit",
  month: "short",
  year: "numeric",
});

/** An RFC 3339 timestamp → "09 Oct 2026" in the viewer's time zone; "—" when unknown. */
export function formatDay(value: string | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : DAY.format(date);
}
