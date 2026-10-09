<!-- eslint-disable vue/multi-word-component-names -- named after the design system component -->
<script setup lang="ts">
import { computed, useId } from "vue";

import Icon from "./Icon.vue";
import type { IconName } from "./icons";

const props = withDefaults(
  defineProps<{
    variant?: "primary" | "secondary" | "ghost" | "danger";
    size?: "sm" | "md" | "lg";
    type?: "button" | "submit" | "reset";
    /** Leading icon. */
    icon?: IconName;
    /** Shows the spinner; the label should say what is happening ("Approving…"). */
    loading?: boolean;
    disabled?: boolean;
    /** Why the action is unavailable. Shown as a tooltip and read out with the button. */
    disabledReason?: string;
  }>(),
  {
    variant: "secondary",
    size: "md",
    type: "button",
    icon: undefined,
    loading: false,
    disabled: false,
    disabledReason: undefined,
  },
);

defineOptions({ inheritAttrs: false });

const emit = defineEmits<{ click: [event: MouseEvent] }>();

const reasonId = useId();
const isDisabled = computed(
  () => props.disabled || props.disabledReason !== undefined,
);
const iconSize = computed(() => (props.size === "lg" ? 20 : 16));

function onClick(event: MouseEvent): void {
  if (isDisabled.value || props.loading) return;
  emit("click", event);
}
</script>

<template>
  <span class="button-wrap">
    <button
      v-bind="$attrs"
      class="button"
      :class="[
        `button--${variant}`,
        `button--${size}`,
        { 'button--loading': loading },
      ]"
      :type="type"
      :disabled="isDisabled"
      :aria-busy="loading ? 'true' : undefined"
      :aria-disabled="loading ? 'true' : undefined"
      :aria-describedby="disabledReason ? reasonId : undefined"
      @click="onClick"
    >
      <Icon v-if="loading" name="loader" :size="iconSize" spin />
      <Icon v-else-if="disabledReason" name="lock" :size="14" />
      <Icon v-else-if="icon" :name="icon" :size="iconSize" />
      <slot />
    </button>
    <span
      v-if="disabledReason"
      :id="reasonId"
      role="tooltip"
      class="button-tooltip"
      >{{ disabledReason }}</span
    >
  </span>
</template>

<style scoped>
.button-wrap {
  position: relative;
  display: inline-flex;
}

.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-8);
  height: var(--size-md);
  padding: 0 var(--space-12);
  border: 1px solid transparent;
  border-radius: var(--r-sm);
  font-size: var(--fs-14);
  font-weight: 500;
  line-height: 1;
  white-space: nowrap;
  cursor: pointer;
}

.button:active:not(:disabled) {
  transform: translateY(1px);
}

.button--sm {
  gap: var(--space-4);
  height: var(--size-sm);
  font-size: var(--fs-13);
}

.button--lg {
  height: var(--size-lg);
  padding: 0 var(--space-20);
  font-size: var(--fs-16);
}

.button--primary {
  background: var(--ink);
  color: var(--win);
  border-color: var(--ink);
}

.button--primary:hover:not(:disabled) {
  background: var(--text);
  border-color: var(--text);
}

.button--secondary {
  background: var(--win);
  color: var(--ink);
  border-color: var(--line-strong);
}

.button--secondary:hover:not(:disabled) {
  background: var(--soft);
}

.button--secondary:active:not(:disabled) {
  background: var(--line);
}

.button--ghost {
  background: transparent;
  color: var(--text);
}

.button--ghost:hover:not(:disabled) {
  background: var(--soft);
  color: var(--ink);
}

.button--ghost:active:not(:disabled) {
  background: var(--line);
}

.button--danger {
  background: var(--block-soft);
  color: var(--block);
  border-color: var(--block);
}

.button--danger:hover:not(:disabled),
.button--danger:active:not(:disabled) {
  background: var(--block);
  color: var(--win);
}

.button--loading,
.button--loading:hover:not(:disabled) {
  cursor: progress;
}

.button--primary.button--loading,
.button--primary.button--loading:hover:not(:disabled) {
  background: var(--ink);
  border-color: var(--ink);
}

.button--secondary.button--loading,
.button--secondary.button--loading:hover:not(:disabled) {
  background: var(--win);
}

.button--ghost.button--loading,
.button--ghost.button--loading:hover:not(:disabled) {
  background: transparent;
  color: var(--text);
}

.button--danger.button--loading,
.button--danger.button--loading:hover:not(:disabled) {
  background: var(--block-soft);
  color: var(--block);
}

.button:disabled {
  background: var(--soft);
  color: var(--muted);
  border-color: var(--line);
  cursor: not-allowed;
}

.button--ghost:disabled {
  background: transparent;
  border-color: transparent;
}

.button-tooltip {
  position: absolute;
  left: 0;
  bottom: calc(100% + var(--space-8));
  z-index: 10;
  width: max-content;
  max-width: var(--size-tooltip-max);
  padding: var(--space-4) var(--space-8);
  border-radius: var(--r-sm);
  background: var(--ink);
  color: var(--win);
  font-size: var(--fs-12);
  font-weight: 400;
  line-height: 1.4;
  white-space: normal;
  visibility: hidden;
  pointer-events: none;
}

.button-wrap:hover .button-tooltip,
.button-wrap:focus-within .button-tooltip {
  visibility: visible;
}
</style>
