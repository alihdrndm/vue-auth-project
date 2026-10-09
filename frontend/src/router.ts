import {
  createRouter,
  createWebHistory,
  type RouteLocationRaw,
  type Router,
  type RouterHistory,
  type RouteRecordRaw,
} from "vue-router";

import { setAuthFailureHandler } from "./api/client";
import { useSessionStore } from "./stores/session";

declare module "vue-router" {
  interface RouteMeta {
    /** The route needs a signed-in session (every `/app/*` route). */
    requiresAuth?: boolean;
  }
}

export const routes: RouteRecordRaw[] = [
  { path: "/", name: "home", component: () => import("./views/HomeView.vue") },
  {
    path: "/accuracy",
    name: "accuracy-public",
    component: () => import("./views/AccuracyPublicView.vue"),
  },
  {
    path: "/sign-in",
    name: "sign-in",
    component: () => import("./views/SignInView.vue"),
  },
  {
    path: "/app",
    component: () => import("./views/AppFrame.vue"),
    meta: { requiresAuth: true },
    children: [
      { path: "", redirect: { name: "inbox" } },
      {
        path: "inbox",
        name: "inbox",
        component: () => import("./views/InboxView.vue"),
      },
      {
        path: "invoices/:id",
        name: "invoice",
        component: () => import("./views/InvoiceReviewView.vue"),
        props: true,
      },
      {
        path: "approvals",
        name: "approvals",
        component: () => import("./views/ApprovalsView.vue"),
      },
      {
        path: "suppliers",
        name: "suppliers",
        component: () => import("./views/SuppliersView.vue"),
      },
      {
        path: "suppliers/:id",
        name: "supplier",
        component: () => import("./views/SupplierDetailView.vue"),
        props: true,
      },
      {
        path: "exports",
        name: "exports",
        component: () => import("./views/ExportsView.vue"),
      },
      {
        path: "accuracy",
        name: "accuracy",
        component: () => import("./views/AccuracyView.vue"),
      },
      {
        path: "settings",
        name: "settings",
        component: () => import("./views/SettingsView.vue"),
      },
    ],
  },
  {
    path: "/:pathMatch(.*)*",
    name: "not-found",
    component: () => import("./views/NotFoundView.vue"),
  },
];

/** Where a signed-out visitor of `fullPath` is sent. */
function signInLocation(fullPath: string): RouteLocationRaw {
  return { name: "sign-in", query: { redirect: fullPath } };
}

/** Sends `/app/*` visitors without a session to sign-in, and expired sandboxes to the homepage. */
export function installGuards(router: Router): void {
  router.beforeEach(async (to) => {
    if (!to.matched.some((record) => record.meta.requiresAuth)) return true;
    const session = useSessionStore();
    try {
      if (await session.load()) return true;
    } catch {
      // The API could not answer (network or 5xx): the app cannot run without a session.
      return signInLocation(to.fullPath);
    }
    return session.notice ? { name: "home" } : signInLocation(to.fullPath);
  });

  setAuthFailureHandler((code) => {
    const session = useSessionStore();
    session.handleAuthFailure(code);
    const current = router.currentRoute.value;
    if (!current.path.startsWith("/app")) return;
    void router.push(
      code === "SANDBOX_EXPIRED"
        ? { name: "home" }
        : signInLocation(current.fullPath),
    );
  });
}

export function createAppRouter(
  history: RouterHistory = createWebHistory(),
): Router {
  const router = createRouter({ history, routes });
  installGuards(router);
  return router;
}
