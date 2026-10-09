<script setup lang="ts"></script>

<template>
  <section class="not-found">
    <p class="code">404</p>
    <h1>Nothing at this address</h1>
    <p class="lead">
      The link may be old, or the sandbox it pointed to has been deleted.
    </p>
    <RouterLink :to="{ name: 'inbox' }">Go to the Inbox</RouterLink>
  </section>
</template>

<style scoped>
.not-found {
  display: grid;
  gap: var(--space-12);
  justify-items: center;
  padding: var(--space-72) var(--space-16);
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
  font-size: var(--fs-21);
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
