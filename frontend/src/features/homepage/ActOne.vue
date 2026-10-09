<script setup lang="ts">
// Homepage Act 1 (design "Every format lands in one inbox"): four sample documents; drag one
// onto the stamp, or press its "Stamp it" button. Each lands in the sample inbox as a row
// that goes Received → Processing → its verdict. Sample data only; nothing is sent anywhere.
import { computed, ref } from "vue";

import Button from "../../components/ui/Button.vue";
import Icon from "../../components/ui/Icon.vue";
import type { IconName } from "../../components/ui/icons";
import Stamp from "../../components/ui/Stamp.vue";
import { prefersReducedMotion, useTimers } from "./motion";

type Kind = "valid" | "ai" | "bwl" | "invalid";
type Phase = "received" | "processing" | "done";

interface SampleDocument {
  id: string;
  supplier: string;
  number: string;
  format: string;
  icon: IconName;
  kind: Kind;
  caption: string;
}

const DOCUMENTS: SampleDocument[] = [
  {
    id: "xr",
    supplier: "Elektro Kessler GmbH",
    number: "RE-2026-0412",
    format: "XRechnung · UBL",
    icon: "file-code",
    kind: "valid",
    caption: "RE-2026-0412.xml",
  },
  {
    id: "pdf",
    supplier: "Druckerei Sommer GmbH",
    number: "2026-1043",
    format: "Plain PDF",
    icon: "file-text",
    kind: "ai",
    caption: "Rechnung 2026-1043",
  },
  {
    id: "bwl",
    supplier: "Atelier Moreau SARL",
    number: "F-2026-118",
    format: "ZUGFeRD · BASIC WL",
    icon: "paperclip",
    kind: "bwl",
    caption: "PDF/A-3 with factur-x.xml",
  },
  {
    id: "inv",
    supplier: "Elektro Kessler GmbH",
    number: "RE-2026-0413",
    format: "XRechnung · UBL",
    icon: "file-code",
    kind: "invalid",
    caption: "RE-2026-0413.xml",
  },
];

// The 15 Oct 2024 BMF letter (MINIMUM and BASIC WL are not e-invoices), through the
// summary HANDOFF names as its source.
const BMF_SOURCE =
  "https://www.elo.com/de-de/blog/e-rechnungspflicht-bmf-schreiben-und-faq.html";

interface Row {
  id: string;
  time: string;
  phase: Phase;
  entering: boolean;
}

const rows = ref<Row[]>([]);
const pressing = ref(false);
const over = ref(false);
const { later, clear } = useTimers();

const stamped = (id: string) => rows.value.some((row) => row.id === id);
const documentOf = (id: string) => DOCUMENTS.find((item) => item.id === id);
const finished = computed(
  () =>
    rows.value.length === DOCUMENTS.length &&
    rows.value.every((row) => row.phase === "done"),
);
const announcement = computed(() => {
  if (finished.value) return "4 invoices stamped. 1 is a valid e-invoice.";
  const last = rows.value[0];
  if (!last) return "";
  const doc = documentOf(last.id);
  return last.phase === "done" && doc
    ? `${doc.number}: ${verdictText(doc.kind)}`
    : "";
});

function setRow(id: string, patch: Partial<Row>): void {
  rows.value = rows.value.map((row) =>
    row.id === id ? { ...row, ...patch } : row,
  );
}

function stamp(id: string): void {
  if (!documentOf(id) || stamped(id)) return;
  const reduced = prefersReducedMotion();
  const time = `09 Oct, 10:4${1 + rows.value.length}`;
  rows.value = [
    { id, time, phase: reduced ? "done" : "received", entering: !reduced },
    ...rows.value,
  ];
  over.value = false;
  if (reduced) return;
  pressing.value = true;
  later(() => (pressing.value = false), 300);
  requestAnimationFrame(() =>
    requestAnimationFrame(() => setRow(id, { entering: false })),
  );
  later(() => setRow(id, { phase: "processing" }), 400);
  later(() => setRow(id, { phase: "done" }), 1100);
}

function reset(): void {
  clear();
  rows.value = [];
  pressing.value = false;
}

function onDragStart(event: DragEvent, id: string): void {
  event.dataTransfer?.setData("text/plain", id);
  if (event.dataTransfer) event.dataTransfer.effectAllowed = "copy";
}

function onDrop(event: DragEvent): void {
  event.preventDefault();
  over.value = false;
  const id = event.dataTransfer?.getData("text/plain");
  if (id) stamp(id);
}

