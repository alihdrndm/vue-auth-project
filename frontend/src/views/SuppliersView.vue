<script setup lang="ts">
// Suppliers (design "Eingang App Screens" ?screen=suppliers, HANDOFF `/app/suppliers`): every
// supplier with its invoice count, searchable by name (`?q=`); rows open the supplier.
import { keepPreviousData, useQuery } from "@tanstack/vue-query";
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { api, ApiError, unwrap } from "../api/client";
import { queryKeys, type SupplierListParams } from "../api/query";
import type { components } from "../api/schema";
import Button from "../components/ui/Button.vue";
import DataTable, {
  type DataTableColumn,
} from "../components/ui/DataTable.vue";
import EmptyState from "../components/ui/EmptyState.vue";
import ErrorState from "../components/ui/ErrorState.vue";
import Icon from "../components/ui/Icon.vue";
import Skeleton, { type SkeletonColumn } from "../components/ui/Skeleton.vue";
import TextInput from "../components/ui/TextInput.vue";
import { PAGE_SIZE } from "../features/inbox/listParams";
import { formatDay } from "../features/suppliers/iban";
import { plural } from "../features/review-screen/format";

type Supplier = components["schemas"]["Supplier"];

const SEARCH_DEBOUNCE_MS = 300;

const route = useRoute();
const router = useRouter();

function single(value: unknown): string {
  const first = Array.isArray(value) ? value[0] : value;
  return typeof first === "string" ? first : "";
}

const q = computed(() => single(route.query.q).trim());
const page = computed(() => {
  const value = Number.parseInt(single(route.query.page), 10);
  return Number.isFinite(value) && value > 1 ? value : 1;
});

const params = computed<SupplierListParams>(() => ({
  ...(q.value ? { q: q.value } : {}),
  ...(page.value > 1 ? { page: page.value } : {}),
}));

function update(next: { q?: string; page?: number }): void {
  const query: Record<string, string> = {};
  const nextQ = next.q ?? q.value;
  const nextPage = next.page ?? 1;
  if (nextQ) query.q = nextQ;
  if (nextPage > 1) query.page = String(nextPage);
  void router.push({ name: "suppliers", query });
}

const list = useQuery({
  queryKey: computed(() => queryKeys.suppliers.list(params.value)),
  queryFn: async ({ queryKey }) =>
    unwrap(
      await api.GET("/api/v1/suppliers", {
        params: { query: queryKey[2] as SupplierListParams },
      }),
    ),
  placeholderData: keepPreviousData,
});

const rows = computed<Supplier[]>(() => list.data.value?.results ?? []);
const total = computed(() => list.data.value?.count ?? 0);
const pageCount = computed(() =>
  Math.max(1, Math.ceil(total.value / PAGE_SIZE)),
);

// --- Search -------------------------------------------------------------------------

const searchText = ref(q.value);
let timer: ReturnType<typeof setTimeout> | undefined;

watch(q, (value) => {
  if (value !== searchText.value.trim()) searchText.value = value;
});

watch(searchText, (text) => {
  if (timer !== undefined) clearTimeout(timer);
  timer = setTimeout(() => {
    if (text.trim() !== q.value) update({ q: text.trim() });
  }, SEARCH_DEBOUNCE_MS);
});

onBeforeUnmount(() => {
  if (timer !== undefined) clearTimeout(timer);
});

function clearSearch(): void {
  searchText.value = "";
  update({ q: "" });
}

// --- States -------------------------------------------------------------------------

const error = computed(() => {
  if (!list.isError.value || list.data.value) return null;
  const value = list.error.value;
  if (value instanceof ApiError)
    return { title: value.title, detail: value.detail };
  return {
    title: "Couldn’t load the suppliers",
    detail: value instanceof Error ? value.message : undefined,
  };
});

const summary = computed(() =>
  list.data.value ? plural(total.value, "supplier") : "",
);

