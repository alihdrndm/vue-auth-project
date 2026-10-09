<!-- eslint-disable vue/multi-word-component-names -- named after the design system component -->
<script lang="ts">
export interface SkeletonColumn {
  /** A grid track, e.g. "96px" or "minmax(0, 1fr)". */
  track: string;
  /** text: 12 px bar; box: 16 px (checkbox); chip: 20 px pill. */
  shape?: "text" | "box" | "chip";
}

/** Skeletons appear only when loading takes longer than this. */
export const SKELETON_DELAY_MS = 300;
</script>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

const props = withDefaults(
  defineProps<{
    /** Read out while loading, e.g. "Loading invoices". */
    label: string;
    columns: SkeletonColumn[];
    rows?: number;
    /** A pane-header bar above the rows. */
    header?: boolean;
  }>(),
  { rows: 4, header: false },
);

const visible = ref(false);
let timer: ReturnType<typeof setTimeout> | undefined;

onMounted(() => {
  timer = setTimeout(() => {
    visible.value = true;
  }, SKELETON_DELAY_MS);
});

onBeforeUnmount(() => {
  if (timer !== undefined) clearTimeout(timer);
});

// Vary the text bar widths so the rows read as content.
const WIDTHS = ["70%", "55%", "80%", "60%", "65%", "50%", "85%", "75%"];
const template = computed(() =>
  props.columns.map((column) => column.track).join(" "),
);

function width(row: number, column: number): string {
  return WIDTHS[(row * 3 + column) % WIDTHS.length] ?? "70%";
}
</script>

<template>
  <div
    class="skeleton"
    :class="{ 'is-visible': visible }"
    aria-busy="true"
    :aria-label="label"
  >
    <div v-if="header" class="skeleton-header">
      <span class="bar bar--text bar--header" />
    </div>
    <div
      v-for="row in rows"
      :key="row"
      class="skeleton-row"
      :style="{ gridTemplateColumns: template }"
    >
      <span
        v-for="(column, index) in columns"
        :key="index"
        class="bar"
        :class="`bar--${column.shape ?? 'text'}`"
        :style="
          column.shape === undefined || column.shape === 'text'
            ? { width: width(row, index) }
            : undefined
        "
      />
    </div>
  </div>
</template>

<style scoped>
.skeleton {
  display: grid;
  align-content: start;
  visibility: hidden;
}

.skeleton.is-visible {
  visibility: visible;
}

.skeleton-header {
  display: flex;
  align-items: center;
  height: var(--size-lg);
  padding: 0 var(--space-16);
  border-bottom: 1px solid var(--line);
  background: var(--bar);
}

.skeleton-row {
  display: grid;
  gap: var(--space-12);
  align-items: center;
  height: var(--size-row);
  padding: 0 var(--space-16);
  border-bottom: 1px solid var(--line);
}

.skeleton-row:last-child {
  border-bottom: 0;
}

.bar {
  display: block;
  border-radius: var(--r-sm);
  background: var(--line);
}

.bar--text {
  height: var(--space-12);
}

.bar--header {
  width: 96px;
}

.bar--box {
  width: var(--space-16);
  height: var(--space-16);
}

.bar--chip {
  height: var(--size-badge);
  border-radius: var(--r-pill);
}
</style>
