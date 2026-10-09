<script setup lang="ts">
import { computed, useId } from "vue";

import Icon from "./Icon.vue";

const props = withDefaults(
  defineProps<{
    label: string;
    type?: "text" | "email" | "password" | "search" | "number" | "tel" | "url";
    /** Mono for IBANs, VAT IDs and numbers. */
    mono?: boolean;
    /** lg: 44 px, 16 px text (phone). */
    size?: "md" | "lg";
    hint?: string;
    error?: string;
    disabled?: boolean;
    placeholder?: string;
    required?: boolean;
    autocomplete?: string;
    name?: string;
    maxlength?: number;
  }>(),
  {
    type: "text",
    mono: false,
    size: "md",
    hint: undefined,
    error: undefined,
    disabled: false,
    placeholder: undefined,
    required: false,
    autocomplete: undefined,
    name: undefined,
    maxlength: undefined,
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
  <div class="field" :class="{ 'field--disabled': disabled }">
    <label class="field-label" :for="id">{{ label }}</label>
    <input
      :id="id"
      v-model="model"
      v-bind="$attrs"
      class="field-control"
      :class="{
        'field-control--mono': mono,
        'field-control--lg': size === 'lg',
      }"
      :type="type"
      :name="name"
      :placeholder="placeholder"
      :required="required"
      :autocomplete="autocomplete"
      :maxlength="maxlength"
      :disabled="disabled"
      :aria-invalid="error ? 'true' : undefined"
      :aria-describedby="describedBy"
    />
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

.field-label {
  font-size: var(--fs-13);
  font-weight: 500;
  color: var(--ink);
}

.field--disabled .field-label {
  color: var(--muted);
}

.field-control {
  width: 100%;
  height: var(--size-md);
  padding: 0 var(--space-12);
  border: 1px solid var(--line-strong);
  border-radius: var(--r-sm);
  background: var(--win);
  font-size: var(--fs-14);
  color: var(--ink);
}

.field-control::placeholder {
  color: var(--muted);
}

.field-control--mono {
  font-family: var(--font-mono);
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
