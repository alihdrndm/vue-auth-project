import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import StatusChip, { type DocumentStatus } from "./StatusChip.vue";

const CASES: [DocumentStatus, string, string][] = [
  ["received", "Received", "chip--stamp"],
  ["processing", "Processing", "chip--info"],
  ["needs_review", "Needs review", "chip--warn"],
  ["awaiting_approval", "Awaiting approval", "chip--stamp"],
  ["approved", "Approved", "chip--ok"],
  ["rejected", "Rejected", "chip--block"],
  ["exported", "Exported", "chip--neutral"],
  ["failed", "Failed", "chip--block"],
];

describe("StatusChip", () => {
  it.each(CASES)(
    "shows %s as the word %s with an icon and its colour",
    (status, label, tone) => {
      const wrapper = mount(StatusChip, { props: { status } });
      expect(wrapper.text()).toBe(label);
      expect(wrapper.classes()).toContain(tone);
      // Colour is never the only signal: a word and an icon.
      expect(wrapper.find("svg").exists()).toBe(true);
      expect(wrapper.get("svg").attributes("aria-hidden")).toBe("true");
    },
  );

  it("spins the icon only while processing", () => {
    expect(
      mount(StatusChip, { props: { status: "processing" } })
        .get("svg")
        .classes(),
    ).toContain("icon--spin");
    expect(
      mount(StatusChip, { props: { status: "received" } })
        .get("svg")
        .classes(),
    ).not.toContain("icon--spin");
  });

  it("uses distinct icons for every status", () => {
    const icons = CASES.map(([status]) =>
      mount(StatusChip, { props: { status } }).get("svg").classes().join(" "),
    );
    expect(new Set(icons).size).toBe(CASES.length);
  });
});
