import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { defineComponent, h } from "vue";
import { createMemoryHistory, createRouter } from "vue-router";

import AppShell, { navKeyForPath } from "./AppShell.vue";

const Page = defineComponent({ setup: () => () => h("p", "page") });

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      "/app/inbox",
      "/app/invoices/:id",
      "/app/approvals",
      "/app/suppliers",
      "/app/suppliers/:id",
      "/app/exports",
      "/app/accuracy",
      "/app/settings",
    ].map((path) => ({ path, component: Page })),
  });
}

async function mountShell(path: string, props: Record<string, unknown> = {}) {
  const router = makeRouter();
  await router.push(path);
  await router.isReady();
  const wrapper = mount(AppShell, {
    attachTo: document.body,
    props: { orgName: "Holzwerk Brandt GmbH", ...props },
    slots: {
      default: "<h1>Inbox</h1>",
      banner:
        '<div role="status">Sandbox · deleted in 23 h · sample data, nothing is real</div>',
      "user-menu": '<button aria-haspopup="menu">Anna Weber</button>',
    },
    global: { plugins: [router] },
  });
  return { wrapper, router };
}

describe("AppShell", () => {
  it("shows the brand, the organisation, the page and its slots", async () => {
    const { wrapper } = await mountShell("/app/inbox");
    expect(wrapper.get(".wordmark").text()).toBe("Eingang");
    expect(wrapper.get(".org").text()).toBe("Holzwerk Brandt GmbH");
    expect(wrapper.get("main h1").text()).toBe("Inbox");
    expect(wrapper.get("main").text()).toContain(
      "Sandbox · deleted in 23 h · sample data, nothing is real",
    );
    expect(wrapper.get('header button[aria-haspopup="menu"]').text()).toBe(
      "Anna Weber",
    );
    wrapper.unmount();
  });

  it("links every nav item and marks the current page", async () => {
    const { wrapper } = await mountShell("/app/approvals");
    const rail = wrapper.get("nav.rail");
    expect(rail.attributes("aria-label")).toBe("Main");
    const links = rail.findAll("a");
    expect(links.map((a) => a.text())).toEqual([
      "Inbox",
      "Approvals",
      "Suppliers",
      "Exports",
      "Accuracy",
      "Settings",
    ]);
    expect(links.map((a) => a.attributes("href"))).toEqual([
      "/app/inbox",
      "/app/approvals",
      "/app/suppliers",
      "/app/exports",
      "/app/accuracy",
      "/app/settings",
    ]);
    expect(links[1]?.attributes("aria-current")).toBe("page");
    expect(links[0]?.attributes("aria-current")).toBeUndefined();
    wrapper.unmount();
  });

  it("navigates with the router", async () => {
    const { wrapper, router } = await mountShell("/app/inbox");
    await wrapper.get('nav.rail a[href="/app/exports"]').trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.path).toBe("/app/exports");
    expect(
      wrapper.get('nav.rail a[href="/app/exports"]').attributes("aria-current"),
    ).toBe("page");
    wrapper.unmount();
  });

  it("treats invoice and supplier detail pages as their section", () => {
    expect(navKeyForPath("/app/invoices/42")).toBe("inbox");
    expect(navKeyForPath("/app/suppliers/7")).toBe("suppliers");
    expect(navKeyForPath("/app/settings")).toBe("settings");
    expect(navKeyForPath("/somewhere")).toBeUndefined();
  });

  it("shows counts next to nav items", async () => {
    const { wrapper } = await mountShell("/app/inbox", {
      counts: { approvals: 3 },
    });
    expect(
      wrapper.get('nav.rail a[href="/app/approvals"]').get(".badge").text(),
    ).toBe("3");
    expect(
      wrapper.get('nav.rail a[href="/app/inbox"]').find(".badge").exists(),
    ).toBe(false);
    wrapper.unmount();
  });

  it("shows the sandbox countdown only in a sandbox", async () => {
    const plain = await mountShell("/app/inbox");
    expect(plain.wrapper.find(".sandbox-chip").exists()).toBe(false);
    plain.wrapper.unmount();

    const sandbox = await mountShell("/app/inbox", { sandboxHoursLeft: 23 });
    expect(sandbox.wrapper.get(".sandbox-chip").text()).toBe(
      "Sandbox, 23 h left",
    );
    sandbox.wrapper.unmount();
  });

  it("emits search as the user types and clears it", async () => {
    const { wrapper } = await mountShell("/app/inbox");
    const input = wrapper.get('input[aria-label="Search invoices"]');
    await input.setValue("kessler");
    expect(wrapper.emitted("search")?.at(-1)).toEqual(["kessler"]);
    await wrapper.get('button[aria-label="Clear search"]').trigger("click");
    expect(wrapper.emitted("search")?.at(-1)).toEqual([""]);
    wrapper.unmount();
  });

  it("focuses search on / outside text fields, and Esc leaves it", async () => {
    const { wrapper } = await mountShell("/app/inbox");
    const input = wrapper.get<HTMLInputElement>("input[type=search]");
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "/" }));
    expect(document.activeElement).toBe(input.element);

    await input.trigger("keydown", { key: "Escape" });
    expect(document.activeElement).not.toBe(input.element);
    wrapper.unmount();
  });

  it("ignores / while the user is typing in another field", async () => {
    const { wrapper } = await mountShell("/app/inbox");
    const other = document.createElement("textarea");
    document.body.appendChild(other);
    other.focus();
    other.dispatchEvent(
      new KeyboardEvent("keydown", { key: "/", bubbles: true }),
    );
    expect(document.activeElement).toBe(other);
    other.remove();
    wrapper.unmount();
  });

  it("has a phone tab bar whose More opens Accuracy and Settings", async () => {
    const { wrapper } = await mountShell("/app/settings");
    const tabbar = wrapper.get("nav.tabbar");
    expect(tabbar.findAll("a.tabbar-item").map((a) => a.text())).toEqual([
      "Inbox",
      "Approvals",
      "Suppliers",
      "Exports",
    ]);
    const more = tabbar.get("button");
    expect(more.text()).toBe("More");
    expect(more.attributes("aria-expanded")).toBe("false");
    expect(more.classes()).toContain("is-active");

    await more.trigger("click");
    expect(more.attributes("aria-expanded")).toBe("true");
    const menu = wrapper.get(`#${more.attributes("aria-controls")}`);
    expect(menu.findAll("a").map((a) => a.text())).toEqual([
      "Accuracy",
      "Settings",
    ]);

    await menu.trigger("keydown", { key: "Escape" });
    await flushPromises();
    expect(more.attributes("aria-expanded")).toBe("false");
    expect(document.activeElement).toBe(more.element);
    wrapper.unmount();
  });
});
