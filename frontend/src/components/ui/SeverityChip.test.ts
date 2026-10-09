import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import SeverityChip, { type Severity } from "./SeverityChip.vue";

describe("SeverityChip", () => {
  it.each<[Severity, string, string]>([
    ["block", "Block", "severity--block"],
    ["warn", "Warning", "severity--warn"],
    ["info", "Info", "severity--info"],
    ["fatal", "Error", "severity--block"],
    ["warning", "Warning", "severity--warn"],
    ["information", "Info", "severity--info"],
  ])("shows %s as %s with an icon", (severity, label, tone) => {
    const wrapper = mount(SeverityChip, { props: { severity } });
    expect(wrapper.text()).toBe(label);
    expect(wrapper.classes()).toContain(tone);
    expect(wrapper.get("svg").attributes("aria-hidden")).toBe("true");
  });

  it("labels the icon when it stands alone", () => {
    const wrapper = mount(SeverityChip, {
      props: { severity: "block", iconOnly: true },
    });
    const svg = wrapper.get("svg");
    expect(svg.attributes("role")).toBe("img");
    expect(svg.attributes("aria-label")).toBe("Block");
  });
});
