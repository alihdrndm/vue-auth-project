<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";

import { ApiError } from "../api/client";
import { useSessionStore } from "../stores/session";

const session = useSessionStore();
const router = useRouter();

/** Shown once, for example after a sandbox expired. */
const notice = ref(session.takeNotice());
const error = ref<string | null>(null);
const opening = ref(false);

async function openSandbox(): Promise<void> {
  if (opening.value) return;
  opening.value = true;
  error.value = null;
  notice.value = null;
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
  <main class="home">
    <h1>Eingang</h1>
    <p v-if="notice" class="notice" role="status">{{ notice }}</p>
    <div class="actions">
      <button
        type="button"
        class="primary"
        :aria-busy="opening"
        :disabled="opening"
        @click="openSandbox"
      >
        {{ opening ? "Opening the sandbox…" : "Open the sandbox" }}
      </button>
      <RouterLink :to="{ name: 'sign-in' }">Sign in</RouterLink>
    </div>
    <p class="error" role="alert" aria-live="assertive">{{ error }}</p>
    <RouterLink :to="{ name: 'accuracy-public' }"
      >How accurate is it? Measured, with the method</RouterLink
    >
  </main>
</template>

<style scoped>
.home {
  display: grid;
  gap: 16px;
  justify-items: start;
  max-width: 640px;
  margin: 0 auto;
  padding: 72px 16px;
  color: var(--text);
}

h1 {
  margin: 0;
  font-family: var(--font-head);
  color: var(--ink);
}

.actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
}

.primary {
  height: 44px;
  padding: 0 20px;
  border: 1px solid var(--ink);
  border-radius: var(--r-sm);
  background: var(--ink);
  color: var(--win);
  font: inherit;
  font-weight: 500;
  cursor: pointer;
}

.notice {
  margin: 0;
  padding: 8px 12px;
  border-radius: var(--r-sm);
  background: var(--info-soft);
  color: var(--ink);
}

.error {
  margin: 0;
  color: var(--block);
}

a {
  color: var(--stamp);
}
</style>
