<script setup lang="ts">
// The inbox list: a real table from 768 px, cards on phones (design "Inbox", responsive rules).
// Sorting is the API's; this component only shows which column is sorted and reports clicks.
import { computed } from "vue";
import type { RouteLocationRaw } from "vue-router";

import Badge from "../../components/ui/Badge.vue";
import DataTable, {
  type DataTableColumn,
  type DataTableSort,
} from "../../components/ui/DataTable.vue";
import FormatChip from "../../components/ui/FormatChip.vue";
import Icon from "../../components/ui/Icon.vue";
import Stamp from "../../components/ui/Stamp.vue";
import StatusChip from "../../components/ui/StatusChip.vue";
import InboxChip from "./InboxChip.vue";
import {
  einvoiceLook,
  formatDue,
  formatGross,
  highlight,
  isOverdue,
  stepText,
  today,
  validationLook,
  type DocumentSummary,
} from "./rows";

const props = defineProps<{
  rows: DocumentSummary[];
  /** The search text, highlighted in supplier and number. */
  query: string;
  /** Cards instead of the table (≤ 767 px). */
  phone: boolean;
  /** Where a card links to (the review screen). */
  linkFor: (row: DocumentSummary) => RouteLocationRaw;
}>();

const sort = defineModel<DataTableSort | null>("sort", { default: null });

const emit = defineEmits<{ open: [row: DocumentSummary] }>();

defineSlots<{ empty?: () => unknown }>();

const columns: DataTableColumn<DocumentSummary>[] = [
  { key: "received", label: "Received", sortable: true, width: "112px" },
  { key: "supplier", label: "Supplier" },
  { key: "number", label: "Number", mono: true, width: "124px" },
  {
    key: "gross",
    label: "Gross",
    sortable: true,
    align: "right",
    mono: true,
    width: "112px",
  },
  { key: "due", label: "Due", sortable: true, width: "112px" },
  { key: "format", label: "Format", width: "164px" },
  { key: "einvoice", label: "E-invoice", width: "144px" },
  { key: "validation", label: "Validation", width: "152px" },
  { key: "checks", label: "Checks", width: "72px" },
  { key: "status", label: "Status", width: "176px" },
];

const todayIso = computed(() => today());

function supplierOf(row: DocumentSummary): string {
  return row.supplier_name ?? row.original_filename;
}

function blockText(row: DocumentSummary): string {
  const n = row.open_block_checks;
  return `${n} blocking ${n === 1 ? "check" : "checks"}`;
}

function warnText(row: DocumentSummary): string {
  const n = row.open_warn_checks;
  return `${n} ${n === 1 ? "warning" : "warnings"}`;
}

function checksLabel(row: DocumentSummary): string {
  const parts: string[] = [];
  if (row.open_block_checks > 0) parts.push(blockText(row));
  if (row.open_warn_checks > 0) parts.push(warnText(row));
  return parts.length ? parts.join(", ") : "No open checks";
}

const rowKey = (row: DocumentSummary): string => row.id;
</script>