function verdictText(kind: Kind): string {
  switch (kind) {
    case "valid":
      return "Valid e-invoice";
    case "ai":
      return "Not an e-invoice · AI-read, 1 field to check";
    case "bwl":
      return "Not an e-invoice (profile BASIC WL)";
    default:
      return "Invalid · BR-DE-15";
  }
}
</script>

<template>
  <div class="act">
    <div class="pile">
      <ul class="docs" aria-label="Sample documents">
        <li
          v-for="doc in DOCUMENTS"
          :key="doc.id"
          class="doc"
          :class="{ 'doc--stamped': stamped(doc.id) }"
          :draggable="!stamped(doc.id)"
          @dragstart="onDragStart($event, doc.id)"
        >
          <Icon :name="doc.icon" :size="20" class="doc__icon" />
          <span class="doc__text">
            <span class="doc__supplier">{{ doc.supplier }}</span>
            <span class="doc__caption">{{ doc.caption }}</span>
          </span>
          <Button size="sm" :disabled="stamped(doc.id)" @click="stamp(doc.id)">
            {{ stamped(doc.id) ? "Stamped" : "Stamp it"
            }}<span class="visually-hidden">: {{ doc.number }}</span>
          </Button>
        </li>
      </ul>
      <p class="hint">
        Sample documents. Drag one onto the stamp, or press Stamp it.
      </p>
    </div>

    <div class="window" aria-label="Sample inbox" role="region">
      <div class="window__bar">
        <Stamp size="mark" :mark-size="24" />
        <span class="window__brand">Eingang</span>
        <span aria-hidden="true">/</span>
        <span>Holzwerk Brandt GmbH</span>
        <span class="badge">Sample data</span>
      </div>
      <div class="window__head">
        <span class="window__title">Inbox</span>
        <span class="count">{{ rows.length }}</span>
      </div>
      <div
        class="dropzone"
        :class="{ 'dropzone--over': over, 'dropzone--pressing': pressing }"
        @dragover.prevent="over = true"
        @dragleave="over = false"
        @drop="onDrop"
      >
        <Stamp
          size="md"
          date="2026-10-09"
          :rotate="-6"
          class="dropzone__stamp"
        />
        <span class="dropzone__text">Drop a document on the stamp</span>
      </div>
      <table class="rows">
        <caption class="visually-hidden">
          Stamped sample invoices
        </caption>
        <thead>
          <tr>
            <th scope="col">Received</th>
            <th scope="col">Supplier</th>
            <th scope="col">Format</th>
            <th scope="col">Verdict</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="rows.length === 0">
            <td colspan="4" class="rows__empty">Nothing stamped yet.</td>
          </tr>
          <tr
            v-for="row in rows"
            :key="row.id"
            class="row"
            :class="{ 'row--entering': row.entering }"
          >
            <td class="mono">{{ row.time }}</td>
            <td>
              <span class="row__supplier">{{
                documentOf(row.id)?.supplier
              }}</span>
              <span class="row__number mono">{{
                documentOf(row.id)?.number
              }}</span>
            </td>
            <td>{{ documentOf(row.id)?.format }}</td>
            <td>
              <span
                v-if="row.phase === 'received'"
                class="verdict verdict--muted"
              >
                <Icon name="inbox" :size="14" />Received
              </span>
              <span
                v-else-if="row.phase === 'processing'"
                class="verdict verdict--muted"
              >
                <Icon name="loader" :size="14" spin />Processing
              </span>
              <template v-else>
                <span
                  class="verdict"
                  :class="`verdict--${documentOf(row.id)?.kind}`"
                >
                  <Icon
                    :name="
                      documentOf(row.id)?.kind === 'valid'
                        ? 'circle-check'
                        : documentOf(row.id)?.kind === 'invalid'
                          ? 'octagon'
                          : 'info'
                    "
                    :size="14"
                  />{{ verdictText(documentOf(row.id)?.kind ?? "valid") }}
                </span>
                <p
                  v-if="documentOf(row.id)?.kind === 'invalid'"
                  class="verdict__note"
                >
                  XRechnung invoices must name the buyer's reference — for
                  public bodies this is the Leitweg-ID. Ask the supplier to
                  resend the invoice with your reference.
                </p>
                <p
                  v-if="documentOf(row.id)?.kind === 'bwl'"
                  class="verdict__note"
                >
                  BASIC WL carries too little data to count as an e-invoice.
                  <a :href="BMF_SOURCE" rel="noopener" target="_blank"
                    >Source: ELO summary of the BMF letter, 15 Oct 2024</a
                  >
                </p>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="finished" class="done">
        <span>4 invoices stamped. 1 is a valid e-invoice.</span>
        <Button size="sm" variant="ghost" @click="reset">
          <Icon name="refresh" :size="14" />Do it again
        </Button>
      </div>
      <p class="visually-hidden" aria-live="polite">{{ announcement }}</p>
    </div>
  </div>
