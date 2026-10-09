<script setup lang="ts">
// TaxBreakdown (design "VAT breakdown"): net, VAT per rate on its base, gross.
import { computed, useId } from "vue";

import type { components } from "../../api/schema";
import { formatMoney, formatRate } from "./format";

type InvoiceDetail = components["schemas"]["InvoiceDetail"];

const props = withDefaults(
  defineProps<{
    invoice?: InvoiceDetail;
    credit?: boolean;
  }>(),
  { invoice: undefined, credit: false },
);

const id = useId();
const currency = computed(() => props.invoice?.currency ?? "EUR");

interface Row {
  label: string;
  amount: string;
}

const rows = computed<Row[]>(() => {
  const invoice = props.invoice;
  if (!invoice) return [];
  const money = (value: unknown): string =>
    formatMoney(
      typeof value === "string" || typeof value === "number" ? value : null,
      currency.value,
      props.credit,
    );
  const breakdown = invoice.tax_breakdown ?? [];
  const vat: Row[] =
    breakdown.length > 0
      ? breakdown.map((entry) => ({
          label: `VAT ${formatRate(entry.rate)} % on ${money(entry.taxable_amount)}`,
          amount: money(entry.tax_amount),
        }))
      : [{ label: "VAT", amount: money(invoice.tax_total) }];
  return [{ label: "Net", amount: money(invoice.net_total) }, ...vat];
});

const gross = computed(() =>
  formatMoney(props.invoice?.gross_total, currency.value, props.credit),
);
</script>

<template>
  <section class="section" :aria-labelledby="`${id}-title`">
    <h2 :id="`${id}-title`" class="section-title">VAT breakdown</h2>
    <p v-if="!invoice" class="section-empty">No amounts were read yet.</p>
    <dl v-else class="vat">
      <template v-for="row in rows" :key="row.label">
        <dt>{{ row.label }}</dt>
        <dd>{{ row.amount }}</dd>
      </template>
      <dt class="total">Gross</dt>
      <dd class="total">{{ gross }}</dd>
    </dl>
  </section>
</template>

<style scoped src="./section.css"></style>

<style scoped>
.vat {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--space-8) var(--space-16);
  font-size: var(--fs-13);
}

dt {
  color: var(--muted);
}

dd {
  font-family: var(--font-mono);
  color: var(--ink);
  text-align: right;
  white-space: nowrap;
}

.total {
  padding-top: var(--space-8);
  border-top: 1px solid var(--line);
  font-size: var(--fs-14);
  color: var(--ink);
}

dt.total {
  font-weight: 600;
}

dd.total {
  font-weight: 500;
}
</style>
