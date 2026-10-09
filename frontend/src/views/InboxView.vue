<script setup lang="ts">
// The inbox (design "Eingang App Inbox", HANDOFF `/app/inbox`): status tabs with counts from
// /stats, search and filters in the URL, the document list with live processing steps, and the
// upload zone. The list state is described in features/inbox/listParams.ts.
import {
  keepPreviousData,
  useQuery,
  useQueryClient,
} from "@tanstack/vue-query";
import {
  computed,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
  type ComponentPublicInstance,
} from "vue";
import { useRoute, useRouter, type RouteLocationRaw } from "vue-router";

import { api, ApiError, unwrap } from "../api/client";
import { queryKeys, type DocumentListParams } from "../api/query";
import type { components } from "../api/schema";
import Button from "../components/ui/Button.vue";
import type { DataTableSort } from "../components/ui/DataTable.vue";
import EmptyState from "../components/ui/EmptyState.vue";
import ErrorState from "../components/ui/ErrorState.vue";
import Icon from "../components/ui/Icon.vue";
import Select from "../components/ui/Select.vue";
import Skeleton, { type SkeletonColumn } from "../components/ui/Skeleton.vue";
import Tabs, { type TabItem } from "../components/ui/Tabs.vue";
import TextInput from "../components/ui/TextInput.vue";
import InboxTable from "../features/inbox/InboxTable.vue";
import {
  EMPTY_COPY,
  isFiltered,
  listParams,
  NO_RESULTS_COPY,
  PAGE_SIZE,
  queryFromState,
  serializeFrom,
  stateFromQuery,
  TABS,
  type InboxState,
  type InboxTab,
  type Ordering,
} from "../features/inbox/listParams";
import {
  formatOptions,
  isProcessing,
  PROCESSING_POLL_MS,
  type DocumentSummary,
} from "../features/inbox/rows";
import UploadZone from "../features/upload/UploadZone.vue";

type Supplier = components["schemas"]["Supplier"];

const SEARCH_DEBOUNCE_MS = 300;
const PHONE_QUERY = "(max-width: 767px)";

const route = useRoute();
const router = useRouter();
const queryClient = useQueryClient();

const state = computed(() => stateFromQuery(route.query));
const params = computed(() => listParams(state.value));

function update(patch: Partial<InboxState>): void {
  // Any change other than the page itself starts again at page 1.
  const next = { ...state.value, page: 1, ...patch };
  void router.push({ name: "inbox", query: queryFromState(next) });
}

// --- Data ---------------------------------------------------------------------------

const list = useQuery({
  queryKey: computed(() => queryKeys.documents.list(params.value)),
  queryFn: async ({ queryKey }) =>
    unwrap(
      await api.GET("/api/v1/documents", {
        params: { query: queryKey[2] as DocumentListParams },
      }),
    ),
  placeholderData: keepPreviousData,
  // Poll while anything on the page is received or processing; the default query options stop
  // polling while the browser tab is hidden.
  refetchInterval: (query) =>
    query.state.data?.results.some(isProcessing) ? PROCESSING_POLL_MS : false,
});

const stats = useQuery({
  queryKey: queryKeys.stats(),
  queryFn: async () => unwrap(await api.GET("/api/v1/stats")),
});

const suppliers = useQuery({
  queryKey: queryKeys.suppliers.options(),
  queryFn: async () => {
    const all: Supplier[] = [];
    for (let page = 1; page <= 40; page += 1) {
      const data = unwrap(
        await api.GET("/api/v1/suppliers", { params: { query: { page } } }),
      );
      all.push(...data.results);
      if (!data.next) break;
    }
    return all;
  },
  staleTime: 60_000,
});

const rows = computed<DocumentSummary[]>(() => list.data.value?.results ?? []);
const total = computed(() => list.data.value?.count ?? 0);

// --- Tabs ---------------------------------------------------------------------------

const tabItems = computed<TabItem[]>(() => {
  const byStatus = stats.data.value?.by_status;
  return TABS.map(({ key, label }) => {
    if (!byStatus) return { key, label };
    const count =
      key === "all"
        ? Object.values(byStatus).reduce((sum, n) => sum + n, 0)
        : byStatus[key];
    return { key, label, count };
  });
});

const tab = computed<string>({
  get: () => state.value.tab,
  set: (key) => update({ tab: key as InboxTab }),
});

