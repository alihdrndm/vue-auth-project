<script setup lang="ts">
// Accuracy for visitors (HANDOFF `/accuracy`, design ?screen=accuracy-public): the same results
// as in the app, without the app shell, under a small header with the way into the sandbox.
import { ref } from "vue";
import { useRouter } from "vue-router";

import { ApiError } from "../api/client";
import Button from "../components/ui/Button.vue";
import Stamp from "../components/ui/Stamp.vue";
import AccuracyReport from "../features/accuracy/AccuracyReport.vue";
import { useSessionStore } from "../stores/session";

const session = useSessionStore();
const router = useRouter();

const opening = ref(false);
const error = ref<string | null>(null);

async function openSandbox(): Promise<void> {
  if (opening.value) return;
  opening.value = true;
  error.value = null;
  try {
    await session.openSandbox();
    await router.push({ name: "inbox" });
  } catch (caught) {
    error.value =
      caught instanceof ApiError
        ? caught.detail || caught.title
        : "The sandbox could not be opened. Check your connection and try again.";
  } finally {
    opening.value = false;
  }
}
</script>

<template>
  <div class="public">
    <header class="top">
      <RouterLink to="/" class="brand" aria-label="Eingang, home">
        <Stamp size="mark" :mark-size="28" />
        <span>Eingang</span>
      </RouterLink>
      <Button variant="primary" :loading="opening" @click="openSandbox">{{
        opening ? "Opening…" : "Open the sandbox"
      }}</Button>
    </header>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <main class="main" aria-labelledby="accuracy-title">
      <AccuracyReport />
    </main>
  </div>
</template>

<style scoped>
.public {
  min-height: 100vh;
  background: var(--paper);
}

.top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-16);
  max-width: 1112px;
  margin: 0 auto;
  padding: var(--space-16);
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: var(--space-8);
  color: var(--ink);
  font: 700 var(--fs-17) / 1 var(--font-head);
  letter-spacing: var(--tracking-head);
  text-decoration: none;
}

.error {
  max-width: 1080px;
  margin: 0 auto;
  padding: 0 var(--space-16);
  color: var(--block);
  font-size: var(--fs-13);
}

.main {
  display: grid;
  justify-content: center;
  grid-template-columns: minmax(0, 1080px);
  padding: var(--space-16) var(--space-16) var(--space-72);
}
</style>
