import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import FormatChip, { formatIcon, ZUGFERD_TOOLTIP } from "./FormatChip.vue";

describe("FormatChip", () => {
  it("shows the format label with an icon", () => {
    const wrapper = mount(FormatChip, { props: { label: "XRechnung · UBL" } });
    expect(wrapper.text()).toBe("XRechnung · UBL");
    expect(wrapper.find("svg").exists()).toBe(true);
    expect(wrapper.attributes("title")).toBeUndefined();
  });

  it("explains ZUGFeRD in a tooltip", () => {
    const wrapper = mount(FormatChip, {
      props: { label: "ZUGFeRD · EN 16931" },
    });
    expect(wrapper.attributes("title")).toBe(ZUGFERD_TOOLTIP);
  });

  it("marks credit notes", () => {
    const wrapper = mount(FormatChip, {
      props: { label: "XRechnung · UBL", creditNote: true },
    });
    expect(wrapper.text()).toBe("XRechnung · UBL · credit note");
  });

  it("picks the icon by kind of file", () => {
    expect(formatIcon("XRechnung · CII")).toBe("file-code");
    expect(formatIcon("EN 16931 · UBL")).toBe("file-code");
    expect(formatIcon("ZUGFeRD · BASIC WL")).toBe("paperclip");
    expect(formatIcon("ZUGFeRD 1")).toBe("paperclip");
    expect(formatIcon("Hybrid PDF (unsupported)")).toBe("paperclip");
    expect(formatIcon("Plain PDF")).toBe("file-text");
    expect(formatIcon("Scanned PDF")).toBe("file-text");
  });
});
