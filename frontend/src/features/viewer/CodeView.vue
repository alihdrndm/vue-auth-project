<script setup lang="ts">
// The XML tab: the invoice XML with line numbers and token colours from the design tokens.
import { computed } from "vue";

import { highlightXml } from "./xml";

const props = defineProps<{
  source: string;
  /** Accessible name, e.g. "XML of RE-2026-0412". */
  label: string;
}>();

const lines = computed(() => highlightXml(props.source));
</script>

<template>
  <div class="code" role="region" :aria-label="label" tabindex="0">
    <div class="code-lines">
      <div v-for="(line, index) in lines" :key="index" class="code-line">
        <span class="code-number" aria-hidden="true">{{ index + 1 }}</span>
        <code class="code-text"
          ><span
            v-for="(token, part) in line"
            :key="part"
            :class="`tok tok--${token.kind}`"
            >{{ token.text }}</span
          ></code
        >
      </div>
    </div>
  </div>
</template>

<style scoped>
.code {
  min-height: 100%;
  overflow: auto;
  background: var(--win);
}

.code:focus-visible {
  outline-offset: var(--focus-offset-inset);
}

.code-lines {
  display: grid;
  min-width: max-content;
  font-family: var(--font-mono);
  font-size: var(--fs-13);
  line-height: var(--space-24);
  color: var(--ink);
}

.code-line {
  display: grid;
  grid-template-columns: var(--space-56) max-content;
}

.code-number {
  padding-right: var(--space-12);
  border-right: 1px solid var(--line);
  background: var(--bar);
  color: var(--muted);
  text-align: right;
  user-select: none;
}

.code-text {
  padding: 0 var(--space-16);
  white-space: pre;
}

.tok--bracket {
  color: var(--muted);
}

.tok--name {
  color: var(--stamp);
}

.tok--attr {
  color: var(--warn-text);
}

.tok--value {
  color: var(--ok);
}

.tok--comment {
  color: var(--muted);
  font-style: italic;
}

.tok--text {
  color: var(--ink);
}
</style>
