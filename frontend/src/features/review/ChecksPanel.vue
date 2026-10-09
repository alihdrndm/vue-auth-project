<script setup lang="ts">
// The Checks section of the review screen (HANDOFF "Business checks", design "CheckCard"):
// open checks first, worst first; a block or warn check is resolved with a note of 5–500
// characters; whether this user may resolve it, and why not, comes from the API.
import { computed, ref } from "vue";

import { api, ApiError, unwrap } from "../../api/client";
import type { components } from "../../api/schema";
import Button from "../../components/ui/Button.vue";
import Dialog from "../../components/ui/Dialog.vue";
import Icon from "../../components/ui/Icon.vue";
import SeverityChip from "../../components/ui/SeverityChip.vue";
import TextArea from "../../components/ui/TextArea.vue";
import { useToast } from "../../components/ui/useToast";
import {
  type Check,
  isOpen,
  NOTE_MAX,
  noteError,
  resolveLabel,
  resolveState,
  sortChecks,
} from "./checks";

const props = defineProps<{
  document: components["schemas"]["DocumentDetail"];
}>();
const emit = defineEmits<{ resolved: [] }>();

const { show } = useToast();
const checks = computed(() => sortChecks(props.document.checks as Check[]));

const active = ref<Check | null>(null);
const dialogOpen = ref(false);
const note = ref("");
const tried = ref(false);
const busy = ref(false);
const serverError = ref<string | null>(null);

const isAccept = computed(() => active.value?.check_id === "C15");
const dialogTitle = computed(() => {
  if (!active.value) return "";
  if (isAccept.value)
    return `Accept ${props.document.invoice_number ?? "this invoice"} anyway?`;
  return `Resolve check: ${active.value.message}`;
});
const dialogBody = computed(() =>
  isAccept.value
    ? "Accepting keeps the error on record, saves your note and lets the invoice go to approval."
    : "Say how you checked this. The note is saved with the invoice and shown to the approver.",
);
const error = computed(() => (tried.value ? noteError(note.value) : null));

function open(check: Check): void {
  active.value = check;
  note.value = "";
  tried.value = false;
  serverError.value = null;
  dialogOpen.value = true;
}

async function confirm(): Promise<void> {
  tried.value = true;
  const check = active.value;
  if (!check || noteError(note.value)) return;
  busy.value = true;
  serverError.value = null;
  try {
    unwrap(
      await api.POST("/api/v1/checks/{check_id}/resolve", {
        params: { path: { check_id: check.id } },
        body: { note: note.value.trim() },
      }),
    );
    dialogOpen.value = false;
    show({ kind: "success", message: "Check resolved." });
    emit("resolved");
  } catch (caught) {
    serverError.value =
      caught instanceof ApiError
        ? `${caught.title}. ${caught.detail}`
        : "The check could not be resolved. Try again.";
  } finally {
    busy.value = false;
  }
}

function resolvedText(check: Check): string {
  const how = check.check_id === "C15" ? "Accepted anyway by" : "Resolved by";
  return `${how} ${check.resolved_by_name ?? "someone"}`;
}

interface Difference {
  field: string;
  xml: string;
  pdf: string;
}

function detail(check: Check, key: string): string | null {
  const value = (check.details as Record<string, unknown>)[key];
  return typeof value === "string" && value !== "" ? value : null;
}

/** C02 and C03 name the earlier invoice (HANDOFF section 8: the message links it). */
function earlierInvoice(check: Check): string | null {
  return detail(check, "document_id");
}

/** C11 links the source of the mandate dates. */
function sourceUrl(check: Check): string | null {
  const url = detail(check, "source_url");
  return url && /^https:\/\//.test(url) ? url : null;
}

function sourceLabel(url: string): string {
  return url.includes("ec.europa.eu")
    ? "Source: European Commission"
    : "Source";
}

/** The message without a URL that is shown as a link instead. */
function messageText(check: Check): string {
  const url = sourceUrl(check);
  return url
    ? check.message.replace(` (${url})`, "").replace(url, "").trim()
    : check.message;
}

function differences(check: Check): Difference[] {
  const list = (check.details as { differences?: unknown }).differences;
  return Array.isArray(list) ? (list as Difference[]) : [];
}
</script>

