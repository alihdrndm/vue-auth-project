import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import App from "./App.vue";
import { routes } from "./router";

describe("router", () => {
  it("renders the placeholder heading on the home route", async () => {
    const router = createRouter({ history: createMemoryHistory(), routes });
    await router.push("/");
    await router.isReady();

    const wrapper = mount(App, { global: { plugins: [router] } });
    await flushPromises();

    expect(wrapper.get("h1").text()).toBe("Eingang");
  });
});
