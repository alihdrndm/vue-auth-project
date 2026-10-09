<script setup lang="ts">
// Approvals (design "Eingang App Screens" ?screen=approvals, HANDOFF `/app/approvals`): the
// invoices awaiting approval as compact rows with the bank account tag, open warnings and the
// Approve / Reject… decisions from `allowed_actions`; disabled ones show the API's reason.
import {
  keepPreviousData,
  useQuery,
  useQueryClient,
} from "@tanstack/vue-query";
import { computed, nextTick, ref, watch } from "vue";

import { api, ApiError, unwrap } from "../api/client";
import { queryKeys, type DocumentListParams } from "../api/query";
import Badge from "../components/ui/Badge.vue";
import Button from "../components/ui/Button.vue";
import DataTable, {
  type DataTableColumn,
} from "../components/ui/DataTable.vue";
import Dialog from "../components/ui/Dialog.vue";
import EmptyState from "../components/ui/EmptyState.vue";
import ErrorState from "../components/ui/ErrorState.vue";
import Icon from "../components/ui/Icon.vue";
import Skeleton, { type SkeletonColumn } from "../components/ui/Skeleton.vue";
import TextArea from "../components/ui/TextArea.vue";
import { useToast } from "../components/ui/useToast";
import {
  type Decision,
  decisionActions,
  disabledReasons,
  documentNumber,
  warningsText,
} from "../features/approvals/approvals";
import { PAGE_SIZE } from "../features/inbox/listParams";
import {
  type DocumentSummary,
  formatDue,
  formatGross,
} from "../features/inbox/rows";
import { NOTE_MAX, NOTE_MIN } from "../features/review/checks";
import {
  problemMessage,
  successMessage,
} from "../features/review-screen/actions";
import { useMediaQuery } from "../features/review-screen/useMediaQuery";
import { maskedIban } from "../features/suppliers/iban";
import IbanTag from "../features/suppliers/IbanTag.vue";
import { useSessionStore } from "../stores/session";

const session = useSessionStore();
const queryClient = useQueryClient();
const toast = useToast();
const phone = useMediaQuery("(max-width: 767px)");

const page = ref(1);
const params = computed<DocumentListParams>(() => ({
  status: "awaiting_approval",
  ordering: "due_date",
  ...(page.value > 1 ? { page: page.value } : {}),
}));

const list = useQuery({
  queryKey: computed(() => queryKeys.documents.list(params.value)),
  queryFn: async ({ queryKey }) =>
    unwrap(
      await api.GET("/api/v1/documents", {
        params: { query: queryKey[2] as DocumentListParams },
      }),
    ),
  placeholderData: keepPreviousData,
});

const rows = computed<DocumentSummary[]>(() => list.data.value?.results ?? []);
const total = computed(() => list.data.value?.count ?? 0);
const pageCount = computed(() =>
  Math.max(1, Math.ceil(total.value / PAGE_SIZE)),
);

// A decision can empty the last page: step back to one that has rows.
watch(pageCount, (count) => {
  if (page.value > count) page.value = count;
});

const fourEyes = computed(() => session.me?.organization.four_eyes === true);

const error = computed(() => {
  if (!list.isError.value || list.data.value) return null;
  const value = list.error.value;
  if (value instanceof ApiError)
    return { title: value.title, detail: value.detail };
  return {
    title: "Couldn’t load the approvals",
    detail: value instanceof Error ? value.message : undefined,
  };
});

const COLUMNS: DataTableColumn<DocumentSummary>[] = [
  { key: "supplier", label: "Supplier" },
  { key: "gross", label: "Gross", align: "right", mono: true, width: "128px" },
  { key: "due", label: "Due", width: "112px" },
  { key: "iban", label: "Bank account", width: "248px" },
  { key: "warnings", label: "Open warnings", width: "136px" },
  { key: "reviewer", label: "Reviewed by", width: "160px" },
  { key: "actions", label: "Actions", width: "220px" },
];

