<script setup lang="ts">
// Homepage Act 2 (design "Someone still has to say yes."): Anna resolves the bank-account
// check with a note and marks the invoice reviewed; Jonas approves it on his phone; the
// export drops into the folder for the tax advisor. A demo with sample data: nothing is sent.
import { computed, nextTick, ref } from "vue";

import Button from "../../components/ui/Button.vue";
import Icon from "../../components/ui/Icon.vue";
import { prefersReducedMotion, useTimers } from "./motion";

// Design-only example; never seed data (design "Do not change", 6).
const EXAMPLE_NOTE = "Called Bürobedarf Nord on their old number — confirmed";
const APPROVE_MS = 700;
const EXPORT_AFTER_MS = 500;

const note = ref("");
const noteError = ref(false);
const resolved = ref(false);
const reviewed = ref(false);
const approving = ref(false);
const approved = ref(false);
const exported = ref(false);
const rejectHint = ref(false);
const { later, clear } = useTimers();
const root = ref<HTMLElement | null>(null);

/** Keyboard focus follows the demo to its next step instead of falling to the page top. */
async function focusNext(selector: string): Promise<void> {
  await nextTick();
  root.value?.querySelector<HTMLElement>(selector)?.focus();
}

const quote = computed(() => note.value.trim());
const status = computed(() => {
  if (exported.value) return { key: "exported", label: "Exported" };
  if (approved.value) return { key: "approved", label: "Approved" };
  if (reviewed.value) return { key: "awaiting", label: "Awaiting approval" };
  return { key: "needs", label: "Needs review" };
});

const steps = computed(() => {
  const done = [resolved.value, reviewed.value, approved.value, exported.value];
  const current = done.indexOf(false);
  return [
    "Resolve the check",
    "Mark reviewed",
    "Approve on Jonas’s phone",
    "Export for the tax advisor",
  ].map((label, index) => ({
    label,
    n: index + 1,
    done: done[index] ?? false,
    current: index === current,
  }));
});

function useExample(): void {
  note.value = EXAMPLE_NOTE;
  noteError.value = false;
}

function resolve(): void {
  if (!quote.value) {
    noteError.value = true;
    return;
  }
  resolved.value = true;
  void focusNext(".review button");
}

function markReviewed(): void {
  if (!resolved.value || reviewed.value) return;
  reviewed.value = true;
  void focusNext(".card__actions .button--primary");
}

function approve(): void {
  if (!reviewed.value || approving.value || approved.value) return;
  rejectHint.value = false;
  const reduced = prefersReducedMotion();
  if (reduced) {
    approved.value = true;
    exported.value = true;
    void focusNext(".review__end button");
    return;
  }
  approving.value = true;
  later(() => {
    approving.value = false;
    approved.value = true;
    void focusNext(".review__end button");
    later(() => (exported.value = true), EXPORT_AFTER_MS);
  }, APPROVE_MS);
}

function reset(): void {
  clear();
  note.value = "";
  noteError.value = false;
  resolved.value = false;
  reviewed.value = false;
  approving.value = false;
  approved.value = false;
  exported.value = false;
  rejectHint.value = false;
}
</script>

