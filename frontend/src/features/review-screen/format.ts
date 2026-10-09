// How the review screen writes amounts, dates and times (design: "1.190,00 €", "23 Oct 2026",
// "07 Oct 2026, 14:30"; credit notes with a minus sign, U+2212).

/** UNTDID 1001 type code of a credit note. */
export const CREDIT_NOTE_TYPE_CODE = 381;

const MONEY = new Intl.NumberFormat("de-DE", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const DAY = new Intl.DateTimeFormat("en-GB", {
  day: "2-digit",
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});

const DAY_TIME = new Intl.DateTimeFormat("en-GB", {
  day: "2-digit",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

const MINUS = "−";

export function isCreditNote(typeCode: number | undefined): boolean {
  return typeCode === CREDIT_NOTE_TYPE_CODE;
}

/**
 * "1190.00" → "1.190,00 €". With `credit` the amount gets a minus sign ("−58,31 €"); an amount
 * that is already negative keeps its single minus. Unknown values read "—".
 */
export function formatMoney(
  value: string | number | null | undefined,
  currency = "EUR",
  credit = false,
): string {
  if (value === null || value === undefined || value === "") return "—";
  const amount = Number(value);
  if (Number.isNaN(amount)) return String(value);
  const negative = amount < 0 || (credit && amount !== 0);
  const digits = MONEY.format(Math.abs(amount));
  const unit = currency === "EUR" ? "€" : currency;
  return `${negative ? MINUS : ""}${digits} ${unit}`;
}

/** "2026-10-23" → "23 Oct 2026". */
export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return value;
  return DAY.format(new Date(`${value}T00:00:00Z`));
}

/** An RFC 3339 timestamp → "07 Oct 2026, 14:30" in the viewer's time zone. */
export function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return DAY_TIME.format(date);
}

/** A tax rate "19.00" → "19", "7.5" → "7,5". */
export function formatRate(value: unknown): string {
  const rate = Number(value);
  if (value === null || value === undefined || Number.isNaN(rate)) return "—";
  return String(rate).replace(".", ",");
}

/** "1 error", "2 errors". */
export function plural(count: number, one: string, many = `${one}s`): string {
  return `${count} ${count === 1 ? one : many}`;
}