const SKELETON_COLUMNS: SkeletonColumn[] = [
  { track: "minmax(0, 1fr)" },
  { track: "112px" },
  { track: "112px" },
  { track: "248px", shape: "chip" },
  { track: "120px" },
  { track: "160px" },
  { track: "200px", shape: "chip" },
];

// --- Decisions --------------------------------------------------------------------------

const busy = ref<{ id: string; decision: Decision } | null>(null);

function isBusy(doc: DocumentSummary, decision: Decision): boolean {
  return busy.value?.id === doc.id && busy.value.decision === decision;
}

const rejecting = ref<DocumentSummary | null>(null);
const note = ref("");
const tried = ref(false);
const serverError = ref<string | null>(null);

const dialogOpen = computed({
  get: () => rejecting.value !== null,
  set: (value: boolean) => {
    if (!value && busy.value === null) rejecting.value = null;
  },
});

const noteError = computed(() => {
  if (serverError.value) return serverError.value;
  if (!tried.value) return undefined;
  const length = note.value.trim().length;
  if (length < NOTE_MIN) return `Write at least ${NOTE_MIN} characters.`;
  if (length > NOTE_MAX) return `Write at most ${NOTE_MAX} characters.`;
  return undefined;
});

const dialogDescription = computed(() => {
  const doc = rejecting.value;
  if (!doc) return undefined;
  const who = doc.reviewed_by_name
    ? `${doc.reviewed_by_name} sees your reason`
    : "Your reason is saved";
  return `${doc.supplier_name ?? "Unknown supplier"}, ${formatGross(doc)}. ${who} in the invoice’s activity.`;
});

watch(note, () => {
  serverError.value = null;
});

async function decide(
  doc: DocumentSummary,
  decision: Decision,
  comment = "",
): Promise<void> {
  if (busy.value) return;
  busy.value = { id: doc.id, decision };
  const number = documentNumber(doc);
  try {
    unwrap(
      await api.POST("/api/v1/documents/{document_id}/decision", {
        params: { path: { document_id: doc.id } },
        body: {
          decision: decision === "approve" ? "approved" : "rejected",
          comment,
        },
      }),
    );
    busy.value = null;
    rejecting.value = null;
    toast.show({ kind: "success", message: successMessage(decision, number) });
    void queryClient.invalidateQueries({
      queryKey: queryKeys.documents.detail(doc.id),
    });
    void queryClient.invalidateQueries({ queryKey: queryKeys.stats() });
    await queryClient.invalidateQueries({ queryKey: ["documents", "list"] });
    await nextTick();
    focusNextDecision();
  } catch (caught) {
    busy.value = null;
    const fieldError =
      caught instanceof ApiError && caught.status === 422
        ? caught.errors.find((entry) => entry.path.includes("comment"))?.message
        : undefined;
    if (fieldError && rejecting.value) {
      serverError.value = fieldError;
      return;
    }
    toast.show({ kind: "error", message: problemMessage(caught) });
    // The row may have changed meanwhile (decided by someone else, sent back): reload it.
    void list.refetch();
  }
}

/** The decided row is gone: keep keyboard focus on the next decision, or the title. */
function focusNextDecision(): void {
  const next = document.querySelector<HTMLButtonElement>(
    ".card-actions button:not([disabled]), .actions button:not([disabled])",
  );
  (next ?? document.getElementById("approvals-title"))?.focus();
}

function start(doc: DocumentSummary, decision: Decision): void {
  if (decision === "approve") {
    void decide(doc, "approve");
    return;
  }
  note.value = "";
  tried.value = false;
  serverError.value = null;
  rejecting.value = doc;
}

function confirmReject(): void {
  const doc = rejecting.value;
  if (!doc) return;
  tried.value = true;
  serverError.value = null;
  if (noteError.value) return;
  void decide(doc, "reject", note.value.trim());
}

function label(doc: DocumentSummary, decision: Decision): string {
  if (isBusy(doc, decision))
    return decision === "approve" ? "Approving…" : "Rejecting…";
  return decision === "approve" ? "Approve" : "Reject…";
}
</script>