<template>
  <div ref="root" class="act">
    <ol class="steps" aria-label="Steps">
      <li
        v-for="step in steps"
        :key="step.n"
        class="step"
        :class="{ 'step--done': step.done, 'step--current': step.current }"
        :aria-current="step.current ? 'step' : undefined"
      >
        <Icon :name="step.done ? 'circle-check' : 'circle'" :size="16" />
        <span>{{ step.n }}. {{ step.label }}</span>
        <span v-if="step.done" class="visually-hidden">(done)</span>
      </li>
    </ol>

    <div class="stage">
      <section class="window" aria-label="Sample review screen">
        <div class="window__bar">
          <span class="window__brand">Eingang</span>
          <span aria-hidden="true">/</span>
          <span>Holzwerk Brandt GmbH</span>
          <span class="badge">Sample data</span>
          <span class="user"
            ><span class="avatar" aria-hidden="true">AW</span>Anna Weber ·
            Accountant</span
          >
        </div>
        <div class="invoice">
          <div class="invoice__head">
            <div>
              <h3 class="invoice__supplier">Bürobedarf Nord KG</h3>
              <span class="mono">BN-88290</span>
            </div>
            <span
              class="chip"
              :class="`chip--${status.key}`"
              aria-live="polite"
              >{{ status.label }}</span
            >
          </div>
          <dl class="facts">
            <div>
              <dt>Gross</dt>
              <dd class="mono">97,58 €</dd>
            </div>
            <div>
              <dt>Due</dt>
              <dd>06 Nov 2026</dd>
            </div>
            <div>
              <dt>Received</dt>
              <dd>07 Oct, 10:05</dd>
            </div>
            <div>
              <dt>Format</dt>
              <dd>XRechnung · CII <span class="ok">Valid</span></dd>
            </div>
          </dl>

          <div class="check" :class="{ 'check--resolved': resolved }">
            <p class="check__title">
              <Icon name="octagon" :size="14" />
              <span class="check__severity">Block</span>
              Bank account differs from earlier invoices
            </p>
            <dl class="ibans">
              <div>
                <dt>Before</dt>
                <dd class="mono">DE89 3704 0044 0532 0130 00</dd>
              </div>
              <div>
                <dt>Now</dt>
                <dd class="mono">
                  DE02 1203 0000 0000 2020 51
                  <span class="tag" :class="{ 'tag--confirmed': resolved }">{{
                    resolved ? "Confirmed change" : "New account"
                  }}</span>
                </dd>
              </div>
            </dl>
            <form v-if="!resolved" class="note" @submit.prevent="resolve">
              <label for="act2-note" class="note__label"
                >How did you check this?</label
              >
              <textarea
                id="act2-note"
                v-model="note"
                rows="2"
                maxlength="500"
                :aria-invalid="noteError ? 'true' : undefined"
                :aria-describedby="noteError ? 'act2-note-error' : undefined"
                @input="noteError = false"
              ></textarea>
              <p
                v-if="noteError"
                id="act2-note-error"
                class="note__error"
                role="alert"
              >
                <Icon name="octagon" :size="14" />Add a note before you resolve
                this check.
              </p>
              <div class="note__actions">
                <Button size="sm" variant="ghost" @click="useExample"
                  >Use example note</Button
                >
                <Button size="sm" variant="primary" type="submit"
                  >Resolve check</Button
                >
              </div>
            </form>
            <div v-else class="resolution">
              <span>Resolved by Anna Weber, just now</span>
              <q>{{ quote }}</q>
            </div>
          </div>

          <div class="review">
            <template v-if="!reviewed">
              <Button
                :disabled="!resolved"
                :disabled-reason="
                  resolved ? undefined : 'Resolve the block check first.'
                "
                variant="primary"
                @click="markReviewed"
              >
                Mark reviewed
              </Button>
              <p v-if="resolved" class="review__ready" role="status">
                Check resolved. Ready for review.
              </p>
            </template>
            <p v-else-if="!approved" role="status">
              You marked this reviewed. Jonas Brandt approves next.
            </p>
            <div v-else class="review__end">
              <span role="status">Approved by Jonas Brandt.</span>
              <Button size="sm" variant="ghost" @click="reset">
                <Icon name="refresh" :size="14" />Do it again
              </Button>
            </div>
          </div>
        </div>
      </section>

      <section class="phone" aria-label="Jonas Brandt's phone">
        <div class="phone__bar"><span>10:12</span></div>
        <div class="phone__head">
          <span>Approvals</span
          ><span class="avatar" aria-hidden="true">JB</span>
        </div>
        <div v-if="!reviewed" class="phone__empty">
          <p class="phone__empty-title">Nothing to approve yet</p>
          <p>Anna is still reviewing.</p>
        </div>
        <article v-else class="card">
          <h3 class="card__supplier">Bürobedarf Nord KG</h3>
          <p class="mono">BN-88290 · 97,58 €</p>
          <p>Due 06 Nov 2026</p>
          <p class="mono">
            DE02 1203 0000 0000 2020 51
            <span class="tag tag--confirmed">Confirmed change</span>
          </p>
          <p class="card__reviewed">Reviewed by Anna Weber, just now</p>
          <q class="card__quote">{{ quote }}</q>
          <div v-if="!approved" class="card__actions">
            <Button size="lg" :disabled="approving" @click="rejectHint = true"
              >Reject…</Button
            >
            <Button
              size="lg"
              variant="primary"
              :loading="approving"
              @click="approve"
            >
              {{ approving ? "Approving…" : "Approve" }}
            </Button>
          </div>
          <p v-else class="card__done" role="status">
            You approved this on 09 Oct 2026.
          </p>
          <p v-if="rejectHint" class="card__hint" role="status">
            Rejecting works in the sandbox. Here, approve it to see the export.
          </p>
        </article>
      </section>

      <div class="folder" aria-label="Exports">
        <div
          class="export"
          :class="{ 'export--in': exported }"
          :aria-hidden="!exported"
        >
          <span class="mono">BN-88290</span>
          <span>Bürobedarf Nord KG</span>
          <span class="mono">97,58 €</span>
          <span class="chip chip--exported">Exported</span>
        </div>
        <div class="folder__body">
          <span class="folder__label">Für den Steuerberater</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.act {
  display: grid;
  gap: var(--space-24);
}

