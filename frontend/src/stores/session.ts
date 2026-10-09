import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { api, ApiError, unwrap } from "../api/client";
import type { components } from "../api/schema";

export type Session = components["schemas"]["Session"];
export type Role = components["schemas"]["RoleEnum"];

export const SANDBOX_EXPIRED_MESSAGE =
  "This sandbox has expired. Open a new one.";

const HOUR_MS = 60 * 60 * 1000;

export const useSessionStore = defineStore("session", () => {
  /** The signed-in session, or null when nobody is signed in. */
  const me = ref<Session | null>(null);
  /** True once `/auth/me` has answered (or a sign-in, sign-out or sandbox set the session). */
  const loaded = ref(false);
  /** A one-off message for the homepage, such as the expired-sandbox notice. */
  const notice = ref<string | null>(null);

  let pending: Promise<Session | null> | null = null;

  const role = computed<Role | null>(() => me.value?.role ?? null);
  const isSandbox = computed(() => me.value?.organization.kind === "sandbox");
  /** Whole hours until the sandbox is deleted (rounded up), or null outside a sandbox. */
  const hoursLeft = computed<number | null>(() => {
    const expiresAt = me.value?.organization.expires_at;
    if (!isSandbox.value || !expiresAt) return null;
    const ms = Date.parse(expiresAt) - Date.now();
    return Number.isNaN(ms) ? null : Math.max(0, Math.ceil(ms / HOUR_MS));
  });

  function setSession(session: Session | null): void {
    me.value = session;
    loaded.value = true;
  }

  /** Calls `/auth/me` once. A 401 means "not signed in" (null); other errors are thrown. */
  async function load(): Promise<Session | null> {
    if (loaded.value) return me.value;
    pending ??= (async () => {
      try {
        setSession(unwrap(await api.GET("/api/v1/auth/me")));
      } catch (error) {
        if (!(error instanceof ApiError) || error.status !== 401) throw error;
        if (error.code === "SANDBOX_EXPIRED")
          notice.value = SANDBOX_EXPIRED_MESSAGE;
        setSession(null);
      } finally {
        pending = null;
      }
      return me.value;
    })();
    return pending;
  }

  async function signIn(email: string, password: string): Promise<Session> {
    const session = unwrap(
      await api.POST("/api/v1/auth/login", { body: { email, password } }),
    );
    setSession(session);
    notice.value = null;
    return session;
  }

  async function signOut(): Promise<void> {
    try {
      unwrap(await api.POST("/api/v1/auth/logout"));
    } finally {
      setSession(null);
    }
  }

  /** Opens a new sandbox and signs into it. Throws `ApiError` (`429 SANDBOX_LIMIT`) when refused. */
  async function openSandbox(): Promise<Session> {
    const session = unwrap(await api.POST("/api/v1/sandbox"));
    setSession(session);
    notice.value = null;
    return session;
  }

  /** Forgets the session after the API answered 401, keeping an expired-sandbox notice. */
  function handleAuthFailure(
    code: "NOT_AUTHENTICATED" | "SANDBOX_EXPIRED",
  ): void {
    setSession(null);
    if (code === "SANDBOX_EXPIRED") notice.value = SANDBOX_EXPIRED_MESSAGE;
  }

  /** Returns the notice and clears it, so it is shown once. */
  function takeNotice(): string | null {
    const message = notice.value;
    notice.value = null;
    return message;
  }

  return {
    me,
    loaded,
    notice,
    role,
    isSandbox,
    hoursLeft,
    load,
    signIn,
    signOut,
    openSandbox,
    handleAuthFailure,
    takeNotice,
  };
});
