<script setup lang="ts">
// The status header of the review screen: supplier, number, received chip, format and
// validation chips, amount and due date, and the document's `allowed_actions` as buttons.
// Disabled actions keep their button and show the API's reason as text and as the button's
// description. Reject and Send back ask for a 5–500 character note; Delete asks to confirm.
import { computed, ref, watch } from "vue";

import { api, ApiError, unwrap } from "../../api/client";
import type { components } from "../../api/schema";
import Button from "../../components/ui/Button.vue";
import Dialog from "../../components/ui/Dialog.vue";
import FormatChip from "../../components/ui/FormatChip.vue";
import Icon from "../../components/ui/Icon.vue";
import Stamp from "../../components/ui/Stamp.vue";
import StatusChip, { STATUS_LOOK } from "../../components/ui/StatusChip.vue";
import TextArea from "../../components/ui/TextArea.vue";
import { useToast } from "../../components/ui/useToast";
import { useSessionStore } from "../../stores/session";
import { NOTE_MAX, NOTE_MIN } from "../review/checks";
import {
  ACTION_LOOK,
  type DocumentAction,
  headerActions,
  problemMessage,
  successMessage,
} from "./actions";
import { formatDate, formatMoney, isCreditNote } from "./format";
import ValidationChip from "./ValidationChip.vue";
import { validationLook } from "./validation";

type DocumentDetail = components["schemas"]["DocumentDetail"];

const props = withDefaults(
  defineProps<{
    document: DocumentDetail;
    /** Phone layout: 44 px buttons. */
    phone?: boolean;
  }>(),
  { phone: false },
);

const emit = defineEmits<{
  /** An action succeeded; the API's updated detail. */
  changed: [detail: DocumentDetail];
  deleted: [];
}>();

const toast = useToast();
const session = useSessionStore();

const doc = computed(() => props.document);
const number = computed(
  () => doc.value.invoice_number ?? doc.value.original_filename,
);
const supplier = computed(
  () => doc.value.supplier_name ?? doc.value.original_filename,
);
const credit = computed(() =>
  isCreditNote(doc.value.type_code ?? doc.value.invoice?.type_code),
);
const gross = computed(() =>
  formatMoney(doc.value.gross_total, doc.value.currency ?? "EUR", credit.value),
);
const validation = computed(() => validationLook(doc.value));
const actions = computed(() => headerActions(doc.value.allowed_actions));
const buttonSize = computed(() => (props.phone ? "lg" : "md"));

/** Each distinct reason once, as visible text under the buttons. */
const reasons = computed(() => [
  ...new Set(
    actions.value
      .filter((action) => !action.enabled && action.reason)
      .map((action) => action.reason as string),
  ),
]);

const decision = computed(() => {
  const status = doc.value.status;
  if (status !== "approved" && status !== "rejected") return null;
  const latest = [...doc.value.approvals]
    .sort((a, b) => Date.parse(b.decided_at) - Date.parse(a.decided_at))
    .at(0);
  if (!latest) return null;
  const who =
    latest.decided_by_name === session.me?.user.name
      ? "You"
      : latest.decided_by_name;
  const verb = latest.decision === "approved" ? "approved" : "rejected";
  return {
    tone: latest.decision === "approved" ? "ok" : "block",
    icon: latest.decision === "approved" ? "circle-check" : "ban",
    text: `${who} ${verb} this on ${formatDate(latest.decided_at.slice(0, 10))}.`,
  } as const;
});

// Announced politely whenever the status changes (HANDOFF accessibility).
const statusAnnouncement = computed(
  () => `Status: ${STATUS_LOOK[doc.value.status].label}.`,
);
const processing = computed(() => {
  const status = doc.value.status;
  if (status !== "received" && status !== "processing") return null;
  return doc.value.processing_step
    ? `Processing: ${doc.value.processing_step}…`
    : "Waiting to be processed…";
});

// ---------------------------------------------------------------------------
// Running actions

const busy = ref<DocumentAction | null>(null);

type DialogAction = "reject" | "send_back" | "delete";
const dialogAction = ref<DialogAction | null>(null);
const dialogOpen = computed({
  get: () => dialogAction.value !== null,
  set: (value: boolean) => {
    if (!value && busy.value === null) dialogAction.value = null;
  },
});
const note = ref("");
const tried = ref(false);
const serverError = ref<string | null>(null);

const NOTE_ERROR = "Write at least 5 characters.";

const noteError = computed(() => {
  if (serverError.value) return serverError.value;
  if (!tried.value) return undefined;
  const length = note.value.trim().length;
  if (length < NOTE_MIN) return NOTE_ERROR;
  if (length > NOTE_MAX) return `Write at most ${NOTE_MAX} characters.`;
  return undefined;
});