.steps {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-8) var(--space-24);
  margin: 0;
  padding: 0;
  list-style: none;
  color: var(--muted);
  font-weight: 500;
}

.step {
  display: inline-flex;
  gap: var(--space-8);
  align-items: center;
}

.step--current {
  color: var(--ink);
  font-weight: 600;
}

.step--done {
  color: var(--ok);
}

.stage {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  grid-template-areas:
    "window phone"
    "folder phone";
  gap: var(--space-24);
  align-items: start;
}

.window {
  grid-area: window;
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
  padding: 0 var(--space-8);
  border-radius: var(--r-pill);
  background: var(--stamp-soft);
  color: var(--stamp);
  font-size: var(--fs-12);
}

.user {
  display: inline-flex;
  gap: var(--space-8);
  align-items: center;
  margin-left: auto;
}

.avatar {
  display: inline-grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--stamp-soft);
  color: var(--stamp);
  font-size: var(--fs-12);
  font-weight: 600;
}

.invoice {
  display: grid;
  gap: var(--space-16);
  padding: var(--space-20);
}

.invoice__head {
  display: flex;
  justify-content: space-between;
  gap: var(--space-12);
}

.invoice__supplier,
.card__supplier {
  margin: 0;
  font-family: var(--font-head);
  font-size: var(--fs-16);
}

.facts,
.ibans {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: var(--space-8) var(--space-16);
  margin: 0;
  font-size: var(--fs-13);
}

.facts dt,
.ibans dt {
  color: var(--muted);
}

.facts dd,
.ibans dd {
  margin: 0;
}

.ok {
  color: var(--ok);
}

.mono {
  font-family: var(--font-mono);
}

.chip {
  align-self: start;
  padding: 0 var(--space-8);
  border-radius: var(--r-pill);
  font-size: var(--fs-12);
  font-weight: 500;
  white-space: nowrap;
}

.chip--needs {
  background: var(--warn-soft);
  color: var(--warn-text);
}

.chip--awaiting {
  background: var(--stamp-soft);
  color: var(--stamp);
}

.chip--approved,
.chip--exported {
  background: var(--ok-soft);
  color: var(--ok);
}

.check {
  display: grid;
  gap: var(--space-12);
  padding: var(--space-12) var(--space-16);
  border: 1px solid var(--line);
  border-left: 4px solid var(--block);
  border-radius: var(--r-md);
}

.check--resolved {
  border-left-color: var(--ok);
}

