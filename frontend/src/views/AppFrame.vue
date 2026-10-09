<script setup lang="ts">
import { useQueryClient } from "@tanstack/vue-query";
import { useRouter } from "vue-router";

import { useSessionStore } from "../stores/session";

const session = useSessionStore();
const router = useRouter();
const queryClient = useQueryClient();

const links = [
  { name: "inbox", label: "Inbox" },
  { name: "approvals", label: "Approvals" },
  { name: "suppliers", label: "Suppliers" },
  { name: "exports", label: "Exports" },
  { name: "accuracy", label: "Accuracy" },
  { name: "settings", label: "Settings" },
] as const;

async function signOut(): Promise<void> {
  try {
    await session.signOut();
  } finally {
    queryClient.clear();
    await router.push({ name: "sign-in" });
  }
}
</script>

<template>
  <div class="frame">
    <p v-if="session.isSandbox" class="sandbox-banner">
      Sandbox · deleted in {{ session.hoursLeft }} h · sample data, nothing is
      real
    </p>
    <header class="header">
      <RouterLink :to="{ name: 'inbox' }" class="brand">Eingang</RouterLink>
      <nav aria-label="Main">
        <ul>
          <li v-for="link in links" :key="link.name">
            <RouterLink :to="{ name: link.name }">{{ link.label }}</RouterLink>
          </li>
        </ul>
      </nav>
      <button type="button" class="sign-out" @click="signOut">Sign out</button>
    </header>
    <main class="content">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.frame {
  min-height: 100vh;
  background: var(--bar);
  color: var(--text);
}

.sandbox-banner {
  margin: 0;
  padding: 8px 16px;
  background: var(--stamp);
  color: var(--win);
  font-size: 13px;
  text-align: center;
}

.header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--line);
  background: var(--win);
}

.brand {
  font-family: var(--font-head);
  font-weight: 700;
  color: var(--ink);
  text-decoration: none;
}

nav ul {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin: 0;
  padding: 0;
  list-style: none;
}

nav a {
  color: var(--text);
}

nav a.router-link-active {
  color: var(--ink);
  font-weight: 600;
}

.sign-out {
  margin-left: auto;
}

.content {
  padding: 24px 16px;
}
</style>