const dialog = computed(() => {
  switch (dialogAction.value) {
    case "reject":
      return {
        title: `Reject invoice ${number.value}?`,
        description: `${supplier.value}, ${gross.value}. The reason is saved in the invoice’s activity.`,
        label: "Reason",
        placeholder: "What should the supplier correct?",
        cta: "Reject invoice",
        variant: "danger" as const,
        note: true,
      };
    case "send_back":
      return {
        title: `Send ${number.value} back to review?`,
        description:
          "It goes back to Needs review. Say what needs another look.",
        label: "Note",
        placeholder: "What needs another look?",
        cta: "Send back",
        variant: "primary" as const,
        note: true,
      };
    case "delete":
      return {
        title: `Delete ${number.value}?`,
        description: `${supplier.value}, ${gross.value}. It leaves the inbox and every list; its activity stays on record.`,
        label: "",
        placeholder: "",
        cta: "Delete invoice",
        variant: "danger" as const,
        note: false,
      };
    default:
      return null;
  }
});

async function request(
  action: DocumentAction,
  comment: string,
): Promise<DocumentDetail | null> {
  const path = { params: { path: { document_id: doc.value.id } } };
  switch (action) {
    case "mark_reviewed":
      return unwrap(
        await api.POST("/api/v1/documents/{document_id}/mark-reviewed", path),
      );
    case "approve":
    case "reject":
      return unwrap(
        await api.POST("/api/v1/documents/{document_id}/decision", {
          ...path,
          body: {
            decision: action === "approve" ? "approved" : "rejected",
            comment,
          },
        }),
      );
    case "send_back":
      return unwrap(
        await api.POST("/api/v1/documents/{document_id}/send-back", {
          ...path,
          body: { comment },
        }),
      );
    case "reopen":
      return unwrap(
        await api.POST("/api/v1/documents/{document_id}/reopen", path),
      );
    case "retry":
      return unwrap(
        await api.POST("/api/v1/documents/{document_id}/retry", path),
      );
    case "delete":
      unwrap(await api.DELETE("/api/v1/documents/{document_id}", path));
      return null;
  }
}

async function run(action: DocumentAction, comment = ""): Promise<void> {
  if (busy.value) return;
  busy.value = action;
  const shownNumber = number.value;
  try {
    const detail = await request(action, comment);
    busy.value = null;
    dialogAction.value = null;
    toast.show({
      kind: "success",
      message: successMessage(action, shownNumber),
    });
    if (detail) emit("changed", detail);
    else emit("deleted");
  } catch (error) {
    busy.value = null;
    const fieldError =
      error instanceof ApiError && error.status === 422
        ? error.errors.find((entry) => entry.path.includes("comment"))?.message
        : undefined;
    if (fieldError && dialogAction.value) {
      serverError.value = fieldError;
      return;
    }
    toast.show({ kind: "error", message: problemMessage(error) });
  }
}

function start(action: DocumentAction): void {
  if (ACTION_LOOK[action].dialog) {
    note.value = "";
    tried.value = false;
    serverError.value = null;
    dialogAction.value = action as DialogAction;
    return;
  }
  void run(action);
}

function confirm(): void {
  const action = dialogAction.value;
  if (!action) return;
  if (action === "delete") {
    void run("delete");
    return;
  }
  tried.value = true;
  serverError.value = null;
  if (noteError.value) return;
  void run(action, note.value.trim());
}

watch(note, () => {
  serverError.value = null;
});
</script>