// --- Search and filters ---------------------------------------------------------------

const searchText = ref(state.value.q);
let searchTimer: ReturnType<typeof setTimeout> | undefined;

watch(
  () => state.value.q,
  (q) => {
    if (q !== searchText.value.trim()) searchText.value = q;
  },
);

watch(searchText, (text) => {
  if (searchTimer !== undefined) clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    if (text.trim() !== state.value.q) update({ q: text.trim() });
  }, SEARCH_DEBOUNCE_MS);
});

const supplierOptions = computed(() => [
  { value: "", label: "All suppliers" },
  ...(suppliers.data.value ?? [])
    .map((supplier) => ({ value: supplier.id, label: supplier.name }))
    .sort((a, b) => a.label.localeCompare(b.label, "de")),
]);

const seenFormats = ref<string[]>([]);
watch(
  rows,
  (current) => {
    const labels = current
      .map((row) => row.format_label)
      .filter((label): label is string => Boolean(label));
    const added = labels.filter((label) => !seenFormats.value.includes(label));
    if (added.length) seenFormats.value = [...seenFormats.value, ...added];
  },
  { immediate: true },
);

const formatSelectOptions = computed(() => [
  { value: "", label: "All formats" },
  ...formatOptions([
    ...seenFormats.value,
    ...(state.value.format ? [state.value.format] : []),
  ]).map((label) => ({ value: label, label })),
]);

const supplier = computed<string>({
  get: () => state.value.supplier,
  set: (value) => update({ supplier: value }),
});

const format = computed<string>({
  get: () => state.value.format,
  set: (value) => update({ format: value }),
});

const hasFilters = computed(() =>
  Boolean(state.value.supplier || state.value.format),
);

function clearFilters(): void {
  update({ supplier: "", format: "" });
}

function clearSearch(): void {
  searchText.value = "";
  update({ q: "" });
}

function clearAll(): void {
  searchText.value = "";
  update({ q: "", supplier: "", format: "" });
}

// --- Sorting --------------------------------------------------------------------------

const SORT_OF: Record<Ordering, DataTableSort> = {
  "-received_at": { key: "received", direction: "descending" },
  received_at: { key: "received", direction: "ascending" },
  "-gross_total": { key: "gross", direction: "descending" },
  due_date: { key: "due", direction: "ascending" },
};

/** The API sorts gross only from high to low and due dates only from soonest. */
const sort = computed<DataTableSort | null>({
  get: () => SORT_OF[state.value.ordering],
  set: (value) => {
    if (!value) return;
    let ordering: Ordering = "-received_at";
    // As in the design, a newly picked Received column starts with the newest first.
    const current = SORT_OF[state.value.ordering].key;
    if (value.key === "received")
      ordering =
        value.direction === "ascending" && current === "received"
          ? "received_at"
          : "-received_at";
    else if (value.key === "gross") ordering = "-gross_total";
    else if (value.key === "due") ordering = "due_date";
    if (ordering !== state.value.ordering) update({ ordering });
  },
});

// --- Paging ---------------------------------------------------------------------------

const pageCount = computed(() =>
  Math.max(1, Math.ceil(total.value / PAGE_SIZE)),
);
const rangeText = computed(() => {
  const start = (state.value.page - 1) * PAGE_SIZE + 1;
  const end = Math.min(total.value, start + rows.value.length - 1);
  return `${start}–${end} of ${total.value}`;
});

function goToPage(page: number): void {
  update({ page });
}

// --- Opening a row ----------------------------------------------------------------------

/**
 * The review screen gets the list parameters as `from` (URL-encoded GET /documents query, see
 * `serializeFrom`) so `j`/`k` can walk the same list.
 */
function reviewLocation(row: DocumentSummary): RouteLocationRaw {
  return {
    name: "invoice",
    params: { id: row.id },
    query: { from: serializeFrom(params.value) },
  };
}

function open(row: DocumentSummary): void {
  void router.push(reviewLocation(row));
}

// --- Live processing -------------------------------------------------------------------

const processingIds = computed(() =>
  rows.value.filter(isProcessing).map((row) => row.id),
);

const liveMessage = computed(() => {
  const n = processingIds.value.length;
  if (n === 0) return "";
  return n === 1
    ? "1 invoice is being processed"
    : `${n} invoices are being processed`;
});

