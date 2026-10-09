<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    /** 3 high, 2 medium, 1 low. */
    level: 1 | 2 | 3;
    /**
     * Text alternative for the bars. Defaults to "High/Medium/Low confidence".
     * Pass an empty string when a visible word next to the bars already says it.
     */
    label?: string;
  }>(),
  { label: undefined },
);

const HEIGHTS = [5, 8, 11] as const;
const DEFAULT_LABELS = {
  1: "Low confidence",
  2: "Medium confidence",
  3: "High confidence",
};

const bars = computed(() =>
  HEIGHTS.map((height, index) => ({
    x: index * 4.5 + 0.5,
    y: 12 - height,
    height,
    filled: index < props.level,
  })),
);
const text = computed(() => props.label ?? DEFAULT_LABELS[props.level]);
</script>

<template>
  <span class="bars">
    <svg
      width="14"
      height="12"
      viewBox="0 0 14 12"
      aria-hidden="true"
      focusable="false"
    >
      <rect
        v-for="bar in bars"
        :key="bar.x"
        :x="bar.x"
        :y="bar.y"
        width="3"
        :height="bar.height"
        rx="1"
        :class="bar.filled ? 'bar--on' : 'bar--off'"
      />
    </svg>
    <span v-if="text" class="sr-only">{{ text }}</span>
  </span>
</template>

<style scoped>
.bars {
  display: inline-flex;
  flex: none;
  line-height: 0;
}

.bar--on {
  fill: currentColor;
}

.bar--off {
  fill: var(--line-strong);
}
</style>
