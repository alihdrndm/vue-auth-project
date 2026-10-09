import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import Badge from "./Badge.vue";

describe("Badge", () => {
  it("shows a count", () => {
    const wrapper = mount(Badge, { slots: { default: "12" } });
    expect(wrapper.text()).toBe("12");
    expect(wrapper.classes()).toContain("badge--count");
  });

  it("marks the selected count", () => {
    const wrapper = mount(Badge, {
      props: { selected: true },
      slots: { default: "7" },
    });
    expect(wrapper.classes()).toContain("badge--selected");
  });

  it("says Sample by default for illustrative numbers", () => {
    const wrapper = mount(Badge, { props: { variant: "sample" } });
    expect(wrapper.text()).toBe("Sample");
  });

  it("shows the overdue marker with an icon", () => {
    const wrapper = mount(Badge, { props: { variant: "overdue" } });
    expect(wrapper.text()).toBe("Overdue");
    expect(wrapper.find("svg").exists()).toBe(true);
  });

  it("shows a label", () => {
    const wrapper = mount(Badge, {
      props: { variant: "label" },
      slots: { default: "You" },
    });
    expect(wrapper.text()).toBe("You");
    expect(wrapper.classes()).toContain("badge--label");
  });
});