// When a row finishes processing, the tab counts change too.
watch(processingIds, (now, before) => {
  if (before.some((id) => !now.includes(id)))
    void queryClient.invalidateQueries({ queryKey: queryKeys.stats() });
});

// --- Upload ---------------------------------------------------------------------------

const uploadZone = ref<ComponentPublicInstance | null>(null);
const uploadHost = ref<HTMLElement | null>(null);

function onUploaded(): void {
  void queryClient.invalidateQueries({ queryKey: ["documents", "list"] });
  void queryClient.invalidateQueries({ queryKey: queryKeys.stats() });
}

/** The "All" empty state's action opens the upload zone's own file picker. */
function startUpload(): void {
  const zone = uploadZone.value as
    (ComponentPublicInstance & { open?: () => void }) | null;
  if (typeof zone?.open === "function") {
    zone.open();
    return;
  }
  uploadHost.value?.querySelector<HTMLButtonElement>("button")?.click();
}

// --- States ---------------------------------------------------------------------------

const isLoading = computed(() => list.isPending.value);
const error = computed(() => {
  if (!list.isError.value || list.data.value) return null;
  const value = list.error.value;
  if (value instanceof ApiError)
    return { title: value.title, detail: value.detail };
  return {
    title: "Couldn’t load the inbox",
    detail: value instanceof Error ? value.message : undefined,
  };
});

const emptyCopy = computed(() =>
  isFiltered(state.value) ? NO_RESULTS_COPY : EMPTY_COPY[state.value.tab],
);

const SKELETON_COLUMNS: SkeletonColumn[] = [
  { track: "112px", shape: "chip" },
  { track: "minmax(0, 1fr)" },
  { track: "124px" },
  { track: "112px" },
  { track: "112px" },
  { track: "164px", shape: "chip" },
  { track: "144px", shape: "chip" },
  { track: "152px", shape: "chip" },
  { track: "72px" },
  { track: "176px", shape: "chip" },
];

// --- Phone layout ----------------------------------------------------------------------

const phone = ref(false);
let media: MediaQueryList | undefined;

function onMedia(): void {
  phone.value = media?.matches ?? false;
}

onMounted(() => {
  if (typeof window.matchMedia !== "function") return;
  media = window.matchMedia(PHONE_QUERY);
  onMedia();
  media.addEventListener("change", onMedia);
});

onBeforeUnmount(() => {
  media?.removeEventListener("change", onMedia);
  if (searchTimer !== undefined) clearTimeout(searchTimer);
});
</script>

