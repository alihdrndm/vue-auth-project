<script setup lang="ts">
// The Fields section of the review screen; built out in the next commits.
import type { components } from "../../api/schema";

defineProps<{
  document: components["schemas"]["DocumentDetail"];
  /** Whether this user may edit fields now (from allowed_actions `edit_fields`). */
  canEdit: boolean;
}>();
defineEmits<{ "select-field": [name: string]; saved: [] }>();
</script>

<template>
  <section aria-labelledby="fields-title">
    <h2 id="fields-title">Fields</h2>
  </section>
</template>
