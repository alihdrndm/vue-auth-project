<script setup lang="ts">
import { computed, useId } from "vue";

import Icon from "./Icon.vue";

const props = withDefaults(
  defineProps<{
    label: string;
    hint?: string;
    error?: string;
    disabled?: boolean;
    placeholder?: string;
    required?: boolean;
    name?: string;
    minlength?: number;
    maxlength?: number;
    /** Shows "<length> / <maxlength>" next to the label, announced politely. */
    counter?: boolean;
  }>(),
  {
    hint: undefined,
    error: undefined,
    disabled: false,
    placeholder: undefined,
    required: false,
    name: undefined,
    minlength: undefined,
    maxlength: undefined,
    counter: false,
  },
);

const model = defineModel<string>({ default: "" });

defineOptions({ inheritAttrs: false });

const id = useId();
const hintId = `${id}-hint`;
const errorId = `${id}-error`;
const describedBy = computed(() => {
  const ids: string[] = [];
  if (props.error) ids.push(errorId);
  if (props.hint) ids.push(hintId);
  return ids.length > 0 ? ids.join(" ") : undefined;
});
const showCounter = computed(
  () => props.counter && props.maxlength !== undefined,
);
</script>

<template>
  <div class="field" :class="{ 'field--disabled': disabled }">
    <span class="field-head">
      <label class="field-label" :for="id">{{ label }}</label>
      <span v-if="showCounter" class="field-counter" aria-live="polite"
        >{{ model.length }} / {{ maxlength }}</span
      >
    </span>
    <textarea
      :id="id"
      v-model="model"
      v-bind="$attrs"
      class="field-control"
      :name="name"
      :placeholder="placeholder"
      :required="required"
      :minlength="minlength"
      :maxlength="maxlength"
      :disabled="disabled"
      :aria-invalid="error ? 'true' : undefined"
      :aria-describedby="describedBy"
    ></textarea>
    <span v-if="error" :id="errorId" class="field-error" role="alert"
      ><Icon name="octagon" :size="14" />{{ error }}</span
    >
    <span v-if="hint" :id="hintId" class="field-hint">{{ hint }}</span>
  </div>
</template>

<style scoped>
.field {
  display: grid;
  gap: var(--space-4);
  align-content: start;
}

.field-head {
  display: flex;
  justify-content: space-between;
  gap: var(--space-8);
}

.field-label {
  font-size: var(--fs-13);
  font-weight: 500;
  color: var(--ink);
}

.field--disabled .field-label {
  color: var(--muted);
}

.field-counter {
  font-family: var(--font-mono);
  font-size: var(--fs-12);
  color: var(--muted);
}

.field-control {
  width: 100%;
  min-height: var(--size-textarea);
  padding: var(--space-8) var(--space-12);
  border: 1px solid var(--line-strong);
  border-radius: var(--r-sm);
  background: var(--win);
  font-size: var(--fs-14);
  line-height: var(--lh-app);
  color: var(--ink);
  resize: vertical;
  field-sizing: content;
}

.field-control::placeholder {
  color: var(--muted);
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
