<script setup lang="ts">
import Icon from "./Icon.vue";
import type { IconName } from "./icons";

withDefaults(
  defineProps<{
    title: string;
    /** What it means. */
    body?: string;
    icon?: IconName;
    /** Heading level, so the state fits the page outline. */
    level?: 2 | 3 | 4;
  }>(),
  { body: undefined, icon: "inbox", level: 2 },
);

defineSlots<{ action?: () => unknown }>();
</script>

<template>
  <div class="state">
    <span class="state-disc"><Icon :name="icon" :size="20" /></span>
    <component :is="`h${level}`" class="state-title">{{ title }}</component>
    <p v-if="body" class="state-body">{{ body }}</p>
    <slot name="action" />
  </div>
</template>

<style scoped>
.state {
  display: grid;
  justify-items: center;
  align-content: center;
  gap: var(--space-12);
  min-height: var(--size-empty-state);
  padding: var(--space-40) var(--space-24);
  text-align: center;
}

.state-disc {
  display: grid;
  place-items: center;
  width: var(--size-icon-disc);
  height: var(--size-icon-disc);
  border-radius: var(--r-pill);
  background: var(--soft);
  color: var(--ink);
}

.state-title {
  font-family: var(--font-head);
  font-size: var(--fs-16);
  font-weight: 700;
  letter-spacing: var(--tracking-head);
  line-height: var(--lh-app);
  color: var(--ink);
}

.state-body {
  max-width: 44ch;
  font-size: var(--fs-14);
  color: var(--muted);
}
</style>
