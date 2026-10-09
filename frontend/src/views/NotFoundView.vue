<script setup lang="ts"></script>

<template>
  <main class="not-found">
    <p class="code">404</p>
    <h1>Nothing at this address</h1>
    <p class="lead">
      The link may be old, or the sandbox it pointed to has been deleted.
    </p>
    <RouterLink :to="{ name: 'inbox' }">Go to the Inbox</RouterLink>
  </main>
</template>

<style scoped>
.not-found {
  display: grid;
  gap: 12px;
  justify-items: center;
  padding: 72px 16px;
  text-align: center;
}

.code {
  margin: 0;
  font-family: var(--font-mono);
  color: var(--muted);
}

h1 {
  margin: 0;
  font-family: var(--font-head);
  font-size: 21px;
  color: var(--ink);
}

.lead {
  margin: 0;
  color: var(--muted);
}

a {
  color: var(--stamp);
}
</style>
