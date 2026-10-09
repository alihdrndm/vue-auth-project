<script setup lang="ts">
// The Text tab: the PDF's text layer as read for extraction, with the selected field's evidence
// marked (design: --hl with a --stamp ring) and scrolled into view.
import { computed, nextTick, ref, watch } from "vue";

import { findEvidence, markLines } from "./evidence";

const props = withDefaults(
  defineProps<{
    text: string;
    /** The evidence string of the selected field, if any. */
    evidence?: string | null;
  }>(),
  { evidence: null },
);

const root = ref<HTMLElement | null>(null);
const normalised = computed(() => props.text.replace(/\r\n?/g, "\n"));
const range = computed(() => findEvidence(normalised.value, props.evidence));
const lines = computed(() => markLines(normalised.value, range.value));

watch(
  range,
  async (value) => {
    if (!value) return;
    await nextTick();
    root.value
      ?.querySelector("mark")
      ?.scrollIntoView?.({ block: "center", behavior: "smooth" });
  },
  { immediate: true },
);
</script>

<template>
  <div ref="root" class="text">
    <p class="text-note">
      Text layer of the PDF, as the AI read it. Highlighted: the line behind the
      selected field.
    </p>
    <p
      v-if="evidence && !range"
      class="text-note text-note--miss"
      role="status"
    >
      The selected field's text was not found in the text layer.
    </p>
    <p v-if="lines.length === 0 || normalised.trim() === ''" class="text-empty">
      This PDF has no text layer.
    </p>
    <div v-else class="text-lines">
      <div
        v-for="line in lines"
        :key="line.number"
        class="text-line"
        :class="{ 'is-hit': line.hit }"
      >
        <span class="text-number" aria-hidden="true">{{ line.number }}</span>
        <span class="text-content"
          ><template v-for="(segment, index) in line.segments" :key="index"
            ><mark v-if="segment.mark" class="evidence">{{ segment.text }}</mark
            ><template v-else>{{ segment.text }}</template></template
          ></span
        >
      </div>
    </div>
  </div>
</template>

<style scoped>
.text {
  min-height: 100%;
  background: var(--win);
  font-family: var(--font-mono);
  font-size: var(--fs-13);
  line-height: var(--space-24);
  color: var(--ink);
}

.text-note,
.text-empty {
  padding: var(--space-8) var(--space-16);
  border-bottom: 1px solid var(--line);
  font-family: var(--font-sans);
  font-size: var(--fs-12);
  line-height: var(--lh-app);
  color: var(--muted);
}

.text-note--miss {
  color: var(--text);
}

.text-empty {
  border-bottom: 0;
}

.text-line {
  display: grid;
  grid-template-columns: var(--space-56) minmax(0, 1fr);
}

.text-line.is-hit {
  background: var(--soft);
}

.text-number {
  padding-right: var(--space-12);
  border-right: 1px solid var(--line);
  background: var(--bar);
  color: var(--muted);
  text-align: right;
  user-select: none;
}

.text-content {
  padding: 0 var(--space-16);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.evidence {
  border-radius: var(--r-sm);
  background: var(--hl);
  box-shadow: 0 0 0 2px var(--stamp);
  color: var(--ink);
}
</style>
