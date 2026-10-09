<!-- eslint-disable vue/multi-word-component-names -- named after the design system component -->
<script setup lang="ts">
import { computed, useId } from "vue";

import Icon from "./Icon.vue";

export interface SelectOption {
  value: string;
  label: string;
}

const props = withDefaults(
  defineProps<{
    label: string;
    options: SelectOption[];
    /** Shown first with an empty value, e.g. "Choose a role". */
    placeholder?: string;
    hint?: string;
    error?: string;
    disabled?: boolean;
    required?: boolean;
    name?: string;
    /** lg: 44 px, 16 px text (phone). */
    size?: "md" | "lg";
    /** Label to the left in muted text, as in the inbox filter bar. */
    inline?: boolean;
  }>(),
  {
    placeholder: undefined,
    hint: undefined,
    error: undefined,
    disabled: false,
    required: false,
    name: undefined,
    size: "md",
    inline: false,
  },
);

const model = defineModel<string>({ default: "" });

defineOptions({ inheritAttrs: false });

const id = useId();
const hintId = `${id}-hint`;
const errorId = `${id}-error`;
const describedBy = computed(() => {
  if (props.error) return errorId;
  if (props.hint) return hintId;
  return undefined;
});
</script>

<template>
  <div
    class="field"
    :class="{ 'field--disabled': disabled, 'field--inline': inline }"
  >
    <label class="field-label" :for="id">{{ label }}</label>
    <span class="field-box">
      <select
        :id="id"
        v-model="model"
        v-bind="$attrs"
        class="field-control"
        :class="{
          'field-control--lg': size === 'lg',
          'field-control--empty': model === '',
        }"
        :name="name"
        :required="required"
        :disabled="disabled"
        :aria-invalid="error ? 'true' : undefined"
        :aria-describedby="describedBy"
      >
        <option v-if="placeholder !== undefined" value="" disabled>
          {{ placeholder }}
        </option>
        <option
          v-for="option in options"
          :key="option.value"
          :value="option.value"
        >
          {{ option.label }}
        </option>
      </select>
      <Icon
        class="field-chevron"
        :name="disabled ? 'lock' : 'chevron-down'"
        :size="16"
      />
    </span>
    <span v-if="error" :id="errorId" class="field-error"
      ><Icon name="octagon" :size="14" />{{ error }}</span
    >
    <span v-else-if="hint" :id="hintId" class="field-hint">{{ hint }}</span>
  </div>
</template>

<style scoped>
.field {
  display: grid;
  gap: var(--space-4);
  align-content: start;
}

.field--inline {
  display: inline-flex;
  align-items: center;
  gap: var(--space-8);
}

.field-label {
  font-size: var(--fs-13);
  font-weight: 500;
  color: var(--ink);
}

.field--inline .field-label {
  font-weight: 400;
  color: var(--muted);
}

.field--disabled .field-label {
  color: var(--muted);
}

.field-box {
  position: relative;
  display: flex;
}

.field-control {
  appearance: none;
  width: 100%;
  height: var(--size-md);
  padding: 0 var(--space-32) 0 var(--space-12);
  border: 1px solid var(--line-strong);
  border-radius: var(--r-sm);
  background: var(--win);
  font-size: var(--fs-14);
  color: var(--ink);
  cursor: pointer;
}

.field-control--empty {
  color: var(--muted);
}

.field-control--lg {
  height: var(--size-lg);
  font-size: var(--fs-16);
}

.field-control:hover:not(:disabled) {
  border-color: var(--muted);
}

.field-control:focus-visible {
  border-color: var(--ink);
}

.field-control[aria-invalid="true"] {
  border-color: var(--block);
}

.field-control:disabled {
  border-color: var(--line);
  background: var(--soft);
  color: var(--muted);
  cursor: not-allowed;
}

.field-chevron {
  position: absolute;
  top: 50%;
  right: var(--space-8);
  transform: translateY(-50%);
  color: var(--text);
  pointer-events: none;
}

.field--disabled .field-chevron {
  color: var(--muted);
}

.field-error {
  display: flex;
  align-items: flex-start;
  gap: var(--space-4);
  font-size: var(--fs-12);
  color: var(--block);
}

.field-hint {
  font-size: var(--fs-12);
  color: var(--muted);
}
</style>
