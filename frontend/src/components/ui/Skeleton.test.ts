import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import Skeleton, { SKELETON_DELAY_MS } from "./Skeleton.vue";

describe("Skeleton", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("is a busy region in the layout of the content", () => {
    const wrapper = mount(Skeleton, {
      props: {
        label: "Loading invoices",
        rows: 3,
        header: true,
        columns: [
          { track: "16px", shape: "box" },
          { track: "minmax(0, 1fr)" },
          { track: "120px", shape: "chip" },
        ],
      },
    });
    expect(wrapper.attributes("aria-busy")).toBe("true");
    expect(wrapper.attributes("aria-label")).toBe("Loading invoices");
    expect(wrapper.find(".skeleton-header").exists()).toBe(true);
    expect(wrapper.findAll(".skeleton-row")).toHaveLength(3);
    expect(wrapper.findAll(".bar--chip")).toHaveLength(3);
    expect(wrapper.findAll(".bar--box")).toHaveLength(3);
  });

  it("appears only after 300 ms", async () => {
    const wrapper = mount(Skeleton, {
      props: { label: "Loading", columns: [{ track: "1fr" }] },
    });
    expect(wrapper.classes()).not.toContain("is-visible");
    vi.advanceTimersByTime(SKELETON_DELAY_MS);
    await nextTick();
    expect(wrapper.classes()).toContain("is-visible");
  });
});
