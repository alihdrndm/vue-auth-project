<script setup lang="ts">
import Button from "./Button.vue";
import Icon from "./Icon.vue";

withDefaults(
  defineProps<{
    /** The problem's `title` from the API. */
    title: string;
    /** The problem's `detail` from the API. */
    detail?: string;
    /** Shows a spinner on "Try again" while the retry runs. */
    retrying?: boolean;
    level?: 2 | 3 | 4;
  }>(),
  { detail: undefined, retrying: false, level: 2 },
);

const emit = defineEmits<{ retry: [] }>();
</script>

<template>
  <div class="state" role="alert">
    <span class="state-disc"><Icon name="circle-alert" :size="20" /></span>
    <component :is="`h${level}`" class="state-title">{{ title }}</component>
    <p v-if="detail" class="state-body">{{ detail }}</p>
    <Button
      :icon="retrying ? undefined : 'refresh'"
      :loading="retrying"
      @click="emit('retry')"
      >Try again</Button
    >
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
  background: var(--block-soft);
  color: var(--block);
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