const COLUMNS: DataTableColumn<Supplier>[] = [
  { key: "name", label: "Supplier" },
  {
    key: "invoices",
    label: "Invoices",
    align: "right",
    mono: true,
    width: "96px",
    value: (row) => String(row.invoice_count),
  },
  {
    key: "first",
    label: "First invoice",
    width: "144px",
    value: (row) => formatDay(row.first_seen_at),
  },
  {
    key: "last",
    label: "Last invoice",
    width: "144px",
    value: (row) => formatDay(row.last_seen_at),
  },
];

const SKELETON_COLUMNS: SkeletonColumn[] = [
  { track: "minmax(0, 1fr)" },
  { track: "96px" },
  { track: "144px" },
  { track: "144px" },
];

function open(row: Supplier): void {
  void router.push({ name: "supplier", params: { id: row.id } });
}
</script>

<template>
  <section class="page" aria-labelledby="suppliers-title">
    <div class="pane">
      <header class="pane-head pane-head--page">
        <h1 id="suppliers-title" class="page-title">Suppliers</h1>
        <span class="muted">{{ summary }}</span>
        <span class="spacer" />
        <TextInput
          v-model="searchText"
          class="search"
          type="search"
          label="Search suppliers"
          placeholder="Supplier name"
        />
      </header>

      <div :aria-busy="list.isPlaceholderData.value">
        <Skeleton
          v-if="list.isPending.value"
          label="Loading suppliers"
          :columns="SKELETON_COLUMNS"
          :rows="6"
        />
        <ErrorState
          v-else-if="error"
          :title="error.title"
          :detail="error.detail"
          :retrying="list.isFetching.value"
          @retry="list.refetch()"
        />
        <EmptyState
          v-else-if="rows.length === 0 && q"
          class="empty"
          icon="search"
          title="No suppliers match"
          :body="`Nothing matches “${q}”. Check the spelling or clear the search.`"
        >
          <template #action>
            <Button @click="clearSearch">Clear search</Button>
          </template>
        </EmptyState>
        <EmptyState
          v-else-if="rows.length === 0"
          class="empty"
          icon="building"
          title="No suppliers yet"
          body="A supplier appears here when Eingang reads its first invoice."
        />
        <DataTable
          v-else
          caption="Suppliers"
          :columns="COLUMNS"
          :rows="rows"
          :row-key="(row) => row.id"
          @row-click="open"
        >
          <template #cell-name="{ row }">
            <span class="name-cell">
              <RouterLink
                class="name"
                :to="{ name: 'supplier', params: { id: row.id } }"
                >{{ row.name }}</RouterLink
              >
              <span v-if="row.vat_id" class="mono small muted">{{
                row.vat_id
              }}</span>
            </span>
          </template>
        </DataTable>
      </div>

      <nav v-if="pageCount > 1" class="pager" aria-label="Pages">
        <span class="pager-range">Page {{ page }} of {{ pageCount }}</span>
        <Button
          size="sm"
          icon="chevron-left"
          :disabled="page <= 1"
          @click="update({ page: page - 1 })"
          >Previous</Button
        >
        <Button
          size="sm"
          :disabled="page >= pageCount"
          @click="update({ page: page + 1 })"
          >Next<Icon name="chevron-right" :size="16"
        /></Button>
      </nav>
    </div>
  </section>
</template>

<style scoped src="../features/approvals/pane.css"></style>
<style scoped>
.search {
  width: min(280px, 100%);
}

.empty {
  min-height: 280px;
}

.name-cell {
  display: grid;
  gap: var(--space-4);
  min-width: 0;
}

.name {
  justify-self: start;
  color: var(--ink);
  font-size: var(--fs-14);
  font-weight: 500;
  text-decoration: none;
  overflow-wrap: anywhere;
}

.name:hover {
  text-decoration: underline;
}

@media (max-width: 767px) {
  .search {
    width: 100%;
  }
}
</style>
