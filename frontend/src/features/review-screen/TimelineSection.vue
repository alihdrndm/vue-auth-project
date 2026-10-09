<script setup lang="ts">
// Timeline (design): what happened to the invoice, newest first, with who did it and when.
import { computed, useId } from "vue";

import type { components } from "../../api/schema";
import Icon from "../../components/ui/Icon.vue";
import { timelineEntries } from "./timeline";

type DocumentDetail = components["schemas"]["DocumentDetail"];

const props = defineProps<{ document: DocumentDetail }>();

const id = useId();
const entries = computed(() => timelineEntries(props.document));
</script>

<template>
  <section class="section section--last" :aria-labelledby="`${id}-title`">
    <h2 :id="`${id}-title`" class="section-title">Timeline</h2>
    <ol class="timeline">
      <li v-for="entry in entries" :key="entry.key" class="entry">
        <span class="entry-rail" aria-hidden="true">
          <span class="entry-dot" :class="`dot--${entry.tone}`">
            <Icon :name="entry.icon" :size="14" />
          </span>
          <span class="entry-line" />
        </span>
        <span class="entry-body">
          <span class="entry-title">{{ entry.title }}</span>
          <q v-if="entry.detail && entry.quote" class="entry-quote">{{
            entry.detail
          }}</q>
          <span v-else-if="entry.detail" class="entry-detail">{{
            entry.detail
          }}</span>
          <time
            v-if="entry.datetime"
            class="entry-when"
            :datetime="entry.datetime"
            >{{ entry.when }}</time
          >
          <span v-else class="entry-when">{{ entry.when }}</span>
        </span>
      </li>
    </ol>
  </section>
</template>

<style scoped src="./section.css"></style>

<style scoped>
.section--last {
  border-bottom: 0;
}

.timeline {
  display: grid;
  list-style: none;
}

.entry {
  display: grid;
  grid-template-columns: var(--size-chip) minmax(0, 1fr);
  gap: var(--space-12);
}

.entry-rail {
  display: grid;
  grid-template-rows: var(--size-chip) 1fr;
  justify-items: center;
}

.entry-dot {
  display: grid;
  place-items: center;
  width: var(--size-chip);
  height: var(--size-chip);
  border-radius: var(--r-pill);
  background: var(--soft);
  color: var(--text);
}

.dot--stamp {
  background: var(--stamp-soft);
  color: var(--stamp);
}

.dot--ok {
  background: var(--ok-soft);
  color: var(--ok);
}

.dot--block {
  background: var(--block-soft);
  color: var(--block);
}

.dot--warn {
  background: var(--warn-soft);
  color: var(--warn-text);
}

.entry-line {
  width: 1px;
  background: var(--line);
}

.entry:last-child .entry-line {
  visibility: hidden;
}

.entry-body {
  display: grid;
  gap: var(--space-4);
  padding-bottom: var(--space-20);
}

.entry-title {
  font-size: var(--fs-14);
  color: var(--ink);
}

.entry-detail {
  font-size: var(--fs-13);
  color: var(--text);
}

.entry-quote {
  display: block;
  padding: var(--space-8) var(--space-12);
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  background: var(--bar);
  font-size: var(--fs-13);
  color: var(--ink);
  quotes: none;
}

.entry-when {
  font-size: var(--fs-12);
  color: var(--muted);
}
</style>