.check__title {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-4);
  align-items: center;
  margin: 0;
  font-weight: 500;
}

.check__severity {
  color: var(--block);
}

.tag {
  margin-left: var(--space-8);
  padding: 0 var(--space-8);
  border-radius: var(--r-pill);
  background: var(--block-soft);
  color: var(--block);
  font-family: var(--font-sans);
  font-size: var(--fs-12);
}

.tag--confirmed {
  background: var(--ok-soft);
  color: var(--ok);
}

.note {
  display: grid;
  gap: var(--space-8);
}

.note__label {
  font-size: var(--fs-13);
  font-weight: 500;
}

.note textarea {
  width: 100%;
  padding: var(--space-8);
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  font: inherit;
  resize: vertical;
}

.note__error {
  display: flex;
  gap: var(--space-4);
  align-items: center;
  margin: 0;
  color: var(--block);
  font-size: var(--fs-13);
}

.note__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-8);
  justify-content: flex-end;
}

.resolution {
  display: grid;
  gap: var(--space-4);
  color: var(--muted);
  font-size: var(--fs-13);
  animation: fade 200ms var(--ease-out);
}

.review {
  display: grid;
  gap: var(--space-8);
  justify-items: start;
}

.review p {
  margin: 0;
}

.review__ready {
  color: var(--ok);
}

.review__end {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-12);
  align-items: center;
}

.phone {
  grid-area: phone;
  display: grid;
  align-content: start;
  gap: var(--space-12);
  min-height: 460px;
  padding: var(--space-16);
  border: 8px solid var(--ink);
  border-radius: 32px;
  background: var(--paper);
}

.phone__bar {
  font-size: var(--fs-12);
  font-weight: 600;
}

.phone__head {
  display: flex;
  justify-content: space-between;
  font-family: var(--font-head);
  font-weight: 700;
}

.phone__empty {
  color: var(--muted);
  text-align: center;
}

.phone__empty-title {
  color: var(--ink);
  font-weight: 600;
}

.card {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-12);
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  background: var(--win);
  font-size: var(--fs-13);
  animation: rise 320ms var(--ease-arrive);
}

.card p {
  margin: 0;
}

.card__reviewed,
.card__quote {
  color: var(--muted);
}

.card__actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-8);
  margin-top: var(--space-8);
}

.card__done {
  color: var(--ok);
  font-weight: 500;
}

.folder {
  grid-area: folder;
  position: relative;
  max-width: 420px;
  padding-top: 32px;
}

.folder__body {
  position: relative;
  z-index: 1;
  height: 96px;
  border: 2px solid var(--ink);
  border-radius: 4px 4px var(--r-md) var(--r-md);
  background: var(--paper);
}

.folder__label {
  position: absolute;
  bottom: var(--space-12);
  left: var(--space-16);
  font-family: var(--font-hand);
  font-size: var(--fs-21);
}

.export {
  position: absolute;
  top: 0;
  right: var(--space-16);
  left: var(--space-16);
  z-index: 0;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-8);
  align-items: center;
  padding: var(--space-8) var(--space-12);
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  background: var(--win);
  font-size: var(--fs-12);
  opacity: 0;
  transform: translateY(-48px);
  transition:
    opacity 700ms var(--ease-draw),
    transform 700ms var(--ease-draw);
}

.export--in {
  opacity: 1;
  transform: translateY(26px);
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}

@keyframes fade {
  from {
    opacity: 0;
  }
}

@keyframes rise {
  from {
    opacity: 0;
    transform: translateY(24px);
  }
}

@media (max-width: 1099px) {
  .stage {
    grid-template-columns: 1fr;
    grid-template-areas:
      "window"
      "phone"
      "folder";
  }

  .phone {
    max-width: 358px;
    min-height: 0;
  }

  .card__actions :deep(button),
  .note__actions :deep(button) {
    min-height: 44px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .resolution,
  .card {
    animation: none;
  }

  .export {
    transition: none;
  }
}
</style>
