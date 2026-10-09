<script lang="ts">
import type { IconName } from "./icons";

export const ZUGFERD_TOOLTIP = "ZUGFeRD and Factur-X are the same standard";

/** XML files, PDFs with XML attached and plain PDFs each have their own icon. */
export function formatIcon(label: string): IconName {
  if (label.startsWith("ZUGFeRD") || label.startsWith("Hybrid PDF"))
    return "paperclip";
  if (label.endsWith("PDF")) return "file-text";
  return "file-code";
}
</script>

<script setup lang="ts">
import { computed } from "vue";

import Icon from "./Icon.vue";

const props = withDefaults(
  defineProps<{
    /** The API's format label, e.g. "XRechnung · UBL" or "Plain PDF". */
    label: string;
    /** Appends " · credit note". */
    creditNote?: boolean;
  }>(),
  { creditNote: false },
);

const text = computed(() =>
  props.creditNote ? `${props.label} · credit note` : props.label,
);
const icon = computed(() => formatIcon(props.label));
const tooltip = computed(() =>
  props.label.startsWith("ZUGFeRD") ? ZUGFERD_TOOLTIP : undefined,
);
</script>

<template>
  <span class="format-chip" :title="tooltip"
    ><Icon :name="icon" :size="14" />{{ text }}</span
  >
</template>

<style scoped>
.format-chip {
  display: inline-flex;
  align-items: center;
  gap: var(--space-4);
  min-height: var(--size-chip);
  padding: var(--space-4) var(--space-8);
  border: 1px solid var(--line-strong);
  border-radius: var(--r-sm);
  background: var(--win);
  color: var(--text);
  font-size: var(--fs-12);
  font-weight: 500;
  line-height: var(--lh-tight);
}
</style>
