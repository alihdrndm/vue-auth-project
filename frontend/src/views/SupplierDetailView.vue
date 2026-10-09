<script setup lang="ts">
// Supplier detail (design "Eingang App Screens" ?screen=supplier / supplier-confirmed): the IBAN
// history (an untrusted account is highlighted "Not confirmed yet" with a link to the invoice
// whose check asks about it; a confirmed one names who, when and the note) and the invoices.
import { useQuery } from "@tanstack/vue-query";
import { computed } from "vue";
import { useRouter } from "vue-router";

import { api, ApiError, unwrap } from "../api/client";
import { queryKeys } from "../api/query";
import DataTable, {
  type DataTableColumn,
} from "../components/ui/DataTable.vue";
import EmptyState from "../components/ui/EmptyState.vue";
import ErrorState from "../components/ui/ErrorState.vue";
import Icon from "../components/ui/Icon.vue";
import Skeleton, { type SkeletonColumn } from "../components/ui/Skeleton.vue";
import Stamp from "../components/ui/Stamp.vue";
import StatusChip from "../components/ui/StatusChip.vue";
import {
  firstSeenInvoice,
  formatDay,
  groupIban,
  type SupplierIban,
  type SupplierInvoice,
} from "../features/suppliers/iban";
import IbanTag from "../features/suppliers/IbanTag.vue";
import {
  formatDate,
  formatMoney,
  plural,
} from "../features/review-screen/format";

const props = defineProps<{ id: string }>();

const router = useRouter();

const supplier = useQuery({
  queryKey: computed(() => queryKeys.suppliers.detail(props.id)),
  queryFn: async () =>
    unwrap(
      await api.GET("/api/v1/suppliers/{supplier_id}", {
        params: { path: { supplier_id: props.id } },
      }),
    ),
});

const data = computed(() => supplier.data.value);
const notFound = computed(
  () =>
    supplier.error.value instanceof ApiError &&
    supplier.error.value.status === 404,
);
const error = computed(() => {
  if (!supplier.isError.value || data.value || notFound.value) return null;
  const value = supplier.error.value;
  if (value instanceof ApiError)
    return { title: value.title, detail: value.detail };
  return {
    title: "Couldn’t load the supplier",
    detail: value instanceof Error ? value.message : undefined,
  };
});

/** Unconfirmed accounts first, then newest first, as in the design. */
const ibans = computed<SupplierIban[]>(() =>
  [...(data.value?.ibans ?? [])].sort((a, b) => {
    if (a.trusted !== b.trusted) return a.trusted ? 1 : -1;
    return Date.parse(b.first_seen_at) - Date.parse(a.first_seen_at);
  }),
);

function seenOn(entry: SupplierIban): SupplierInvoice | null {
  return firstSeenInvoice(entry, data.value?.invoices ?? []);
}

function numberOf(invoice: SupplierInvoice | null): string | null {
  return invoice?.invoice_number ?? null;
}

const subtitle = computed(() => {
  const value = data.value;
  if (!value) return "";
  return `${plural(value.invoice_count, "invoice")} since ${formatDay(value.first_seen_at)}`;
});

const COLUMNS: DataTableColumn<SupplierInvoice>[] = [
  { key: "received", label: "Received", width: "136px" },
  {
    key: "number",
    label: "Number",
    mono: true,
    value: (row) => row.invoice_number ?? "—",
  },
  {
    key: "issued",
    label: "Invoice date",
    width: "128px",
    value: (row) => formatDate(row.issue_date),
  },
  {
    key: "gross",
    label: "Gross",
    align: "right",
    mono: true,
    width: "136px",
    value: (row) => formatMoney(row.gross_total, row.currency),
  },
  { key: "status", label: "Status", width: "184px" },
];

const SKELETON_COLUMNS: SkeletonColumn[] = [
  { track: "136px", shape: "chip" },
  { track: "minmax(0, 1fr)" },
  { track: "128px" },
  { track: "136px" },
  { track: "184px", shape: "chip" },
];

function open(row: SupplierInvoice): void {
  void router.push({ name: "invoice", params: { id: row.document_id } });
}
</script>