<template>
  <header class="head">
    <div class="head-row">
      <RouterLink class="back" :to="{ name: 'inbox' }"
        ><Icon name="chevron-left" />Inbox</RouterLink
      >
      <span class="keys"
        ><kbd>j</kbd><kbd>k</kbd
        ><span class="keys-text">next / previous invoice</span></span
      >
    </div>

    <div class="head-row head-row--top">
      <h1 class="title">{{ supplier }}</h1>
      <StatusChip class="status" :status="doc.status" />
    </div>

    <div class="meta">
      <span v-if="doc.invoice_number" class="number">{{
        doc.invoice_number
      }}</span>
      <Stamp size="chip" :date="doc.received_at" />
      <FormatChip v-if="doc.format_label" :label="doc.format_label" />
      <ValidationChip v-if="validation" :look="validation" />
    </div>

    <div class="head-row head-row--bottom">
      <div class="amount">
        <span class="gross">{{ gross }}</span>
        <span v-if="doc.due_date" class="due"
          >Due {{ formatDate(doc.due_date) }}</span
        >
      </div>

      <div v-if="actions.length > 0 || decision" class="actions-wrap">
        <div v-if="actions.length > 0" class="actions">
          <Button
            v-for="action in actions"
            :key="action.action"
            :variant="ACTION_LOOK[action.action].variant"
            :size="buttonSize"
            :icon="ACTION_LOOK[action.action].icon"
            :loading="busy === action.action"
            :disabled="busy !== null && busy !== action.action"
            :disabled-reason="
              action.enabled ? undefined : (action.reason ?? 'Not available.')
            "
            @click="start(action.action)"
            >{{
              busy === action.action
                ? ACTION_LOOK[action.action].busyLabel
                : ACTION_LOOK[action.action].label
            }}</Button
          >
        </div>
        <p v-for="reason in reasons" :key="reason" class="reason">
          <Icon name="lock" :size="14" />{{ reason }}
        </p>
        <p
          v-if="decision"
          class="decision"
          :class="`decision--${decision.tone}`"
          role="status"
        >
          <Icon :name="decision.icon" />{{ decision.text }}
        </p>
      </div>
    </div>

    <p class="sr-only" aria-live="polite">{{ statusAnnouncement }}</p>
    <p v-if="processing" class="processing">
      <Icon name="loader" spin />{{ processing }}
    </p>
    <p v-if="doc.status === 'failed'" class="failed" role="status">
      <Icon name="circle-alert" />{{
        doc.failure_reason ?? "Processing failed."
      }}
    </p>

    <Dialog
      v-model:open="dialogOpen"
      :title="dialog?.title ?? ''"
      :description="dialog?.description"
      size="md"
    >
      <TextArea
        v-if="dialog?.note"
        v-model="note"
        :label="dialog.label"
        :placeholder="dialog.placeholder"
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
          :variant="dialog?.variant ?? 'primary'"
          :loading="busy !== null"
          @click="confirm"
          >{{
            busy !== null ? ACTION_LOOK[busy].busyLabel : dialog?.cta
          }}</Button
        >
      </template>
    </Dialog>
  </header>
</template>

<style scoped>
.head {
  display: grid;
  gap: var(--space-12);
  padding: var(--space-16) var(--space-20);
  border-bottom: 1px solid var(--line);
  background: var(--bar);
}

.head-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-12);
}

.head-row--top {
  align-items: flex-start;
}

.head-row--bottom {
  flex-wrap: wrap;
  align-items: flex-end;
}

.back {
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
}

.keys {
  display: inline-flex;
  align-items: center;
  gap: var(--space-4);
  font-size: var(--fs-12);
  color: var(--muted);
}

kbd {
  display: inline-grid;
  place-items: center;
  min-width: var(--size-badge);
  height: var(--size-badge);
  border: 1px solid var(--line-strong);
  border-radius: var(--r-sm);
  background: var(--win);
  font-size: var(--fs-12);
  line-height: 1;
  color: var(--ink);
}

.keys-text {
  padding-left: var(--space-4);
}

.title {
  font-family: var(--font-head);
  font-size: var(--fs-21);
  font-weight: 700;
  letter-spacing: var(--tracking-head);
  line-height: var(--lh-tight);
  color: var(--ink);
  overflow-wrap: anywhere;
}

.status {
  flex: none;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-8) var(--space-12);
  font-size: var(--fs-13);
}

.number {
  font-family: var(--font-mono);
  color: var(--muted);
}

.amount {
  display: grid;
  gap: var(--space-4);
}

.gross {
  font-family: var(--font-mono);
  font-size: var(--fs-21);
  font-weight: 500;
  line-height: var(--lh-tight);
  color: var(--ink);
}

.due {
  font-size: var(--fs-13);
}

.actions-wrap {
  display: grid;
  justify-items: end;
  gap: var(--space-4);
}

.actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: var(--space-8);
}

.reason {
  display: inline-flex;
  align-items: center;
  gap: var(--space-4);
  font-size: var(--fs-12);
  color: var(--muted);
}

.decision,
.processing,
.failed {
  display: inline-flex;
  align-items: center;
  gap: var(--space-8);
  font-size: var(--fs-13);
}

.decision--ok {
  color: var(--ok);
}

.decision--block,
.failed {
  color: var(--block);
}

.processing {
  color: var(--info);
}

@media (max-width: 767px) {
  .head {
    padding: var(--space-12) var(--space-16);
  }

  .keys {
    display: none;
  }

  .back {
    min-height: var(--size-lg);
  }

  .actions-wrap {
    justify-items: stretch;
    width: 100%;
  }

  .actions {
    justify-content: stretch;
  }

  .actions > * {
    flex: 1 1 auto;
  }
}
</style>
