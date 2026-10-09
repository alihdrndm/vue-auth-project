<!-- eslint-disable vue/multi-word-component-names -- named after the design system component -->
<script setup lang="ts">
import Icon from "./Icon.vue";

withDefaults(
  defineProps<{
    /**
     * count: mono number pill; label: small word ("You"); sample: dashed "Sample" marker
     * for illustrative numbers; overdue: the overdue marker.
     */
    variant?: "count" | "label" | "sample" | "overdue";
    /** Count badge inside the selected tab. */
    selected?: boolean;
  }>(),
  { variant: "count", selected: false },
);
</script>

<template>
  <span
    class="badge"
    :class="[`badge--${variant}`, { 'badge--selected': selected }]"
  >
    <Icon v-if="variant === 'overdue'" name="clock" :size="12" />
    <slot>{{
      variant === "sample" ? "Sample" : variant === "overdue" ? "Overdue" : ""
    }}</slot>
  </span>
</template>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-4);
  height: var(--size-badge);
  padding: 0 var(--space-8);
  border-radius: var(--r-pill);
  font-size: var(--fs-12);
  font-weight: 500;
  line-height: 1;
  white-space: nowrap;
}

.badge--count {
  min-width: var(--size-badge);
  padding: 0 var(--space-4);
  border: 1px solid var(--line);
  background: var(--soft);
  color: var(--text);
  font-family: var(--font-mono);
}

.badge--count.badge--selected {
  border-color: var(--ink);
  background: var(--ink);
  color: var(--win);
}

.badge--label {
  background: var(--stamp-soft);
  color: var(--stamp);
}

.badge--sample {
  border: 1px dashed var(--muted);
  background: var(--win);
  color: var(--muted);
}

.badge--overdue {
  background: var(--block-soft);
  color: var(--block);
}
</style>