<template>
  <section class="page" aria-labelledby="approvals-title">
    <div class="pane">
      <header class="pane-head pane-head--page">
        <h1 id="approvals-title" class="page-title" tabindex="-1">Approvals</h1>
        <Badge v-if="list.data.value">{{ total }}</Badge>
        <span class="spacer" />
        <p v-if="fourEyes" class="note">
          <Icon name="lock" :size="16" class="note-icon" />Four-eyes is on:
          nobody approves an invoice they reviewed themselves.
        </p>
      </header>

      <div :aria-busy="list.isPlaceholderData.value">
        <Skeleton
          v-if="list.isPending.value"
          label="Loading approvals"
          :columns="SKELETON_COLUMNS"
          :rows="4"
        />
        <ErrorState
          v-else-if="error"
          :title="error.title"
          :detail="error.detail"
          :retrying="list.isFetching.value"
          @retry="list.refetch()"
        />
        <EmptyState
          v-else-if="rows.length === 0"
          class="empty"
          icon="circle-check"
          title="Nothing waiting for you"
          body="Invoices arrive here once someone else marks them reviewed."
        />

        <ul v-else-if="phone" class="cards">
          <li v-for="doc in rows" :key="doc.id" class="card">
            <div class="card-head">
              <span class="supplier">{{
                doc.supplier_name ?? "Unknown supplier"
              }}</span>
              <RouterLink
                class="number mono"
                :to="{ name: 'invoice', params: { id: doc.id } }"
                >{{ documentNumber(doc) }}</RouterLink
              >
            </div>
            <div class="card-line">
              <span class="gross mono">{{ formatGross(doc) }}</span>
              <span>Due {{ formatDue(doc.due_date) }}</span>
            </div>
            <div class="card-line card-line--start">
              <span class="mono">{{ maskedIban(doc.payee_iban_last4) }}</span>
              <IbanTag v-if="doc.iban_status" :status="doc.iban_status" />
            </div>
            <span class="muted"
              >Reviewed by {{ doc.reviewed_by_name ?? "—" }}. Open warnings:
              {{ warningsText(doc) }}.</span
            >
            <div class="card-actions">
              <Button
                v-for="action in decisionActions(doc)"
                :key="action.action"
                size="lg"
                :variant="action.action === 'approve' ? 'primary' : 'danger'"
                :icon="action.action === 'approve' ? 'check' : undefined"
                :loading="isBusy(doc, action.action as Decision)"
                :disabled="
                  !action.enabled ||
                  (busy !== null && !isBusy(doc, action.action as Decision))
                "
                @click="start(doc, action.action as Decision)"
                >{{ label(doc, action.action as Decision) }}</Button
              >
            </div>
            <p
              v-for="reason in disabledReasons(doc)"
              :key="reason"
              class="note"
            >
              <Icon
                name="info"
                :size="16"
                class="note-icon note-icon--info"
              />{{ reason }}
            </p>
          </li>
        </ul>

        <DataTable
          v-else
          caption="Invoices awaiting approval"
          :columns="COLUMNS"
          :rows="rows"
          :row-key="(doc) => doc.id"
          :clickable-rows="false"
        >
          <template #cell-supplier="{ row }">
            <span class="supplier-cell">
              <span class="supplier">{{
                row.supplier_name ?? "Unknown supplier"
              }}</span>
              <RouterLink
                class="number mono"
                :to="{ name: 'invoice', params: { id: row.id } }"
                >{{ documentNumber(row) }}</RouterLink
              >
            </span>
          </template>
          <template #cell-gross="{ row }">{{ formatGross(row) }}</template>
          <template #cell-due="{ row }">{{ formatDue(row.due_date) }}</template>
          <template #cell-iban="{ row }">
            <span class="iban-cell">
              <span class="mono">{{ maskedIban(row.payee_iban_last4) }}</span>
              <IbanTag v-if="row.iban_status" :status="row.iban_status" />
            </span>
          </template>
          <template #cell-warnings="{ row }">
            <span
              :class="
                row.open_warn_checks + row.open_block_checks > 0
                  ? 'warnings'
                  : 'muted'
              "
              >{{ warningsText(row) }}</span
            >
          </template>
          <template #cell-reviewer="{ row }">{{
            row.reviewed_by_name ?? "—"
          }}</template>
          <template #cell-actions="{ row }">
            <span class="actions-cell">
              <span class="actions">
                <Button
                  v-for="action in decisionActions(row)"
                  :key="action.action"
                  size="sm"
                  :variant="action.action === 'approve' ? 'primary' : 'danger'"
                  :icon="action.action === 'approve' ? 'check' : undefined"
                  :loading="isBusy(row, action.action as Decision)"
                  :disabled="
                    !action.enabled ||
                    (busy !== null && !isBusy(row, action.action as Decision))
                  "
                  @click="start(row, action.action as Decision)"
                  >{{ label(row, action.action as Decision)
                  }}<span class="sr-only">
                    {{ documentNumber(row) }}</span
                  ></Button
                >
              </span>
              <span
                v-for="reason in disabledReasons(row)"
                :key="reason"
                class="reason"
                ><Icon name="info" :size="14" class="note-icon--info" />{{
                  reason
                }}</span
              >
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
          @click="page -= 1"
          >Previous</Button
        >
        <Button size="sm" :disabled="page >= pageCount" @click="page += 1"
          >Next<Icon name="chevron-right" :size="16"
        /></Button>
      </nav>
    </div>

    <Dialog
      v-model:open="dialogOpen"
      :title="`Reject invoice ${rejecting ? documentNumber(rejecting) : ''}?`"
      :description="dialogDescription"
      size="md"
    >
      <TextArea
        v-model="note"
        label="Reason (required)"
        placeholder="What should the supplier correct?"
        :maxlength="NOTE_MAX"
        counter
        :error="noteError"
        hint="5 to 500 characters. Saved in the invoice’s activity."
      />
      <template #footer>
        <Button
          variant="ghost"
          :disabled="busy !== null"
          @click="dialogOpen = false"
          >Cancel</Button
        >
        <Button
          variant="danger"
          :loading="busy !== null"
          @click="confirmReject"
          >{{ busy !== null ? "Rejecting…" : "Reject invoice" }}</Button
        >
      </template>
    </Dialog>
  </section>
