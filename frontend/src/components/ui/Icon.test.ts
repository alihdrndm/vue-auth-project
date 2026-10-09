import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import Icon from "./Icon.vue";
import { ICONS } from "./icons";

describe("Icon", () => {
  it("is hidden from assistive tech without a label", () => {
    const wrapper = mount(Icon, { props: { name: "inbox" } });
    const svg = wrapper.get("svg");
    expect(svg.attributes("aria-hidden")).toBe("true");
    expect(svg.attributes("role")).toBeUndefined();
  });

  it("is an image with a name when labelled", () => {
    const wrapper = mount(Icon, { props: { name: "octagon", label: "Block" } });
    const svg = wrapper.get("svg");
    expect(svg.attributes("role")).toBe("img");
    expect(svg.attributes("aria-label")).toBe("Block");
    expect(svg.attributes("aria-hidden")).toBeUndefined();
  });

  it("draws a 1.5 px stroke at the requested size", () => {
    const wrapper = mount(Icon, { props: { name: "search", size: 20 } });
    const svg = wrapper.get("svg");
    expect(svg.attributes("width")).toBe("20");
    expect(Number(svg.attributes("stroke-width"))).toBeCloseTo(1.5 * (24 / 20));
  });

  it("spins on request", () => {
    const wrapper = mount(Icon, { props: { name: "loader", spin: true } });
    expect(wrapper.get("svg").classes()).toContain("icon--spin");
  });

  it("maps every design icon name", () => {
    expect(Object.keys(ICONS)).toHaveLength(41);
    for (const name of Object.keys(ICONS) as (keyof typeof ICONS)[]) {
      const wrapper = mount(Icon, { props: { name } });
      expect(wrapper.find("svg").exists()).toBe(true);
    }
  });
});
