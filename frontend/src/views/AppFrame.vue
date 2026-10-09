<script setup lang="ts">
// The signed-in frame: the designed app shell around every /app page, the sandbox
// banner (HANDOFF: on every app page in a sandbox), nav counts from /stats, and the one
// toast region of the app.
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { computed } from "vue";
import { useRouter } from "vue-router";

import { api, unwrap } from "../api/client";
import { queryKeys } from "../api/query";
import AppShell from "../components/shell/AppShell.vue";
import Button from "../components/ui/Button.vue";
import Toast from "../components/ui/Toast.vue";
import { useSessionStore } from "../stores/session";

const session = useSessionStore();
const router = useRouter();
const queryClient = useQueryClient();

const stats = useQuery({
  queryKey: queryKeys.stats(),
  queryFn: async () => unwrap(await api.GET("/api/v1/stats")),
  refetchInterval: 30_000,
});

const counts = computed(() => {
  const byStatus = stats.data.value?.by_status as
    Record<string, number> | undefined;
  if (!byStatus) return {};
  return {
    inbox: byStatus.needs_review ?? 0,
    approvals: stats.data.value?.awaiting_my_approval ?? 0,
  };
});

function search(query: string): void {
  const q = query.trim();
  void router.push({ name: "inbox", query: q ? { q, tab: "all" } : {} });
}

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
  <AppShell
    :org-name="session.me?.organization.name ?? ''"
    :sandbox-hours-left="
      session.isSandbox ? (session.hoursLeft ?? undefined) : undefined
    "
    :counts="counts"
    @search="search"
  >
    <template #banner>
      <p v-if="session.isSandbox" class="sandbox-banner" role="note">
        Sandbox · deleted in {{ session.hoursLeft }} h · sample data, nothing is
        real
      </p>
    </template>
    <template #user-menu>
      <Button variant="ghost" size="sm" @click="signOut">Sign out</Button>
    </template>
    <RouterView />
  </AppShell>
  <Toast />
</template>

<style scoped>
.sandbox-banner {
  margin: 0;
  padding: var(--space-8) var(--space-16);
  background: var(--stamp-soft);
  color: var(--ink);
  font-size: var(--fs-13);
  text-align: center;
}
</style>
