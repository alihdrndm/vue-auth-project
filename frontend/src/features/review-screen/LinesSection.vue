<script setup lang="ts">
// LinesTable (design): description, quantity, unit price and net amount of every line.
import { computed, useId } from "vue";

import type { components } from "../../api/schema";
import { formatMoney } from "./format";

type Line = components["schemas"]["Line"];

const props = withDefaults(
  defineProps<{
    lines: Line[];
    currency?: string;
    credit?: boolean;
  }>(),
  { currency: "EUR", credit: false },
);

const id = useId();
const rows = computed(() =>
  [...props.lines].sort((a, b) => a.position - b.position),
);

function quantity(line: Line): string {
  if (line.quantity === undefined) return "—";
  const value = String(Number(line.quantity)).replace(".", ",");
  return line.unit_code ? `${value} ${line.unit_code}` : value;
}
</script>

<template>
  <section class="section" :aria-labelledby="`${id}-title`">
    <h2 :id="`${id}-title`" class="section-title">Lines</h2>
    <p v-if="rows.length === 0" class="section-empty">
      No line items were read for this invoice.
    </p>
    <div v-else class="lines-wrap">
      <table class="lines">
        <caption class="sr-only">
          Invoice lines
        </caption>
        <thead>
          <tr>
            <th scope="col">Description</th>
            <th scope="col" class="num">Qty</th>
            <th scope="col" class="num">Unit price</th>
            <th scope="col" class="num">Net</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="line in rows" :key="line.position">
            <td class="desc">{{ line.description || "—" }}</td>
            <td class="num mono">{{ quantity(line) }}</td>
            <td class="num mono">
              {{ formatMoney(line.unit_price, currency, credit) }}
            </td>
            <td class="num mono strong">
              {{ formatMoney(line.net_amount, currency, credit) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped src="./section.css"></style>

<style scoped>
.lines-wrap {
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  overflow-x: auto;
}

.lines {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: var(--fs-13);
}

th {
  height: var(--size-md);
  padding: 0 var(--space-8);
  border-bottom: 1px solid var(--line);
  background: var(--bar);
  color: var(--muted);
  font-size: var(--fs-12);
  font-weight: 500;
  text-align: left;
  white-space: nowrap;
}

td {
  padding: var(--space-12) var(--space-8);
  border-bottom: 1px solid var(--line);
  vertical-align: top;
}

tr:last-child td {
  border-bottom: 0;
}

th:first-child,
td:first-child {
  padding-left: var(--space-12);
}

th:last-child,
td:last-child {
  padding-right: var(--space-12);
}

.num {
  text-align: right;
  white-space: nowrap;
}

.mono {
  font-family: var(--font-mono);
}

.desc,
.strong {
  color: var(--ink);
}
</style>