</template>

<style scoped>
.act {
  display: grid;
  grid-template-columns: minmax(0, 5fr) minmax(0, 7fr);
  gap: var(--space-40);
  align-items: start;
}

.docs {
  display: grid;
  gap: var(--space-12);
  margin: 0;
  padding: 0;
  list-style: none;
}

.doc {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: var(--space-12);
  align-items: center;
  padding: var(--space-12) var(--space-16);
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  background: var(--paper);
  box-shadow: var(--shadow-sheet);
  cursor: grab;
  transition: transform var(--dur-switch) var(--ease-out);
}

.doc:hover:not(.doc--stamped) {
  transform: translateY(-4px);
}

.doc--stamped {
  cursor: default;
  opacity: 0.6;
}

.doc__icon {
  color: var(--muted);
}

.doc__text {
  display: grid;
  min-width: 0;
}

.doc__supplier {
  font-weight: 600;
}

.doc__caption {
  color: var(--muted);
  font-size: var(--fs-13);
  overflow-wrap: anywhere;
}

.hint {
  margin: var(--space-12) 0 0;
  color: var(--muted);
  font-size: var(--fs-13);
}

.window {
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: var(--r-lg);
  background: var(--win);
  box-shadow: var(--shadow-window);
}

.window__bar {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-8);
  align-items: center;
  padding: var(--space-8) var(--space-16);
  border-bottom: 1px solid var(--line);
  background: var(--bar);
  font-size: var(--fs-13);
}

.window__brand {
  font-family: var(--font-head);
  font-weight: 700;
}

.badge {
  margin-left: auto;
  padding: 0 var(--space-8);
  border-radius: var(--r-pill);
  background: var(--stamp-soft);
  color: var(--stamp);
  font-size: var(--fs-12);
}

.window__head {
  display: flex;
  gap: var(--space-8);
  align-items: center;
  padding: var(--space-16) var(--space-16) 0;
}

.window__title {
  font-family: var(--font-head);
  font-size: var(--fs-16);
  font-weight: 700;
}

.count {
  padding: 0 var(--space-8);
  border-radius: var(--r-pill);
  background: var(--ink);
  color: var(--win);
  font-size: var(--fs-12);
}

.dropzone {
  display: grid;
  justify-items: center;
  gap: var(--space-8);
  margin: var(--space-16);
  padding: var(--space-20);
  border: 2px dashed var(--line);
  border-radius: var(--r-md);
  transition: background var(--dur-fast) var(--ease-out);
}

.dropzone--over {
  border-color: var(--stamp);
  background: var(--stamp-soft);
}

.dropzone__stamp {
  transition: transform 140ms ease-out;
}

.dropzone--pressing .dropzone__stamp {
  transform: translateY(3px) scale(0.96);
}

.dropzone__text {
  color: var(--muted);
  font-size: var(--fs-13);
}

.rows {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--fs-13);
}

.rows th,
.rows td {
  padding: var(--space-8) var(--space-16);
  border-top: 1px solid var(--line);
  text-align: left;
  vertical-align: top;
}

.rows th {
  color: var(--muted);
  font-weight: 500;
}

.rows__empty {
  color: var(--muted);
}

.row {
  transition:
    opacity 240ms ease-out,
    transform 240ms ease-out;
}

.row--entering {
  opacity: 0;
  transform: translateY(-8px);
}

.row__supplier {
  display: block;
  font-weight: 500;
}

.row__number {
  color: var(--muted);
}

.mono {
  font-family: var(--font-mono);
}

.verdict {
  display: inline-flex;
  gap: var(--space-4);
  align-items: center;
  font-weight: 500;
}

.verdict--muted {
  color: var(--muted);
}

.verdict--valid {
  color: var(--ok);
}

.verdict--invalid {
  color: var(--block);
}

.verdict--ai,
.verdict--bwl {
  color: var(--warn-text);
}

.verdict__note {
  margin: var(--space-4) 0 0;
  color: var(--text);
}

.done {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-12);
  align-items: center;
  justify-content: space-between;
  padding: var(--space-12) var(--space-16);
  border-top: 1px solid var(--line);
  font-weight: 500;
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}

@media (max-width: 1099px) {
  .act {
    grid-template-columns: 1fr;
    gap: var(--space-24);
  }

  .doc :deep(button) {
    min-height: 44px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .doc,
  .row,
  .dropzone,
  .dropzone__stamp {
    transition: none;
  }
}
</style>