<template>
  <section class="page" aria-labelledby="supplier-title">
    <div class="title-block">
      <RouterLink class="back" :to="{ name: 'suppliers' }"
        ><Icon name="chevron-left" :size="16" />Suppliers</RouterLink
      >
      <h1 id="supplier-title" class="page-title">
        {{ data?.name ?? "Supplier" }}
      </h1>
      <span v-if="data" class="muted"
        >{{ subtitle
        }}<template v-if="data.vat_id">
          · VAT ID <span class="mono">{{ data.vat_id }}</span></template
        ></span
      >
    </div>

    <Skeleton
      v-if="supplier.isPending.value"
      label="Loading the supplier"
      header
      :columns="SKELETON_COLUMNS"
      :rows="4"
    />
    <div v-else-if="notFound" class="pane">
      <EmptyState
        icon="search"
        title="No such supplier"
        body="The link may be old, or the supplier’s invoices were deleted."
      >
        <template #action>
          <RouterLink class="check-link" :to="{ name: 'suppliers' }"
            >Go to the suppliers</RouterLink
          >
        </template>
      </EmptyState>
    </div>
    <div v-else-if="error" class="pane">
      <ErrorState
        :title="error.title"
        :detail="error.detail"
        :retrying="supplier.isFetching.value"
        @retry="supplier.refetch()"
      />
    </div>

    <template v-else-if="data">
      <section class="pane" aria-labelledby="iban-title">
        <div class="pane-head">
          <h2 id="iban-title" class="pane-title">IBAN history</h2>
        </div>
        <p v-if="ibans.length === 0" class="empty-line">
          No bank account on this supplier’s invoices yet.
        </p>
        <ul v-else class="ibans">
          <li
            v-for="entry in ibans"
            :key="entry.iban"
            class="iban"
            :class="{
              'iban--new': !entry.trusted,
              'iban--confirmed': entry.trusted && entry.status === 'confirmed',
            }"
          >
            <div class="iban-line">
              <span class="iban-number mono">{{ groupIban(entry.iban) }}</span>
              <IbanTag
                :status="entry.status"
                :outlined="entry.status !== 'known'"
              />
            </div>

            <template v-if="!entry.trusted">
              <p class="iban-text">
                First seen
                <template v-if="numberOf(seenOn(entry))"
                  >on
                  <span class="mono">{{
                    numberOf(seenOn(entry))
                  }}</span></template
                >, {{ formatDay(entry.first_seen_at) }} · Not confirmed yet
              </p>
              <RouterLink
                v-if="seenOn(entry)"
                class="check-link"
                :to="{
                  name: 'invoice',
                  params: { id: seenOn(entry)?.document_id },
                }"
                ><Icon name="octagon" :size="14" class="check-icon" />Open the
                check on
                {{ numberOf(seenOn(entry)) ?? "this invoice" }}</RouterLink
              >
            </template>
            <p v-else-if="entry.status === 'confirmed'" class="iban-text">
              Confirmed by {{ entry.confirmed_by_name ?? "someone" }},
              {{ formatDay(entry.confirmed_at)
              }}<template v-if="entry.confirmation_note">
                · ‘{{ entry.confirmation_note }}’</template
              >
            </p>
            <p v-else class="iban-text">
              Known account · first seen {{ formatDay(entry.first_seen_at) }}
              <template v-if="numberOf(seenOn(entry))"
                >on
                <span class="mono">{{
                  numberOf(seenOn(entry))
                }}</span></template
              >.
            </p>
          </li>
        </ul>
      </section>

      <section class="pane" aria-labelledby="invoices-title">
        <div class="pane-head">
          <h2 id="invoices-title" class="pane-title">Invoices</h2>
        </div>
        <EmptyState
          v-if="data.invoices.length === 0"
          :level="3"
          title="No invoices"
          body="This supplier’s invoices were deleted."
        />
        <DataTable
          v-else
          :caption="`Invoices from ${data.name}`"
          :columns="COLUMNS"
          :rows="data.invoices"
          :row-key="(row) => row.document_id"
          @row-click="open"
        >
          <template #cell-received="{ row }">
            <Stamp size="chip" :date="row.received_at" />
          </template>
          <template #cell-status="{ row }">
            <StatusChip :status="row.status" />
          </template>
        </DataTable>
      </section>
    </template>
  </section>
</template>

<style scoped src="../features/approvals/pane.css"></style>
<style scoped>
.title-block {
  display: grid;
  gap: var(--space-4);
}

.back {
  justify-self: start;
  display: inline-flex;
  align-items: center;
  gap: var(--space-4);
  color: var(--text);
  font-size: var(--fs-13);
  font-weight: 500;
  text-decoration: none;
}

.back:hover {
  color: var(--ink);
  text-decoration: underline;
}

.ibans {
  margin: 0;
  padding: 0;
  list-style: none;
}

.iban {
  display: grid;
  gap: var(--space-8);
  padding: var(--space-16) var(--space-20);
  border-bottom: 1px solid var(--line);
}

.iban:last-child {
  border-bottom: 0;
}

.iban--new {
  background: var(--block-soft);
}

.iban--confirmed {
  background: var(--ok-soft);
}

.iban-line {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-8) var(--space-12);
}

.iban-number {
  color: var(--ink);
  font-size: var(--fs-14);
  font-weight: 500;
  overflow-wrap: anywhere;
}

.iban-text {
  margin: 0;
  color: var(--ink);
  font-size: var(--fs-13);
  overflow-wrap: anywhere;
}

.check-link {
  justify-self: start;
  display: inline-flex;
  align-items: center;
  gap: var(--space-4);
  color: var(--ink);
  font-size: var(--fs-13);
  font-weight: 500;
}

.check-icon {
  color: var(--block);
}

@media (max-width: 767px) {
  .iban {
    padding: var(--space-16);
  }
}
</style>
