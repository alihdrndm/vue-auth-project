import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import Tabs, { type TabItem } from "./Tabs.vue";

const ITEMS: TabItem[] = [
  { key: "needs_review", label: "Needs review", count: 7 },
  { key: "awaiting", label: "Awaiting approval", count: 3 },
  { key: "locked", label: "XML", disabledReason: "This PDF has no XML inside" },
  { key: "all", label: "All", count: 0 },
];

function mountTabs(selected = "needs_review") {
  const wrapper = mount(Tabs, {
    attachTo: document.body,
    props: {
      label: "Inbox filters",
      items: ITEMS,
      modelValue: selected,
      "onUpdate:modelValue": (value: string) =>
        wrapper.setProps({ modelValue: value }),
    },
    slots: {
      default: `<template #default="{ selected }">Panel {{ selected }}</template>`,
    },
  });
  return wrapper;
}

describe("Tabs", () => {
  it("follows the WAI-ARIA tabs pattern", () => {
    const wrapper = mountTabs();
    const list = wrapper.get('[role="tablist"]');
    expect(list.attributes("aria-label")).toBe("Inbox filters");
    const tabs = wrapper.findAll('[role="tab"]');
    expect(tabs).toHaveLength(4);
    expect(tabs[0]?.attributes("aria-selected")).toBe("true");
    expect(tabs[0]?.attributes("tabindex")).toBe("0");
    expect(tabs[1]?.attributes("aria-selected")).toBe("false");
    expect(tabs[1]?.attributes("tabindex")).toBe("-1");
    const panel = wrapper.get('[role="tabpanel"]');
    expect(panel.attributes("aria-labelledby")).toBe(tabs[0]?.attributes("id"));
    expect(tabs[0]?.attributes("aria-controls")).toBe(panel.attributes("id"));
    expect(panel.text()).toBe("Panel needs_review");
    wrapper.unmount();
  });

  it("shows counts", () => {
    const wrapper = mountTabs();
    expect(wrapper.findAll('[role="tab"]')[0]?.text()).toBe("Needs review7");
    wrapper.unmount();
  });

  it("selects on click and moves with arrow keys, skipping disabled tabs", async () => {
    const wrapper = mountTabs();
    await wrapper.findAll('[role="tab"]')[1]?.trigger("click");
    expect(wrapper.props("modelValue")).toBe("awaiting");

    await wrapper
      .findAll('[role="tab"]')[1]
      ?.trigger("keydown", { key: "ArrowRight" });
    expect(wrapper.props("modelValue")).toBe("all");
    expect(document.activeElement?.textContent).toContain("All");

    await wrapper
      .findAll('[role="tab"]')[3]
      ?.trigger("keydown", { key: "ArrowRight" });
    expect(wrapper.props("modelValue")).toBe("needs_review");

    await wrapper
      .findAll('[role="tab"]')[0]
      ?.trigger("keydown", { key: "ArrowLeft" });
    expect(wrapper.props("modelValue")).toBe("all");

    await wrapper
      .findAll('[role="tab"]')[3]
      ?.trigger("keydown", { key: "Home" });
    expect(wrapper.props("modelValue")).toBe("needs_review");

    await wrapper
      .findAll('[role="tab"]')[0]
      ?.trigger("keydown", { key: "End" });
    expect(wrapper.props("modelValue")).toBe("all");
    wrapper.unmount();
  });

  it("explains a disabled tab and does not select it", async () => {
    const wrapper = mountTabs();
    const locked = wrapper.findAll('[role="tab"]')[2];
    expect(locked?.attributes("aria-disabled")).toBe("true");
    expect(locked?.attributes("title")).toBe("This PDF has no XML inside");
    expect(locked?.text()).toContain("This PDF has no XML inside");
    await locked?.trigger("click");
    expect(wrapper.props("modelValue")).toBe("needs_review");
    wrapper.unmount();
  });
});
