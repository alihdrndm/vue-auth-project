<script lang="ts">
import type { components } from "../../api/schema";
import type { IconName } from "./icons";

export type DocumentStatus = components["schemas"]["DocumentStatusEnum"];

interface StatusLook {
  label: string;
  icon: IconName;
  tone: "stamp" | "info" | "warn" | "ok" | "block" | "neutral";
}

/** The status vocabulary: exact labels and icons from the design system. */
export const STATUS_LOOK: Record<DocumentStatus, StatusLook> = {
  received: { label: "Received", icon: "inbox", tone: "stamp" },
  processing: { label: "Processing", icon: "loader", tone: "info" },
  needs_review: { label: "Needs review", icon: "eye", tone: "warn" },
  awaiting_approval: {
    label: "Awaiting approval",
    icon: "hourglass",
    tone: "stamp",
  },
  approved: { label: "Approved", icon: "circle-check", tone: "ok" },
  rejected: { label: "Rejected", icon: "ban", tone: "block" },
  exported: { label: "Exported", icon: "check", tone: "neutral" },
  failed: { label: "Failed", icon: "circle-alert", tone: "block" },
};
</script>

<script setup lang="ts">
import { computed } from "vue";

import Icon from "./Icon.vue";

const props = defineProps<{ status: DocumentStatus }>();

const look = computed(() => STATUS_LOOK[props.status]);
</script>

<template>
  <span class="chip" :class="`chip--${look.tone}`">
    <Icon
      class="chip-icon"
      :name="look.icon"
      :size="14"
      :spin="status === 'processing'"
    />{{ look.label }}
  </span>
</template>

<style scoped>
.chip {
  display: inline-flex;
  align-items: center;
  gap: var(--space-4);
  height: var(--size-chip);
  padding: 0 var(--space-8);
  border-radius: var(--r-pill);
  font-size: var(--fs-12);
  font-weight: 500;
  white-space: nowrap;
}

.chip--stamp {
  background: var(--stamp-soft);
  color: var(--stamp);
}

.chip--info {
  background: var(--info-soft);
  color: var(--info);
}

.chip--warn {
  background: var(--warn-soft);
  color: var(--warn-text);
}

.chip--warn .chip-icon {
  color: var(--warn);
}

.chip--ok {
  background: var(--ok-soft);
  color: var(--ok);
}

.chip--block {
  background: var(--block-soft);
  color: var(--block);
}

.chip--neutral {
  background: var(--soft);
  color: var(--muted);
}
</style>
