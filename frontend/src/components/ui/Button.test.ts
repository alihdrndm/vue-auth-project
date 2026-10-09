import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import Button from "./Button.vue";

describe("Button", () => {
  it("renders the variant and size and emits click", async () => {
    const wrapper = mount(Button, {
      props: { variant: "primary", size: "lg" },
      slots: { default: "Approve" },
    });
    const button = wrapper.get("button");
    expect(button.text()).toBe("Approve");
    expect(button.classes()).toEqual(
      expect.arrayContaining(["button--primary", "button--lg"]),
    );
    expect(button.attributes("type")).toBe("button");
    await button.trigger("click");
    expect(wrapper.emitted("click")).toHaveLength(1);
  });

  it("defaults to a secondary md button", () => {
    const wrapper = mount(Button, { slots: { default: "Mark reviewed" } });
    expect(wrapper.get("button").classes()).toEqual(
      expect.arrayContaining(["button--secondary", "button--md"]),
    );
  });

  it("shows a spinner and ignores clicks while loading", async () => {
    const wrapper = mount(Button, {
      props: { loading: true },
      slots: { default: "Approving…" },
    });
    const button = wrapper.get("button");
    expect(button.attributes("aria-busy")).toBe("true");
    expect(button.find("svg.icon--spin").exists()).toBe(true);
    await button.trigger("click");
    expect(wrapper.emitted("click")).toBeUndefined();
  });

  it("is really disabled", async () => {
    const wrapper = mount(Button, {
      props: { disabled: true },
      slots: { default: "Approve" },
    });
    const button = wrapper.get("button");
    expect(button.attributes("disabled")).toBeDefined();
    await button.trigger("click");
    expect(wrapper.emitted("click")).toBeUndefined();
  });

  it("explains why it is disabled", () => {
    const wrapper = mount(Button, {
      props: { disabledReason: "Resolve 1 blocking check first" },
      slots: { default: "Mark reviewed" },
    });
    const button = wrapper.get("button");
    expect(button.attributes("disabled")).toBeDefined();
    const tooltip = wrapper.get('[role="tooltip"]');
    expect(tooltip.text()).toBe("Resolve 1 blocking check first");
    expect(button.attributes("aria-describedby")).toBe(
      tooltip.attributes("id"),
    );
  });

  it("passes attributes such as aria-label to the button", () => {
    const wrapper = mount(Button, {
      attrs: { "aria-label": "Upload invoices" },
      props: { icon: "upload" },
    });
    expect(wrapper.get("button").attributes("aria-label")).toBe(
      "Upload invoices",
    );
  });
});
