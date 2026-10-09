import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ConfidenceBars from "./ConfidenceBars.vue";

describe("ConfidenceBars", () => {
  it.each([
    [1, "Low confidence"],
    [2, "Medium confidence"],
    [3, "High confidence"],
  ] as const)("fills %i bars and says %s", (level, text) => {
    const wrapper = mount(ConfidenceBars, { props: { level } });
    expect(wrapper.findAll("rect.bar--on")).toHaveLength(level);
    expect(wrapper.findAll("rect.bar--off")).toHaveLength(3 - level);
    expect(wrapper.get("svg").attributes("aria-hidden")).toBe("true");
    expect(wrapper.get(".sr-only").text()).toBe(text);
  });

  it("drops the text alternative when a visible word says it", () => {
    const wrapper = mount(ConfidenceBars, { props: { level: 3, label: "" } });
    expect(wrapper.find(".sr-only").exists()).toBe(false);
  });
});
