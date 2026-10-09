<!-- eslint-disable vue/multi-word-component-names -- named after the design system component -->
<script setup lang="ts">
import { computed } from "vue";

import { ICONS, type IconName } from "./icons";

const props = withDefaults(
  defineProps<{
    name: IconName;
    /** Rendered size in px: 16 in UI, 14 in chips, 20 in the rail. */
    size?: number;
    /** Spins (pending requests). Static with reduced motion. */
    spin?: boolean;
    /** Gives the icon an accessible name; without it the icon is hidden from assistive tech. */
    label?: string;
  }>(),
  { size: 16, spin: false, label: undefined },
);

const component = computed(() => ICONS[props.name]);
</script>

<template>
  <component
    :is="component"
    class="icon"
    :class="{ 'icon--spin': spin }"
    :size="size"
    :stroke-width="1.5"
    absolute-stroke-width
    focusable="false"
    :role="label ? 'img' : undefined"
    :aria-label="label"
    :aria-hidden="label ? undefined : 'true'"
  />
</template>

<style scoped>
.icon {
  display: inline-block;
  flex: none;
  vertical-align: middle;
}

.icon--spin {
  animation: icon-spin var(--dur-spin) linear infinite;
}

@keyframes icon-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .icon--spin {
    animation: none;
  }
}
</style>
