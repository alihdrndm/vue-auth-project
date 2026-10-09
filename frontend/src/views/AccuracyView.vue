<script setup lang="ts">
// Accuracy inside the app (HANDOFF `/app/accuracy`): the published evaluation results.
import AccuracyReport from "../features/accuracy/AccuracyReport.vue";
</script>

<template>
  <section class="accuracy-page" aria-labelledby="accuracy-title">
    <AccuracyReport />
  </section>
</template>

<style scoped>
.accuracy-page {
  min-width: 0;
}
</style>