</template>

<style scoped src="../features/approvals/pane.css"></style>
<style scoped>
.empty {
  min-height: 280px;
}

.supplier-cell,
.actions-cell {
  display: grid;
  gap: var(--space-4);
  min-width: 0;
}

.supplier {
  color: var(--ink);
  font-size: var(--fs-14);
  font-weight: 500;
  overflow-wrap: anywhere;
}

.number {
  justify-self: start;
  color: var(--muted-strong);
  font-size: var(--fs-12);
  text-decoration: none;
  overflow-wrap: anywhere;
}

.number:hover {
  color: var(--ink);
  text-decoration: underline;
}

.iban-cell {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-4) var(--space-8);
  color: var(--ink);
}

.warnings {
  color: var(--info);
  font-size: var(--fs-13);
}

.actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: var(--space-8);
}

.reason {
  display: flex;
  align-items: flex-start;
  gap: var(--space-4);
  color: var(--text);
  font-size: var(--fs-12);
  white-space: normal;
}

.cards {
  display: grid;
  gap: var(--space-12);
  margin: 0;
  padding: var(--space-12);
  list-style: none;
}

.card {
  display: grid;
  gap: var(--space-8);
  padding: var(--space-16);
  border: 1px solid var(--line);
  border-radius: var(--r-lg);
  background: var(--win);
}

.card-head {
  display: grid;
  gap: var(--space-4);
}

.card-head .supplier {
  font-size: var(--fs-16);
  font-weight: 600;
}

.card-line {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-8);
  font-size: var(--fs-13);
}

.card-line--start {
  justify-content: flex-start;
  align-items: center;
}

.gross {
  color: var(--ink);
  font-size: var(--fs-16);
}

.card-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-8);
}

.card-actions :deep(.button-wrap),
.card-actions :deep(.button) {
  width: 100%;
  justify-content: center;
}
</style>