<template>
  <section class="checks" aria-labelledby="checks-title">
    <h2 id="checks-title" class="checks__title">Checks</h2>
    <p v-if="checks.length === 0" class="checks__empty">
      No checks found anything.
    </p>
    <ul v-else class="checks__list">
      <li
        v-for="check in checks"
        :key="check.id"
        class="card"
        :class="[
          `card--${check.severity}`,
          { 'card--resolved': !isOpen(check) },
        ]"
      >
        <div class="card__head">
          <SeverityChip :severity="check.severity" />
          <span class="card__id">{{ check.check_id }}</span>
        </div>
        <p class="card__message">
          {{ messageText(check) }}
          <RouterLink
            v-if="earlierInvoice(check)"
            :to="{ name: 'invoice', params: { id: earlierInvoice(check) } }"
            >Open the earlier invoice</RouterLink
          >
          <a
            v-if="sourceUrl(check)"
            :href="sourceUrl(check) ?? undefined"
            rel="noopener"
            >{{ sourceLabel(sourceUrl(check) ?? "") }}</a
          >
        </p>
        <table v-if="differences(check).length" class="diff">
          <caption class="visually-hidden">
            Differences between the PDF and the XML
          </caption>
          <thead>
            <tr>
              <th scope="col">Field</th>
              <th scope="col">Visible PDF</th>
              <th scope="col">XML</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in differences(check)" :key="row.field">
              <th scope="row">{{ row.field.replace(/_/g, " ") }}</th>
              <td class="mono">{{ row.pdf }}</td>
              <td class="mono">{{ row.xml }}</td>
            </tr>
          </tbody>
        </table>
        <div v-if="!isOpen(check)" class="card__resolved">
          <span>{{ resolvedText(check) }}</span>
          <q v-if="check.resolution_note">{{ check.resolution_note }}</q>
        </div>
        <div v-else-if="resolveState(check).showButton" class="card__actions">
          <Button
            :disabled="!resolveState(check).canResolve"
            :disabled-reason="resolveState(check).reason ?? undefined"
            @click="open(check)"
          >
            {{ resolveLabel(check) }}
          </Button>
          <span v-if="resolveState(check).reason" class="card__why">{{
            resolveState(check).reason
          }}</span>
        </div>
      </li>
    </ul>

    <Dialog
      v-model:open="dialogOpen"
      :title="dialogTitle"
      :description="dialogBody"
      size="md"
    >
      <TextArea
        v-model="note"
        label="Note"
        placeholder="How did you check this?"
        :maxlength="NOTE_MAX"
        counter
        hint="5 to 500 characters."
        :error="error ?? undefined"
      />
      <p v-if="serverError" class="dialog__error" role="alert">
        <Icon name="octagon" :size="14" />{{ serverError }}
      </p>
      <template #footer>
        <Button variant="ghost" @click="dialogOpen = false">Cancel</Button>
        <Button variant="primary" :loading="busy" @click="confirm">
          {{ isAccept ? "Accept anyway" : "Resolve check" }}
        </Button>
      </template>
    </Dialog>
  </section>
</template>

<style scoped>
.checks {
  min-width: 0;
  padding: var(--space-20);
  border-bottom: 1px solid var(--line);
}

@media (max-width: 767px) {
  .checks {
    padding: var(--space-16);
  }
}

.checks__title {
  margin: 0 0 var(--space-12);
  font-family: var(--font-head);
  font-size: var(--fs-16);
  font-weight: 700;
  letter-spacing: var(--tracking-head);
  color: var(--ink);
}

.checks__empty {
  color: var(--muted);
}

.checks__list {
  display: grid;
  gap: var(--space-12);
  margin: 0;
  padding: 0;
  list-style: none;
}

.card {
  padding: var(--space-12) var(--space-16);
  border: 1px solid var(--line);
  border-left-width: 4px;
  border-radius: var(--r-md);
  background: var(--win);
}

.card--block {
  border-left-color: var(--block);
}

.card--warn {
  border-left-color: var(--warn);
}

.card--info {
  border-left-color: var(--line);
}

.card--resolved {
  border-left-color: var(--ok);
}

.card__head {
  display: flex;
  gap: var(--space-8);
  align-items: center;
}

.card__id {
  color: var(--muted);
  font-family: var(--font-mono);
  font-size: var(--fs-12);
}

.card__message {
  margin: var(--space-8) 0 0;
  overflow-wrap: anywhere; /* messages can carry long source URLs */
}

.card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-8);
  align-items: center;
  margin-top: var(--space-12);
}

.card__why {
  color: var(--muted);
  font-size: var(--fs-13);
}

.card__message a {
  margin-left: var(--space-4);
}

.card__resolved {
  display: grid;
  gap: var(--space-4);
  margin-top: var(--space-8);
  color: var(--muted);
  font-size: var(--fs-13);
}

.diff {
  width: 100%;
  margin-top: var(--space-8);
  border-collapse: collapse;
  font-size: var(--fs-13);
}

.diff th,
.diff td {
  padding: var(--space-4) var(--space-8);
  border-bottom: 1px solid var(--line);
  text-align: left;
}

.mono {
  font-family: var(--font-mono);
}

.dialog__error {
  display: flex;
  gap: var(--space-8);
  align-items: center;
  color: var(--block);
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}
</style>
