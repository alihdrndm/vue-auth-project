<!-- eslint-disable vue/multi-word-component-names -- named after the design system component -->
<script setup lang="ts">
import { computed } from "vue";

import Icon from "./Icon.vue";
import type { IconName } from "./icons";
import { type ToastKind, useToast } from "./useToast";

// The toast region. Mount once per page layout; show toasts with useToast().show().
const { toast, dismiss } = useToast();

const LOOK: Record<ToastKind, { icon: IconName; spin: boolean }> = {
  success: { icon: "circle-check", spin: false },
  info: { icon: "loader", spin: true },
  error: { icon: "octagon", spin: false },
  "rate-limit": { icon: "clock", spin: false },
};

const isAlert = computed(
  () => toast.value?.kind === "error" || toast.value?.kind === "rate-limit",
);

function runAction(): void {
  const action = toast.value?.action;
  dismiss();
  action?.run();
}
</script>

<template>
  <div class="toast-region">
    <div role="status" aria-live="polite" aria-atomic="true">
      <div
        v-if="toast && !isAlert"
        :key="toast.id"
        class="toast"
        :class="`toast--${toast.kind}`"
      >
        <Icon
          class="toast-icon"
          :name="LOOK[toast.kind].icon"
          :spin="LOOK[toast.kind].spin"
        />
        <span class="toast-message">{{ toast.message }}</span>
        <button
          v-if="toast.action"
          type="button"
          class="toast-action"
          @click="runAction"
        >
          {{ toast.action.label }}
        </button>
        <button
          type="button"
          class="toast-dismiss"
          aria-label="Dismiss"
          @click="dismiss"
        >
          <Icon name="x" />
        </button>
      </div>
    </div>
    <div role="alert" aria-atomic="true">
      <div
        v-if="toast && isAlert"
        :key="toast.id"
        class="toast"
        :class="`toast--${toast.kind}`"
      >
        <Icon class="toast-icon" :name="LOOK[toast.kind].icon" />
        <span class="toast-message">{{ toast.message }}</span>
        <button
          v-if="toast.action"
          type="button"
          class="toast-action"
          @click="runAction"
        >
          {{ toast.action.label }}
        </button>
        <button
          type="button"
          class="toast-dismiss"
          aria-label="Dismiss"
          @click="dismiss"
        >
          <Icon name="x" />
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.toast-region {
  position: fixed;
  right: var(--space-24);
  bottom: var(--space-24);
  z-index: 40;
  max-width: calc(100vw - 2 * var(--space-24));
}

.toast {
  display: flex;
  align-items: center;
  gap: var(--space-12);
  width: var(--size-toast);
  max-width: 100%;
  min-height: var(--size-topbar);
  padding: var(--space-8) var(--space-8) var(--space-8) var(--space-16);
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  background: var(--win);
  box-shadow: var(--shadow-window);
}

.toast--success .toast-icon {
  color: var(--ok);
}

.toast--info .toast-icon {
  color: var(--info);
}

.toast--error .toast-icon {
  color: var(--block);
}

.toast--rate-limit .toast-icon {
  color: var(--warn);
}

.toast-message {
  flex: 1;
  font-size: var(--fs-14);
  color: var(--ink);
}

.toast-action {
  display: inline-flex;
  align-items: center;
  height: var(--size-sm);
  padding: 0 var(--space-8);
  border: 1px solid transparent;
  border-radius: var(--r-sm);
  background: transparent;
  color: var(--ink);
  font-size: var(--fs-13);
  font-weight: 500;
  cursor: pointer;
}

.toast-dismiss {
  display: inline-grid;
  flex: none;
  place-items: center;
  width: var(--size-sm);
  height: var(--size-sm);
  border: 1px solid transparent;
  border-radius: var(--r-sm);
  background: transparent;
  color: var(--text);
  cursor: pointer;
}

.toast-action:hover,
.toast-dismiss:hover {
  background: var(--soft);
}

@media (max-width: 767px) {
  .toast-region {
    right: var(--space-16);
    left: var(--space-16);
    bottom: var(--space-16);
    max-width: none;
  }

  .toast {
    width: 100%;
  }
}
</style>
