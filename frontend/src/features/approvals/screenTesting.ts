// Test helpers for the M8 screens: a router with the app's named routes as stubs, Pinia with a
// signed-in session, a fresh query client without retries, and a button finder.
import { QueryClient, VueQueryPlugin } from "@tanstack/vue-query";
import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { type Component, h } from "vue";
import {
  createMemoryHistory,
  createRouter,
  type Router,
  RouterView,
} from "vue-router";

import { resetCsrfToken } from "../../api/client";
import type { components } from "../../api/schema";
import Toast from "../../components/ui/Toast.vue";
import { useSessionStore } from "../../stores/session";
import { sessionBody, setCsrfCookie } from "../../testing/http";

type Role = components["schemas"]["RoleEnum"];
type SessionOrganization = components["schemas"]["SessionOrganization"];

const Stub = { render: () => h("p", "stub") };

const NAMES: [string, string][] = [
  ["/app/inbox", "inbox"],
  ["/app/invoices/:id", "invoice"],
  ["/app/approvals", "approvals"],
  ["/app/suppliers", "suppliers"],
  ["/app/suppliers/:id", "supplier"],
  ["/app/exports", "exports"],
  ["/app/accuracy", "accuracy"],
  ["/app/settings", "settings"],
  ["/accuracy", "accuracy-public"],
  ["/", "home"],
];

export interface ScreenOptions {
  role?: Role;
  organization?: Partial<SessionOrganization>;
}

export interface Screen {
  wrapper: VueWrapper;
  router: Router;
  queryClient: QueryClient;
}

/** Mounts `view` at `path` (its route named `name`), with the toast region next to it. */
export async function mountScreen(
  view: Component,
  name: string,
  path: string,
  options: ScreenOptions = {},
): Promise<Screen> {
  const pinia = createPinia();
  setActivePinia(pinia);
  const session = sessionBody(options.organization);
  useSessionStore().me = { ...session, role: options.role ?? "accountant" };
  useSessionStore().loaded = true;
  resetCsrfToken();
  setCsrfCookie("token");

  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const router = createRouter({
    history: createMemoryHistory(),
    routes: NAMES.map(([routePath, routeName]) => ({
      path: routePath,
      name: routeName,
      component: routeName === name ? view : Stub,
      props: routePath.includes(":id"),
    })),
  });
  await router.push(path);
  await router.isReady();

  const App = { render: () => [h(RouterView), h(Toast)] };
  const wrapper = mount(App, {
    attachTo: document.body,
    global: { plugins: [pinia, router, [VueQueryPlugin, { queryClient }]] },
  });
  await flushPromises();
  return { wrapper, router, queryClient };
}

/** The button whose visible text is `label` (screen-reader-only text ignored). */
export function buttonByText(wrapper: VueWrapper, label: string) {
  const found = wrapper.findAll("button").find((item) => {
    const clone = item.element.cloneNode(true) as HTMLElement;
    clone.querySelectorAll(".sr-only").forEach((node) => node.remove());
    return clone.textContent?.trim() === label;
  });
  if (!found) throw new Error(`No button "${label}"`);
  return found;
}
