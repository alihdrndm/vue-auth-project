<script setup lang="ts">
// The IBAN tag: a pill with icon and words, never colour alone (design "IBAN tag").
import { computed } from "vue";

import Icon from "../../components/ui/Icon.vue";
import { IBAN_TAG, type IbanStatus } from "./iban";

const props = withDefaults(
  defineProps<{ status: IbanStatus; outlined?: boolean }>(),
  { outlined: false },
);

const look = computed(() => IBAN_TAG[props.status]);
</script>

<template>
  <span
    class="tag"
    :class="[`tag--${look.tone}`, { 'tag--outlined': outlined }]"
    ><Icon :name="look.icon" :size="14" />{{ look.label }}</span
  >
</template>

<style scoped>
.tag {
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

.tag--neutral {
  background: var(--soft);
  color: var(--muted-strong);
}

.tag--ok {
  background: var(--ok-soft);
  color: var(--ok);
}

.tag--block {
  background: var(--block-soft);
  color: var(--block);
}

.tag--outlined {
  border: 1px solid currentColor;
  background: var(--win);
}
</style>
