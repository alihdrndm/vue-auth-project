<script lang="ts">
import type { components } from "../../api/schema";
import type { IconName } from "./icons";

export type CheckSeverity = components["schemas"]["CheckSeverityEnum"];
export type IssueSeverity = components["schemas"]["IssueSeverityEnum"];
export type Severity = CheckSeverity | IssueSeverity;

interface SeverityLook {
  label: string;
  icon: IconName;
  tone: "block" | "warn" | "info";
}

/** Business checks (block/warn/info) and validation issues (fatal/warning/information). */
export const SEVERITY_LOOK: Record<Severity, SeverityLook> = {
  block: { label: "Block", icon: "octagon", tone: "block" },
  warn: { label: "Warning", icon: "triangle", tone: "warn" },
  info: { label: "Info", icon: "info", tone: "info" },
  fatal: { label: "Error", icon: "octagon", tone: "block" },
  warning: { label: "Warning", icon: "triangle", tone: "warn" },
  information: { label: "Info", icon: "info", tone: "info" },
};
</script>

<script setup lang="ts">
import { computed } from "vue";

import Icon from "./Icon.vue";

const props = withDefaults(
  defineProps<{
    severity: Severity;
    /** Icon only, labelled for assistive tech. Use only where a text label sits in the same row. */
    iconOnly?: boolean;
  }>(),
  { iconOnly: false },
);

const look = computed(() => SEVERITY_LOOK[props.severity]);
</script>

<template>
  <Icon
    v-if="iconOnly"
    class="severity-icon"
    :class="`severity--${look.tone}`"
    :name="look.icon"
    :size="16"
    :label="look.label"
  />
  <span v-else class="severity" :class="`severity--${look.tone}`">
    <Icon class="severity-icon" :name="look.icon" :size="16" />{{ look.label }}
  </span>
</template>

<style scoped>
.severity {
  display: inline-flex;
  align-items: center;
  gap: var(--space-4);
  font-size: var(--fs-13);
  font-weight: 500;
}

.severity--block {
  color: var(--block);
}

.severity--warn {
  color: var(--warn-text);
}

.severity--warn.severity-icon,
.severity--warn .severity-icon {
  color: var(--warn);
}

.severity--info {
  color: var(--info);
}
</style>
