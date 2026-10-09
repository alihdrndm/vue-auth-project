<script setup lang="ts">
// ValidationChip (design): the validation verdict as text plus icon, never colour alone.
import Icon from "../../components/ui/Icon.vue";
import type { ValidationLook } from "./validation";

defineProps<{ look: ValidationLook }>();
</script>

<template>
  <span class="chip" :class="`chip--${look.tone}`">
    <Icon class="chip-icon" :name="look.icon" :size="14" />{{ look.label }}
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

.chip--ok {
  background: var(--ok-soft);
  color: var(--ok);
}

.chip--warn {
  background: var(--warn-soft);
  color: var(--warn-text);
}

.chip--warn .chip-icon {
  color: var(--warn);
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
