<!-- eslint-disable vue/multi-word-component-names -- named after the design system component -->
<script lang="ts">
const MONTHS_DE = [
  "JAN.",
  "FEB.",
  "MÄRZ",
  "APR.",
  "MAI",
  "JUNI",
  "JULI",
  "AUG.",
  "SEP.",
  "OKT.",
  "NOV.",
  "DEZ.",
];
const MONTHS_EN = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

interface DateParts {
  year: number;
  month: number;
  day: number;
}

function parseDate(date: string): DateParts | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(date);
  if (!match) return null;
  const [, year, month, day] = match;
  return { year: Number(year), month: Number(month), day: Number(day) };
}

/** "2026-10-09" → "09. OKT. 2026" (German, as printed by the stamp). */
export function stampDate(date: string): string {
  const parts = parseDate(date);
  if (!parts) return "";
  const day = String(parts.day).padStart(2, "0");
  return `${day}. ${MONTHS_DE[parts.month - 1] ?? ""} ${parts.year}`;
}

/** "2026-10-09" → "Eingang stamp, 9 October 2026". */
export function stampLabel(date: string): string {
  const parts = parseDate(date);
  if (!parts) return "Eingang stamp";
  return `Eingang stamp, ${parts.day} ${MONTHS_EN[parts.month - 1] ?? ""} ${parts.year}`;
}

/** An RFC 3339 timestamp → "07 Oct, 14:30" in the viewer's time zone (the received chip). */
export function chipDate(timestamp: string): string {
  const value = new Date(timestamp);
  if (Number.isNaN(value.getTime())) return "";
  const day = value.toLocaleString("en-GB", { day: "2-digit" });
  const month = value.toLocaleString("en-GB", { month: "short" });
  const time = value.toLocaleString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  return `${day} ${month}, ${time}`;
}

/** Stamp lettering size W in px. Every stamp measure is a fraction of it. */
const LETTERING = { lg: 44, md: 22 } as const;
</script>

<script setup lang="ts">
import { computed, onMounted } from "vue";

import { ensureInkFilter, INK_FILTER_ID } from "./ink";

const props = withDefaults(
  defineProps<{
    /**
     * lg/md: the EINGANG stamp with a date (YYYY-MM-DD). mark: the square "E" logo.
     * chip: the received date in the app (date is an RFC 3339 timestamp).
     */
    size?: "lg" | "md" | "mark" | "chip";
    date?: string;
    /** Degrees, −5 to +5. */
    rotate?: number;
    /** Side of the mark in px; never below 24. */
    markSize?: 24 | 28 | 40;
  }>(),
  { size: "lg", date: "", rotate: -4, markSize: 24 },
);

const inkFilter = `url(#${INK_FILTER_ID})`;

onMounted(() => {
  if (props.size !== "chip") ensureInkFilter();
});

const stampStyle = computed(() => ({
  fontSize: `${props.size === "md" ? LETTERING.md : LETTERING.lg}px`,
  transform: `rotate(${props.rotate}deg)`,
  filter: inkFilter,
}));
const markStyle = computed(() => ({
  fontSize: `${props.markSize}px`,
  filter: inkFilter,
}));
</script>

<template>
  <span v-if="size === 'chip'" class="received-chip">{{ chipDate(date) }}</span>
  <span
    v-else-if="size === 'mark'"
    class="mark"
    aria-hidden="true"
    :style="markStyle"
    ><span class="mark-letter">E</span></span
  >
  <span
    v-else
    role="img"
    class="stamp"
    :aria-label="stampLabel(date)"
    :style="stampStyle"
  >
    <span class="stamp-word">Eingang</span>
    <span class="stamp-date">{{ stampDate(date) }}</span>
  </span>
</template>

<style scoped>
/* Proportions are fixed fractions of the lettering size (em); do not change them. */
.stamp {
  display: inline-grid;
  justify-items: center;
  gap: 0.09em;
  padding: 0.27em 0.36em;
  border: 0.07em solid var(--stamp);
  border-radius: 0.14em;
  outline: 0.035em solid var(--stamp);
  outline-offset: -0.18em;
  color: var(--stamp);
  font-family: var(--font-stamp);
  font-weight: 700;
  line-height: 1;
  letter-spacing: var(--tracking-stamp);
  text-transform: uppercase;
}

.stamp-word {
  padding: 0.09em 0.1em 0 0.18em;
}

.stamp-date {
  padding: 0.2em 0.2em 0.2em 0.28em;
  border-top: 0.1em solid var(--stamp);
  font-size: 0.45em;
}

.mark {
  display: inline-grid;
  flex: none;
  place-items: center;
  width: 1em;
  height: 1em;
  border: 0.0625em solid var(--stamp);
  border-radius: 0.15em;
  outline: 0.025em solid var(--stamp);
  outline-offset: -0.175em;
  background: var(--win);
  color: var(--stamp);
  font-family: var(--font-stamp);
  font-weight: 700;
  line-height: 1;
}

.mark-letter {
  font-size: 0.55em;
}

.received-chip {
  display: inline-flex;
  align-items: center;
  height: var(--size-chip-sm);
  padding: 0 var(--space-8);
  border-radius: var(--r-sm);
  background: var(--stamp-soft);
  color: var(--stamp);
  font-size: var(--fs-12);
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
</style>
