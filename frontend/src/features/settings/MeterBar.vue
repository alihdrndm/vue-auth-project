<script setup lang="ts">
// The design system's MeterBar (under, near limit, reached): "Spent so far ▬▬▭ $0.42 of $2.00".
// Not in components/ui yet, so it lives with the one screen that uses it.
import { computed } from "vue";

import { formatUsd, meterLevel, meterPercent } from "./settings";

const props = defineProps<{
  label: string;
  /** Accessible name of the meter, e.g. "AI budget spent so far". */
  name: string;
  spent: string;
  budget: string;
}>();

const percent = computed(() => meterPercent(props.spent, props.budget));
const level = computed(() => meterLevel(percent.value));
const text = computed(
  () => `${formatUsd(props.spent)} of ${formatUsd(props.budget)}`,
);
</script>

<template>
  <div class="meter-row" :class="`meter-row--${level}`">
    <span class="meter-label">{{ label }}</span>
    <div
      class="meter"
      role="meter"
      :aria-label="name"
      :aria-valuenow="percent"
      aria-valuemin="0"
      aria-valuemax="100"
      :aria-valuetext="text"
    >
      <div class="meter-fill" :style="{ width: `${percent}%` }" />
    </div>
    <span class="meter-text">{{ text }}</span>
  </div>
</template>

<style scoped>
.meter-row {
  display: grid;
  grid-template-columns: 120px minmax(0, 1fr) auto;
  gap: var(--space-12);
  align-items: center;
  font-size: var(--fs-13);
}

.meter-label {
  color: var(--ink);
  font-weight: 500;
}

.meter {
  height: 8px;
  border-radius: var(--r-pill);
  background: var(--soft);
  box-shadow: inset 0 0 0 1px var(--line);
  overflow: hidden;
}

.meter-fill {
  height: 100%;
  border-radius: var(--r-pill);
  background: var(--ink);
}

.meter-row--near .meter-fill {
  background: var(--warn);
}

.meter-row--reached .meter-fill {
  background: var(--block);
}

.meter-text {
  color: var(--text);
  font-family: var(--font-mono);
  font-size: var(--fs-12);
  white-space: nowrap;
}

.meter-row--reached .meter-text {
  color: var(--block);
}

@media (max-width: 767px) {
  .meter-row {
    grid-template-columns: minmax(0, 1fr) auto;
  }

  .meter {
    grid-column: 1 / -1;
    grid-row: 2;
  }
}
</style>
