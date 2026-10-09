import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import { INK_FILTER_ID } from "./ink";
import Stamp, { chipDate, stampDate, stampLabel } from "./Stamp.vue";

describe("Stamp", () => {
  it("prints the German date the way the stamp does", () => {
    expect(stampDate("2026-10-09")).toBe("09. OKT. 2026");
    expect(stampDate("2027-03-02")).toBe("02. MÄRZ 2027");
    expect(stampDate("2026-09-15")).toBe("15. SEP. 2026");
    expect(stampDate("not a date")).toBe("");
  });

  it("is an image named with the English date", () => {
    const wrapper = mount(Stamp, { props: { date: "2026-10-09" } });
    expect(wrapper.attributes("role")).toBe("img");
    expect(wrapper.attributes("aria-label")).toBe(
      "Eingang stamp, 9 October 2026",
    );
    expect(stampLabel("2027-03-02")).toBe("Eingang stamp, 2 March 2027");
    expect(wrapper.text()).toContain("Eingang");
    expect(wrapper.text()).toContain("09. OKT. 2026");
  });

  it("scales from the lettering size and adds the shared ink filter once", () => {
    const lg = mount(Stamp, {
      props: { date: "2026-10-09" },
      attachTo: document.body,
    });
    const md = mount(Stamp, {
      props: { date: "2026-10-09", size: "md", rotate: 3 },
      attachTo: document.body,
    });
    expect(lg.attributes("style")).toContain("font-size: 44px");
    expect(md.attributes("style")).toContain("font-size: 22px");
    expect(md.attributes("style")).toContain("rotate(3deg)");
    expect(document.querySelectorAll(`#${INK_FILTER_ID}`)).toHaveLength(1);
    lg.unmount();
    md.unmount();
  });

  it("renders the mark hidden from assistive tech", () => {
    const wrapper = mount(Stamp, { props: { size: "mark", markSize: 28 } });
    expect(wrapper.attributes("aria-hidden")).toBe("true");
    expect(wrapper.text()).toBe("E");
    expect(wrapper.attributes("style")).toContain("font-size: 28px");
  });

  it("renders the received chip in the app date format", () => {
    const local = new Date(2026, 9, 7, 14, 30).toISOString();
    expect(chipDate(local)).toBe("07 Oct, 14:30");
    const wrapper = mount(Stamp, { props: { size: "chip", date: local } });
    expect(wrapper.text()).toBe("07 Oct, 14:30");
  });
});
