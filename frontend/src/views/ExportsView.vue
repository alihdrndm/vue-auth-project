<script setup lang="ts">
// Exports (design "Eingang App Screens" ?screen=exports, HANDOFF `/app/exports`): export the
// approved invoices in one of three formats, with the count from /stats, and download past
// exports. Only admins and accountants may export; others see the button disabled with why.
import {
  keepPreviousData,
  useQuery,
  useQueryClient,
} from "@tanstack/vue-query";
import { computed, ref } from "vue";

import { api, ApiError, unwrap } from "../api/client";
import { queryKeys } from "../api/query";
import type { components } from "../api/schema";
import Button from "../components/ui/Button.vue";
import DataTable, {
  type DataTableColumn,
} from "../components/ui/DataTable.vue";
import ErrorState from "../components/ui/ErrorState.vue";
import Icon from "../components/ui/Icon.vue";
import Skeleton, { type SkeletonColumn } from "../components/ui/Skeleton.vue";
import { useToast } from "../components/ui/useToast";
import { PAGE_SIZE } from "../features/inbox/listParams";
import {
  type ExportFormat,
  exportBlockedReason,
  exportedMessage,
  FORMATS,
  formatLabel,
  readyText,
} from "../features/exports/exports";
import { problemMessage } from "../features/review-screen/actions";
import { formatDateTime, plural } from "../features/review-screen/format";
import { useSessionStore } from "../stores/session";

type ExportRow = components["schemas"]["Export"];
type ExportCreated = components["schemas"]["ExportCreated"];

const session = useSessionStore();
const queryClient = useQueryClient();
const toast = useToast();

// --- Ready count ------------------------------------------------------------------------

const stats = useQuery({
  queryKey: queryKeys.stats(),
  queryFn: async () => unwrap(await api.GET("/api/v1/stats")),
});

const ready = computed<number | null>(
  () => stats.data.value?.by_status.approved ?? null,
);

const readyLine = computed(() => {
  if (ready.value !== null) return readyText(ready.value);
  if (stats.isError.value) return "Couldn’t count the approved invoices.";
  return "Counting approved invoices…";
});

// --- Creating an export -------------------------------------------------------------------

const format = ref<ExportFormat>("csv_invoices");
const exporting = ref(false);
const nothingToExport = ref<string | null>(null);
const created = ref<ExportCreated | null>(null);

const blockedReason = computed(() => exportBlockedReason(session.role));

const exportLabel = computed(() => {
  if (exporting.value) return "Exporting…";
  if (ready.value === null) return "Export approved invoices";
  if (ready.value === 0) return "Export";
  return `Export ${plural(ready.value, "invoice")}`;
});

function download(url: string): void {
  const link = document.createElement("a");
  link.href = url;
  link.download = "";
  document.body.append(link);
  link.click();
  link.remove();
}

async function createExport(): Promise<void> {
  if (exporting.value || blockedReason.value) return;
  exporting.value = true;
  nothingToExport.value = null;
  created.value = null;
  try {
    const result = unwrap(
      await api.POST("/api/v1/exports", { body: { format: format.value } }),
    );
    created.value = result;
    toast.show({
      kind: "success",
      message: exportedMessage(result.row_count),
      action: { label: "Download", run: () => download(result.download_url) },
    });
    void queryClient.invalidateQueries({ queryKey: queryKeys.exports() });
    void queryClient.invalidateQueries({ queryKey: ["documents", "list"] });
  } catch (caught) {
    if (caught instanceof ApiError && caught.code === "NOTHING_TO_EXPORT") {
      nothingToExport.value =
        caught.detail || "There are no approved invoices to export.";
    } else {
      toast.show({ kind: "error", message: problemMessage(caught) });
    }
  } finally {
    exporting.value = false;
    void queryClient.invalidateQueries({ queryKey: queryKeys.stats() });
  }
}

// --- Past exports ------------------------------------------------------------------------

const page = ref(1);

const past = useQuery({
  queryKey: computed(() => queryKeys.exportsPage(page.value)),
  queryFn: async ({ queryKey }) =>
    unwrap(
      await api.GET("/api/v1/exports", {
        params: { query: queryKey[2] > 1 ? { page: queryKey[2] } : {} },
      }),
    ),
  placeholderData: keepPreviousData,
});

const rows = computed<ExportRow[]>(() => past.data.value?.results ?? []);
const pageCount = computed(() =>
  Math.max(1, Math.ceil((past.data.value?.count ?? 0) / PAGE_SIZE)),
);

const pastError = computed(() => {
  if (!past.isError.value || past.data.value) return null;
  const value = past.error.value;
  if (value instanceof ApiError)
    return { title: value.title, detail: value.detail };
  return {
    title: "Couldn’t load past exports",
    detail: value instanceof Error ? value.message : undefined,
  };
});

const COLUMNS: DataTableColumn<ExportRow>[] = [
  {
    key: "created",
    label: "Created",
    width: "168px",
    value: (row) => formatDateTime(row.created_at),
  },
  { key: "format", label: "Format", value: (row) => formatLabel(row.format) },
  {
    key: "count",
    label: "Invoices",
    width: "112px",
    value: (row) => plural(row.row_count, "invoice"),
  },
  {
    key: "by",
    label: "By",
    width: "144px",
    value: (row) => row.created_by_name,
  },
  { key: "download", label: "Download", width: "128px", align: "right" },
];

const SKELETON_COLUMNS: SkeletonColumn[] = [
  { track: "152px" },
  { track: "minmax(0, 1fr)" },
  { track: "100px" },
  { track: "120px" },
  { track: "120px" },
];
</script>

