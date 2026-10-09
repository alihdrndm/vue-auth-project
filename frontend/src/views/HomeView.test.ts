import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia, type Pinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter, type Router } from "vue-router";

import { resetCsrfToken } from "../api/client";
import { SANDBOX_EXPIRED_MESSAGE, useSessionStore } from "../stores/session";
import {
  json,
  mockFetch,
  problem,
  sessionBody,
  setCsrfCookie,
} from "../testing/http";
import HomeView from "./HomeView.vue";

let pinia: Pinia;
let router: Router;
const Stub = { template: "<p>stub</p>" };

beforeEach(async () => {
  pinia = createPinia();
  setActivePinia(pinia);
  resetCsrfToken();
  setCsrfCookie("token");
  router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/", name: "home", component: HomeView },
      { path: "/sign-in", name: "sign-in", component: Stub },
      { path: "/accuracy", name: "accuracy-public", component: Stub },
      { path: "/app/inbox", name: "inbox", component: Stub },
    ],
  });
  await router.push("/");
  await router.isReady();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function mountHome() {
  return mount(HomeView, { global: { plugins: [pinia, router] } });
}

describe("HomeView", () => {
  it("opens the sandbox and goes to the inbox", async () => {
    const calls = mockFetch(() =>
      json(
        201,
        sessionBody({ kind: "sandbox", expires_at: "2099-01-01T00:00:00Z" }),
      ),
    );
    const wrapper = mountHome();

    await wrapper.get("button").trigger("click");
    await flushPromises();

    expect(calls.map((call) => [call.method, call.path])).toEqual([
      ["POST", "/api/v1/sandbox"],
    ]);
    expect(router.currentRoute.value.name).toBe("inbox");
    expect(useSessionStore().isSandbox).toBe(true);
  });

  it("shows the limit message on 429 and stays", async () => {
    mockFetch(() =>
      problem(
        429,
        "SANDBOX_LIMIT",
        "Too many sandboxes were opened recently. Please try again later.",
      ),
    );
    const wrapper = mountHome();

    await wrapper.get("button").trigger("click");
    await flushPromises();

    expect(router.currentRoute.value.name).toBe("home");
    expect(wrapper.get('[role="alert"]').text()).toBe(
      "Too many sandboxes were opened recently. Please try again later.",
    );
    expect(wrapper.get("button").text()).toBe("Open the sandbox");
  });

  it("shows the expired-sandbox notice once", () => {
    useSessionStore().handleAuthFailure("SANDBOX_EXPIRED");

    const first = mountHome();
    expect(first.get('[role="status"]').text()).toBe(SANDBOX_EXPIRED_MESSAGE);

    const second = mountHome();
    expect(second.find('[role="status"]').exists()).toBe(false);
  });

  it("links to sign-in and the public accuracy page", () => {
    const wrapper = mountHome();
    const hrefs = wrapper.findAll("a").map((link) => link.attributes("href"));
    expect(hrefs).toContain("/sign-in");
    expect(hrefs).toContain("/accuracy");
    expect(hrefs).toContain("https://github.com/alihdrndm/eingang");
  });

  it("shows the limit message next to the button that was pressed", async () => {
    mockFetch(() =>
      problem(429, "SANDBOX_LIMIT", "Too many sandboxes were opened today."),
    );
    const wrapper = mountHome();
    const buttons = wrapper
      .findAll("button")
      .filter((button) => button.text().includes("Open the sandbox"));
    await buttons[buttons.length - 1]?.trigger("click");
    await flushPromises();
    const errors = wrapper.findAll(".error").map((error) => error.text());
    expect(errors).toEqual(["", "Too many sandboxes were opened today."]);
  });
});