<template>
  <section class="inbox" aria-labelledby="inbox-title">
    <header class="inbox-header">
      <h1 id="inbox-title" class="inbox-title">Inbox</h1>
      <span class="spacer" />
      <div ref="uploadHost" class="upload-host">
        <UploadZone ref="uploadZone" @uploaded="onUploaded" />
      </div>
    </header>

    <div class="inbox-bar">
      <Tabs
        v-model="tab"
        class="inbox-tabs"
        label="Inbox filters"
        :items="tabItems"
      />
      <div class="inbox-filters">
        <TextInput
          v-if="phone"
          v-model="searchText"
          class="inbox-search"
          type="search"
          label="Search invoices"
          size="lg"
          placeholder="Search suppliers and numbers"
        />
        <button
          v-else-if="state.q"
          type="button"
          class="filter-clear"
          :aria-label="`Clear search “${state.q}”`"
          @click="clearSearch"
        >
          <Icon name="search" :size="14" />“{{ state.q }}”<Icon
            name="x"
            :size="14"
          />
        </button>
        <Select
          v-model="supplier"
          label="Supplier"
          inline
          :size="phone ? 'lg' : 'md'"
          :options="supplierOptions"
        />
        <Select
          v-model="format"
          label="Format"
          inline
          :size="phone ? 'lg' : 'md'"
          :options="formatSelectOptions"
        />
        <button
          v-if="hasFilters"
          type="button"
          class="filter-clear"
          @click="clearFilters"
        >
          <Icon name="x" :size="14" />Clear filters
        </button>
      </div>
    </div>

    <p class="sr-only" aria-live="polite">{{ liveMessage }}</p>

    <div class="inbox-body" :aria-busy="list.isPlaceholderData.value">
      <Skeleton
        v-if="isLoading"
        label="Loading invoices"
        :columns="SKELETON_COLUMNS"
        :rows="8"
      />
      <ErrorState
        v-else-if="error"
        :title="error.title"
        :detail="error.detail"
        :retrying="list.isFetching.value"
        @retry="list.refetch()"
      />
      <template v-else>
        <InboxTable
          v-model:sort="sort"
          :rows="rows"
          :query="state.q"
          :phone="phone"
          :link-for="reviewLocation"
          @open="open"
        >
          <template #empty>
            <EmptyState
              class="inbox-empty"
              :icon="emptyCopy.icon"
              :title="emptyCopy.title"
              :body="emptyCopy.body"
            >
              <template v-if="isFiltered(state)" #action>
                <Button @click="clearAll">{{ NO_RESULTS_COPY.action }}</Button>
              </template>
              <template v-else-if="state.tab === 'all'" #action>
                <Button variant="primary" icon="upload" @click="startUpload"
                  >Upload invoices</Button
                >
              </template>
            </EmptyState>
          </template>
        </InboxTable>

        <nav v-if="pageCount > 1" class="pager" aria-label="Pages">
          <span class="pager-range">{{ rangeText }}</span>
          <Button
            size="sm"
            icon="chevron-left"
            :disabled="state.page <= 1"
            @click="goToPage(state.page - 1)"
            >Previous</Button
          >
          <span class="pager-page"
            >Page {{ state.page }} of {{ pageCount }}</span
          >
          <Button
            size="sm"
            :disabled="state.page >= pageCount"
            @click="goToPage(state.page + 1)"
            >Next<Icon name="chevron-right" :size="16"
          /></Button>
        </nav>
      </template>
    </div>
  </section>
</template>

<style scoped>
.inbox {
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  min-height: 0;
  border: 1px solid var(--line);
  border-radius: var(--r-lg);
  background: var(--win);
  overflow: hidden;
}

.inbox-header {
  display: flex;
  align-items: center;
  gap: var(--space-12);
  min-height: var(--size-phone-header);
  padding: var(--space-8) var(--space-16) var(--space-8) var(--space-20);
  border-bottom: 1px solid var(--line);
  background: var(--bar);
}

.inbox-title {
  margin: 0;
  color: var(--ink);
  font: 700 var(--fs-21) / var(--lh-tight) var(--font-head);
  letter-spacing: var(--tracking-head);
}

.spacer {
  flex: 1;
}

.inbox-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-8) var(--space-24);
  padding: 0 var(--space-16) 0 var(--space-12);
  border-bottom: 1px solid var(--line);
}

.inbox-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-12);
  padding: var(--space-8) 0;
}

.filter-clear {
  display: inline-flex;
  align-items: center;
  gap: var(--space-4);
  height: var(--size-md);
  padding: 0 var(--space-8);
  border: 1px solid transparent;
  border-radius: var(--r-sm);
  background: transparent;
  color: var(--text);
  font-size: var(--fs-13);
  font-weight: 500;
  cursor: pointer;
}

.filter-clear:hover {
  background: var(--soft);
  color: var(--ink);
}

.inbox-body {
  min-width: 0;
  min-height: 0;
  overflow: auto;
}

.inbox-empty {
  min-height: 320px;
}

.pager {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-12);
  padding: var(--space-12) var(--space-16);
  border-top: 1px solid var(--line);
  font-size: var(--fs-13);
}

.pager-range {
  margin-right: auto;
  color: var(--muted-strong);
}

.pager-page {
  color: var(--text);
}

@media (max-width: 767px) {
  .inbox {
    border: 0;
    border-radius: 0;
    background: transparent;
  }

  .inbox-header {
    padding: var(--space-8) 0;
    border-bottom: 0;
    background: transparent;
  }

  .inbox-bar {
    flex-direction: column-reverse;
    align-items: stretch;
    padding: 0;
    border-bottom: 0;
  }

  .inbox-tabs {
    overflow-x: auto;
    border-bottom: 1px solid var(--line);
  }

  .inbox-filters {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }

  .inbox-search {
    grid-column: 1 / -1;
  }

  .inbox-body {
    padding: var(--space-12) 0;
  }

  .filter-clear {
    height: var(--size-lg);
  }
}
</style>
