<script setup lang="ts">
// The Checks section of the review screen; built out in the next commits.
import type { components } from "../../api/schema";

defineProps<{ document: components["schemas"]["DocumentDetail"] }>();
defineEmits<{ resolved: [] }>();
</script>

<template>
  <section aria-labelledby="checks-title">
    <h2 id="checks-title">Checks</h2>
  </section>
</template>
