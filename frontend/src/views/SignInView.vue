<script setup lang="ts">
import Icon from "../components/ui/Icon.vue";
import { computed, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { ApiError } from "../api/client";
import { useSessionStore } from "../stores/session";

const session = useSessionStore();
const router = useRouter();
const route = useRoute();

const email = ref("");
const password = ref("");
const showPassword = ref(false);
const busy = ref(false);
const fieldErrors = reactive<{ email: string | null; password: string | null }>(
  {
    email: null,
    password: null,
  },
);
const formError = ref<string | null>(null);

/** Back to the app page the visitor wanted, never to another site. */
const target = computed(() => {
  const redirect = route.query.redirect;
  return typeof redirect === "string" && redirect.startsWith("/app/")
    ? redirect
    : "/app/inbox";
});

function validate(): boolean {
  fieldErrors.email = email.value.trim() ? null : "Enter your email address.";
  fieldErrors.password = password.value ? null : "Enter your password.";
  return !fieldErrors.email && !fieldErrors.password;
}

function showProblem(error: unknown): void {
  if (!(error instanceof ApiError)) {
    formError.value = "Sign-in failed. Check your connection and try again.";
    return;
  }
  if (error.code === "VALIDATION_FAILED" && error.errors.length > 0) {
    for (const entry of error.errors) {
      if (entry.path === "email" || entry.path === "password")
        fieldErrors[entry.path] = entry.message;
      else formError.value = entry.message;
    }
    return;
  }
  formError.value = error.detail || error.title;
}

async function submit(): Promise<void> {
  if (busy.value) return;
  formError.value = null;
  if (!validate()) return;
  busy.value = true;
  try {
    await session.signIn(email.value.trim(), password.value);
    await router.push(target.value);
  } catch (error) {
    showProblem(error);
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <main class="sign-in">
    <div class="column">
      <div class="brand">
        <span class="mark" aria-hidden="true"><span>E</span></span>
        <span class="wordmark">Eingang</span>
      </div>

      <form class="card" novalidate :aria-busy="busy" @submit.prevent="submit">
        <h1>Sign in</h1>

        <p class="form-error" role="alert" aria-live="assertive">
          <template v-if="formError">
            <Icon name="octagon" :size="14" />{{ formError }}
          </template>
        </p>

        <div class="field">
          <label for="sign-in-email">Email</label>
          <input
            id="sign-in-email"
            v-model="email"
            type="email"
            name="email"
            autocomplete="username"
            placeholder="anna.weber@holzwerk-brandt.de"
            :aria-invalid="fieldErrors.email ? 'true' : 'false'"
            :aria-describedby="
              fieldErrors.email ? 'sign-in-email-error' : undefined
            "
          />
          <span
            v-if="fieldErrors.email"
            id="sign-in-email-error"
            class="field-error"
            role="alert"
          >
            <Icon name="octagon" :size="14" />{{ fieldErrors.email }}
          </span>
        </div>

        <div class="field">
          <label for="sign-in-password">Password</label>
          <span class="password">
            <input
              id="sign-in-password"
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              name="password"
              autocomplete="current-password"
              :aria-invalid="fieldErrors.password ? 'true' : 'false'"
              :aria-describedby="
                fieldErrors.password ? 'sign-in-password-error' : undefined
              "
            />
            <button
              type="button"
              class="reveal"
              :aria-label="showPassword ? 'Hide password' : 'Show password'"
              :title="showPassword ? 'Hide password' : 'Show password'"
              :aria-pressed="showPassword"
              @click="showPassword = !showPassword"
            >
              <Icon v-if="showPassword" name="eye-off" :size="16" />
              <Icon v-else name="eye" :size="16" />
            </button>
          </span>
          <span
            v-if="fieldErrors.password"
            id="sign-in-password-error"
            class="field-error"
            role="alert"
          >
            <Icon name="octagon" :size="14" />{{ fieldErrors.password }}
          </span>
        </div>

        <button type="submit" class="submit" :disabled="busy">
          <template v-if="busy">
            <Icon name="loader" :size="16" spin />Signing in…
          </template>
          <template v-else>Sign in</template>
        </button>
      </form>

      <div class="alternative">
        <RouterLink :to="{ name: 'home' }" class="sandbox-link"
          >Open the sandbox instead</RouterLink
        >
        <p>Free and open source. No sign-up for the sandbox.</p>
      </div>
    </div>
  </main>
</template>

<style scoped>
.sign-in {
  display: grid;
  place-items: center;
  min-height: 100vh;
  padding: var(--space-40) var(--space-16);
  background: var(--bar);
  color: var(--text);
  font-family: var(--font-sans);
  font-size: var(--fs-14);
  line-height: 1.45;
}

.column {
  display: grid;
  gap: var(--space-24);
  width: 400px;
  max-width: 100%;
}

.brand {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-12);
}

.mark {
  display: grid;
  place-items: center;
  width: 1em;
  height: 1em;
  border: 0.0625em solid var(--stamp);
  border-radius: 0.15em;
  outline: 0.025em solid var(--stamp);
  outline-offset: -0.175em;
  background: var(--win);
  color: var(--stamp);
  font-family: var(--font-stamp);
  font-size: 40px;
  font-weight: 700;
  line-height: 1;
}

.mark span {
  font-size: 0.55em;
}

.wordmark {
  font-family: var(--font-head);
  font-size: 28px;
  font-weight: 700;
  line-height: 1;
  letter-spacing: -0.025em;
  color: var(--ink);
}

.card {
  display: grid;
  gap: var(--space-20);
  padding: var(--space-32);
  border: 1px solid var(--line);
  border-radius: var(--r-lg);
  background: var(--win);
}

h1 {
  margin: 0;
  font-family: var(--font-head);
  font-size: var(--fs-21);
  font-weight: 700;
  line-height: 1.2;
  letter-spacing: -0.025em;
  color: var(--ink);
}

.field {
  display: grid;
  gap: var(--space-4);
}

label {
  font-size: var(--fs-13);
  font-weight: 500;
  color: var(--ink);
}

input {
  width: 100%;
  height: var(--size-lg);
  padding: 0 var(--space-12);
  border: 1px solid var(--line-strong);
  border-radius: var(--r-sm);
  background: var(--win);
  color: var(--ink);
  font: inherit;
  font-size: var(--fs-16);
}

input:hover {
  border-color: var(--muted);
}

input:focus-visible {
  border-color: var(--ink);
  outline: 2.5px solid var(--focus);
  outline-offset: 2px;
}

input[aria-invalid="true"] {
  border-color: var(--block);
}

.password {
  position: relative;
  display: flex;
}

.password input {
  padding-right: var(--space-56);
}

.reveal {
  position: absolute;
  top: var(--space-4);
  right: var(--space-4);
  display: grid;
  place-items: center;
  width: var(--size-row-header);
  height: var(--size-row-header);
  border: 0;
  border-radius: var(--r-sm);
  background: transparent;
  color: var(--text);
  cursor: pointer;
}

.reveal:hover {
  background: var(--soft);
}

.field-error,
.form-error {
  display: flex;
  gap: var(--space-4);
  align-items: center;
  margin: 0;
  font-size: var(--fs-12);
  color: var(--block);
}

.form-error:empty {
  margin-top: calc(-1 * var(--space-20));
}

.submit {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-8);
  height: var(--size-lg);
  border: 1px solid var(--ink);
  border-radius: var(--r-sm);
  background: var(--ink);
  color: var(--win);
  font: inherit;
  font-size: var(--fs-16);
  font-weight: 500;
  cursor: pointer;
}

.submit:hover:not(:disabled) {
  background: var(--text);
}

.submit:disabled {
  cursor: progress;
}

.alternative {
  display: grid;
  gap: var(--space-12);
  text-align: center;
}

.alternative p {
  margin: 0;
  font-size: var(--fs-13);
  color: var(--muted);
}

.sandbox-link {
  display: flex;
  align-items: center;
  justify-content: center;
  height: var(--size-lg);
  border: 1px solid var(--line-strong);
  border-radius: var(--r-sm);
  background: var(--win);
  color: var(--ink);
  font-size: var(--fs-16);
  font-weight: 500;
  text-decoration: none;
}

.sandbox-link:hover {
  background: var(--soft);
}

:focus-visible {
  outline: 2.5px solid var(--focus);
  outline-offset: 2px;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .spin {
    animation: none;
  }
}
</style>
