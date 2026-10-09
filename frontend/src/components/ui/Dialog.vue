<!-- eslint-disable vue/multi-word-component-names -- named after the design system component -->
<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, useId, watch } from "vue";

import Icon from "./Icon.vue";

withDefaults(
  defineProps<{
    title: string;
    /** Short line under the title, e.g. the supplier and amount. */
    description?: string;
    /** sm 480 px, md 520 px, lg 680 px; full width minus 16 px margins on phones. */
    size?: "sm" | "md" | "lg";
  }>(),
  { description: undefined, size: "sm" },
);

const open = defineModel<boolean>("open", { required: true });

defineSlots<{ default?: () => unknown; footer?: () => unknown }>();

const id = useId();
const titleId = `${id}-title`;
const descriptionId = `${id}-description`;
const dialogRef = ref<HTMLDialogElement | null>(null);
let opener: HTMLElement | null = null;

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
const FIELDS =
  "input:not([disabled]), select:not([disabled]), textarea:not([disabled])";

function focusables(): HTMLElement[] {
  const dialog = dialogRef.value;
  return dialog
    ? Array.from(dialog.querySelectorAll<HTMLElement>(FOCUSABLE))
    : [];
}

async function show(): Promise<void> {
  opener =
    document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null;
  await nextTick();
  const dialog = dialogRef.value;
  if (!dialog) return;
  if (typeof dialog.showModal === "function") {
    if (!dialog.open) dialog.showModal();
  } else {
    dialog.setAttribute("open", "");
  }
  // Focus moves to the first field, otherwise to the first control.
  const target =
    dialog.querySelector<HTMLElement>("[autofocus]") ??
    dialog.querySelector<HTMLElement>(`.dialog-body :is(${FIELDS})`) ??
    focusables()[0];
  target?.focus();
}

function hide(): void {
  const dialog = dialogRef.value;
  if (dialog) {
    if (typeof dialog.close === "function" && dialog.open) dialog.close();
    else dialog.removeAttribute("open");
  }
  if (opener?.isConnected) opener.focus();
  opener = null;
}

function close(): void {
  open.value = false;
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape") {
    event.preventDefault();
    close();
    return;
  }
  if (event.key !== "Tab") return;
  // Keep focus inside the dialog.
  const items = focusables();
  const first = items[0];
  const last = items[items.length - 1];
  if (!first || !last) return;
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

function onCancel(event: Event): void {
  event.preventDefault();
  close();
}

function onBackdropClick(event: MouseEvent): void {
  if (event.target === dialogRef.value) close();
}

watch(
  open,
  (isOpen) => {
    if (isOpen) void show();
    else hide();
  },
  { immediate: true },
);

onBeforeUnmount(() => {
  if (open.value) hide();
});
</script>

<template>
  <dialog
    ref="dialogRef"
    class="dialog"
    :class="`dialog--${size}`"
    aria-modal="true"
    :aria-labelledby="titleId"
    :aria-describedby="description ? descriptionId : undefined"
    @keydown="onKeydown"
    @cancel="onCancel"
    @click="onBackdropClick"
  >
    <div v-if="open" class="dialog-inner">
      <div class="dialog-head">
        <div class="dialog-titles">
          <h2 :id="titleId" class="dialog-title">{{ title }}</h2>
          <p v-if="description" :id="descriptionId" class="dialog-description">
            {{ description }}
          </p>
        </div>
        <button
          type="button"
          class="dialog-close"
          aria-label="Close"
          @click="close"
        >
          <Icon name="x" :size="16" />
        </button>
      </div>
      <div class="dialog-body">
        <slot />
      </div>
      <div v-if="$slots.footer" class="dialog-footer">
        <slot name="footer" />
      </div>
    </div>
  </dialog>
</template>

<style scoped>
.dialog {
  width: var(--size-dialog-sm);
  max-width: calc(100vw - 2 * var(--space-16));
  max-height: calc(100vh - 2 * var(--space-24));
  padding: 0;
  border: 1px solid var(--line);
  border-radius: var(--r-lg);
  background: var(--win);
  box-shadow: var(--shadow-window);
  color: var(--text);
  overflow: auto;
}

.dialog::backdrop {
  background: var(--backdrop);
}

.dialog--md {
  width: var(--size-dialog-md);
}

.dialog--lg {
  width: var(--size-dialog-lg);
}

.dialog-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-16);
  padding: var(--space-20) var(--space-16) 0 var(--space-24);
}

.dialog-titles {
  display: grid;
  gap: var(--space-4);
}

.dialog-title {
  font-family: var(--font-head);
  font-size: var(--fs-16);
  font-weight: 700;
  letter-spacing: var(--tracking-head);
  line-height: var(--lh-app);
  color: var(--ink);
}

.dialog-description {
  font-size: var(--fs-13);
  color: var(--muted);
}

.dialog-close {
  display: inline-grid;
  flex: none;
  place-items: center;
  width: var(--size-md);
  height: var(--size-md);
  border: 1px solid transparent;
  border-radius: var(--r-sm);
  background: transparent;
  color: var(--text);
  cursor: pointer;
}

.dialog-close:hover {
  background: var(--soft);
}

.dialog-body {
  display: grid;
  gap: var(--space-16);
  padding: var(--space-20) var(--space-24);
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-8);
  padding: var(--space-16) var(--space-24);
  border-top: 1px solid var(--line);
  background: var(--bar);
}
</style>