<template>
  <ul v-if="props.phone" class="cards" aria-label="Invoices">
    <li v-for="row in rows" :key="row.id">
      <RouterLink class="card" :to="linkFor(row)">
        <span class="card-line">
          <span class="card-supplier"
            ><template
              v-for="(part, index) in highlight(supplierOf(row), query)"
              :key="index"
              ><mark v-if="part.match">{{ part.text }}</mark
              ><template v-else>{{ part.text }}</template></template
            ></span
          >
          <span class="card-gross">{{ formatGross(row) }}</span>
        </span>
        <span class="card-line">
          <span class="card-number"
            ><template
              v-for="(part, index) in highlight(
                row.invoice_number ?? '—',
                query,
              )"
              :key="index"
              ><mark v-if="part.match">{{ part.text }}</mark
              ><template v-else>{{ part.text }}</template></template
            ></span
          >
          <Stamp size="chip" :date="row.received_at" />
        </span>
        <span class="card-chips">
          <StatusChip :status="row.status" />
          <InboxChip v-if="validationLook(row)" :look="validationLook(row)!" />
          <InboxChip v-if="einvoiceLook(row)" :look="einvoiceLook(row)!" />
          <FormatChip v-if="row.format_label" :label="row.format_label" />
        </span>
        <span v-if="stepText(row)" class="step">{{ stepText(row) }}</span>
        <span class="card-line">
          <span class="checks">
            <span v-if="row.open_block_checks > 0" class="checks-block"
              ><Icon name="octagon" :size="16" />{{ blockText(row) }}</span
            ><span v-if="row.open_warn_checks > 0" class="checks-warn"
              ><Icon name="triangle" :size="16" />{{ warnText(row) }}</span
            ><span
              v-if="row.open_block_checks === 0 && row.open_warn_checks === 0"
              class="none"
              >No open checks</span
            >
          </span>
          <span
            v-if="row.due_date"
            :class="{ 'is-overdue': isOverdue(row, todayIso) }"
            >Due {{ formatDue(row.due_date)
            }}{{ isOverdue(row, todayIso) ? ", overdue" : "" }}</span
          >
        </span>
      </RouterLink>
    </li>
    <li v-if="rows.length === 0" class="cards-empty"><slot name="empty" /></li>
  </ul>

  <DataTable
    v-else
    v-model:sort="sort"
    caption="Invoices"
    :columns="columns"
    :rows="rows"
    :row-key="rowKey"
    @row-click="emit('open', $event)"
  >
    <template #cell-received="{ row }">
      <Stamp size="chip" :date="row.received_at" />
    </template>
    <template #cell-supplier="{ row }">
      <span class="supplier"
        ><template
          v-for="(part, index) in highlight(supplierOf(row), query)"
          :key="index"
          ><mark v-if="part.match">{{ part.text }}</mark
          ><template v-else>{{ part.text }}</template></template
        ></span
      >
    </template>
    <template #cell-number="{ row }">
      <template
        v-for="(part, index) in highlight(row.invoice_number ?? '—', query)"
        :key="index"
        ><mark v-if="part.match">{{ part.text }}</mark
        ><template v-else>{{ part.text }}</template></template
      >
    </template>
    <template #cell-gross="{ row }">{{ formatGross(row) }}</template>
    <template #cell-due="{ row }">
      <span v-if="isOverdue(row, todayIso)" class="due is-overdue"
        ><span>{{ formatDue(row.due_date) }}</span
        ><Badge variant="overdue">overdue</Badge></span
      >
      <span v-else>{{ formatDue(row.due_date) }}</span>
    </template>
    <template #cell-format="{ row }">
      <FormatChip v-if="row.format_label" :label="row.format_label" />
      <span v-else class="none">—</span>
    </template>
    <template #cell-einvoice="{ row }">
      <InboxChip v-if="einvoiceLook(row)" :look="einvoiceLook(row)!" />
      <span v-else class="none">—</span>
    </template>
    <template #cell-validation="{ row }">
      <InboxChip v-if="validationLook(row)" :look="validationLook(row)!" />
      <span v-else class="none">—</span>
    </template>
    <template #cell-checks="{ row }">
      <span class="checks" :aria-label="checksLabel(row)" role="img">
        <span v-if="row.open_block_checks > 0" class="checks-block"
          ><Icon name="octagon" :size="16" />{{ row.open_block_checks }}</span
        ><span v-if="row.open_warn_checks > 0" class="checks-warn"
          ><Icon name="triangle" :size="16" />{{ row.open_warn_checks }}</span
        ><span
          v-if="row.open_block_checks === 0 && row.open_warn_checks === 0"
          class="none"
          >—</span
        >
      </span>
    </template>
    <template #cell-status="{ row }">
      <span class="status">
        <StatusChip :status="row.status" />
        <span v-if="stepText(row)" class="step">{{ stepText(row) }}</span>
      </span>
    </template>
    <template #empty><slot name="empty" /></template>
  </DataTable>
</template>

<style scoped>
mark {
  background: var(--hl);
  color: var(--ink);
}

.supplier {
  color: var(--ink);
  font-weight: 500;
}

.none {
  color: var(--muted);
}

.due.is-overdue {
  display: inline-grid;
  justify-items: start;
  gap: var(--space-4);
}

.is-overdue {
  color: var(--block);
  font-weight: 500;
}

.checks {
  display: inline-flex;
  align-items: center;
  gap: var(--space-8);
  font-weight: 500;
}

.checks-block,
.checks-warn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-4);
}

.checks-block {
  color: var(--block);
}

.checks-warn {
  color: var(--warn-text);
}

.checks-warn :deep(.icon) {
  color: var(--warn);
}

.status {
  display: inline-grid;
  justify-items: start;
  gap: var(--space-4);
}

.step {
  color: var(--info);
  font-size: var(--fs-12);
  font-weight: 500;
}

.cards {
  display: grid;
  gap: var(--space-8);
  margin: 0;
  padding: 0;
  list-style: none;
}

.card {
  display: grid;
  gap: var(--space-8);
  padding: var(--space-12) var(--space-16);
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  background: var(--win);
  color: var(--text);
  text-decoration: none;
}

.card:hover {
  background: var(--soft);
  color: var(--text);
}

.card-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-12);
}

.card-supplier {
  color: var(--ink);
  font-weight: 600;
}

.card-gross {
  flex: none;
  color: var(--ink);
  font-family: var(--font-mono);
  font-weight: 500;
}

.card-number {
  color: var(--muted);
  font-family: var(--font-mono);
  font-size: var(--fs-12);
}

.card-chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-8);
}

.cards-empty {
  list-style: none;
}
</style>