<template>
  <section class="page" aria-labelledby="exports-title">
    <h1 id="exports-title" class="page-title">Exports</h1>

    <div class="layout">
      <section class="pane" aria-labelledby="export-title">
        <div class="pane-head export-head">
          <h2 id="export-title" class="pane-title">Export approved invoices</h2>
          <span class="ready">{{ readyLine }}</span>
        </div>

        <fieldset class="formats">
          <legend class="formats-legend">Format</legend>
          <label
            v-for="look in FORMATS"
            :key="look.value"
            class="format"
            :class="{ 'is-on': format === look.value }"
          >
            <input
              v-model="format"
              class="format-input"
              type="radio"
              name="export-format"
              :value="look.value"
            />
            <span class="format-text">
              <span class="format-label">{{ look.label }}</span>
              <span class="format-help">{{ look.help }}</span>
            </span>
          </label>
        </fieldset>

        <p v-if="nothingToExport" class="problem" role="alert">
          <Icon name="info" :size="16" class="note-icon note-icon--info" />{{
            nothingToExport
          }}
        </p>
        <p v-if="created" class="done" role="status">
          <Icon name="circle-check" :size="16" />Your export of
          {{ plural(created.row_count, "invoice") }} is ready.
          <a class="link" :href="created.download_url" download
            ><Icon name="download" :size="16" />Download</a
          >
        </p>

        <div class="pane-foot">
          <span class="small muted"
            >Exported invoices move to the Exported tab.</span
          >
          <Button
            variant="primary"
            icon="download"
            :loading="exporting"
            :disabled="ready === 0"
            :disabled-reason="blockedReason ?? undefined"
            @click="createExport"
            >{{ exportLabel }}</Button
          >
        </div>
        <p v-if="blockedReason" class="note blocked">
          <Icon name="lock" :size="14" class="note-icon" />{{ blockedReason }}
        </p>
      </section>

      <section class="pane" aria-labelledby="past-title">
        <div class="pane-head">
          <h2 id="past-title" class="pane-title">Past exports</h2>
        </div>
        <Skeleton
          v-if="past.isPending.value"
          label="Loading past exports"
          :columns="SKELETON_COLUMNS"
          :rows="3"
        />
        <ErrorState
          v-else-if="pastError"
          :level="3"
          :title="pastError.title"
          :detail="pastError.detail"
          :retrying="past.isFetching.value"
          @retry="past.refetch()"
        />
        <p v-else-if="rows.length === 0" class="empty-line">
          No exports yet. Your first export appears here.
        </p>
        <DataTable
          v-else
          caption="Past exports"
          :columns="COLUMNS"
          :rows="rows"
          :row-key="(row) => row.id"
          :clickable-rows="false"
        >
          <template #cell-download="{ row }">
            <a
              class="link"
              :href="row.download_url"
              download
              :aria-label="`Download the export of ${formatDateTime(row.created_at)}`"
              ><Icon name="download" :size="16" />Download</a
            >
          </template>
        </DataTable>
        <nav v-if="pageCount > 1" class="pager" aria-label="Pages">
          <span class="pager-range">Page {{ page }} of {{ pageCount }}</span>
          <Button
            size="sm"
            icon="chevron-left"
            :disabled="page <= 1"
            @click="page -= 1"
            >Previous</Button
          >
          <Button size="sm" :disabled="page >= pageCount" @click="page += 1"
            >Next<Icon name="chevron-right" :size="16"
          /></Button>
        </nav>
      </section>
    </div>
  </section>
</template>

<style scoped src="../features/approvals/pane.css"></style>
<style scoped>
.layout {
  display: grid;
  grid-template-columns: minmax(0, 420px) minmax(0, 1fr);
  gap: var(--space-16);
  align-items: start;
}

.export-head {
  display: grid;
  gap: var(--space-4);
}

.ready {
  color: var(--text);
  font-size: var(--fs-13);
}

.formats {
  display: grid;
  gap: var(--space-8);
  margin: 0;
  padding: var(--space-16) var(--space-20);
  border: 0;
}

.formats-legend {
  padding: 0 0 var(--space-8);
  color: var(--ink);
  font-size: var(--fs-13);
  font-weight: 500;
}

.format {
  display: grid;
  grid-template-columns: 20px minmax(0, 1fr);
  gap: var(--space-12);
  align-items: start;
  padding: var(--space-12);
  border: 1px solid var(--line-strong);
  border-radius: var(--r-md);
  background: var(--win);
  cursor: pointer;
}

.format:hover {
  border-color: var(--muted);
}

.format.is-on {
  border-color: var(--ink);
  background: var(--soft);
}

.format:focus-within {
  outline: var(--focus-width) solid var(--focus);
  outline-offset: var(--focus-offset);
}

.format-input {
  width: 18px;
  height: 18px;
  margin: 1px 0 0;
  accent-color: var(--ink);
}

.format-input:focus-visible {
  outline: none;
}

.format-text {
  display: grid;
  gap: var(--space-4);
}

.format-label {
  color: var(--ink);
  font-size: var(--fs-14);
  font-weight: 500;
}

.format-help {
  color: var(--muted-strong);
  font-size: var(--fs-12);
}

.problem,
.done {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-8);
  margin: 0;
  padding: 0 var(--space-20) var(--space-16);
  color: var(--text);
  font-size: var(--fs-13);
}

.done {
  color: var(--ok);
}

.link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-4);
  color: var(--ink);
  font-size: var(--fs-13);
  font-weight: 500;
}

.blocked {
  padding: 0 var(--space-20) var(--space-12);
  background: var(--bar);
}

@media (max-width: 1023px) {
  .layout {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 767px) {
  .formats,
  .problem,
  .done,
  .blocked {
    padding-right: var(--space-16);
    padding-left: var(--space-16);
  }
}
</style>
