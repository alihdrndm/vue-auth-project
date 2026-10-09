import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import ActOne from "./ActOne.vue";
import ActTwo from "./ActTwo.vue";

function reducedMotion(reduce: boolean): void {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: reduce && query.includes("reduce"),
    media: query,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
  }));
}

function button(wrapper: ReturnType<typeof mount>, text: string) {
  const found = wrapper
    .findAll("button")
    .find((candidate) => candidate.text().startsWith(text));
  if (!found) throw new Error(`no button ${text}`);
  return found;
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.stubGlobal("requestAnimationFrame", (fn: FrameRequestCallback) =>
    setTimeout(() => fn(0), 0),
  );
  reducedMotion(false);
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("Act 1", () => {
  it("stamps a document: Received, then Processing, then its verdict", async () => {
    const wrapper = mount(ActOne);
    expect(wrapper.text()).toContain("Nothing stamped yet.");
    await button(wrapper, "Stamp it: RE-2026-0412").trigger("click");
    expect(wrapper.find("tbody").text()).toContain("Received");
    await vi.advanceTimersByTimeAsync(400);
    expect(wrapper.find("tbody").text()).toContain("Processing");
    await vi.advanceTimersByTimeAsync(700);
    expect(wrapper.find("tbody").text()).toContain("Valid e-invoice");
    expect(button(wrapper, "Stamped").attributes("disabled")).toBeDefined();
  });

  it("shows the end state at once with reduced motion", async () => {
    reducedMotion(true);
    const wrapper = mount(ActOne);
    await button(wrapper, "Stamp it: RE-2026-0413").trigger("click");
    expect(wrapper.find("tbody").text()).toContain("Invalid · BR-DE-15");
    expect(wrapper.text()).toContain(
      "for public bodies this is the Leitweg-ID",
    );
  });

  it("accepts a document dropped on the stamp, once", async () => {
    reducedMotion(true);
    const wrapper = mount(ActOne);
    const drop = (id: string) =>
      wrapper
        .find(".dropzone")
        .trigger("drop", { dataTransfer: { getData: () => id } });
    await drop("bwl");
    await drop("bwl");
    const rows = wrapper.findAll("tbody tr");
    expect(rows).toHaveLength(1);
    expect(wrapper.text()).toContain("Not an e-invoice (profile BASIC WL)");
    expect(wrapper.find("a").text()).toContain(
      "Source: BMF letter, 15 Oct 2024",
    );
  });

  it("sums up after all four and starts again", async () => {
    reducedMotion(true);
    const wrapper = mount(ActOne);
    for (const number of [
      "RE-2026-0412",
      "2026-1043",
      "F-2026-118",
      "RE-2026-0413",
    ]) {
      await button(wrapper, `Stamp it: ${number}`).trigger("click");
    }
    expect(wrapper.text()).toContain(
      "4 invoices stamped. 1 is a valid e-invoice.",
    );
    await button(wrapper, "Do it again").trigger("click");
    expect(wrapper.text()).toContain("Nothing stamped yet.");
  });
});

describe("Act 2", () => {
  it("asks for a note before resolving", async () => {
    const wrapper = mount(ActTwo);
    expect(
      button(wrapper, "Mark reviewed").attributes("disabled"),
    ).toBeDefined();
    expect(wrapper.text()).toContain("Resolve the block check first.");
    await wrapper.find("form").trigger("submit");
    expect(wrapper.text()).toContain(
      "Add a note before you resolve this check.",
    );
    expect(wrapper.text()).toContain("New account");
  });

  it("resolves, hands off to the phone, approves and exports", async () => {
    const wrapper = mount(ActTwo);
    expect(wrapper.text()).toContain("Nothing to approve yet");
    await button(wrapper, "Use example note").trigger("click");
    await wrapper.find("form").trigger("submit");
    expect(wrapper.text()).toContain("Resolved by Anna Weber, just now");
    expect(wrapper.text()).toContain("Confirmed change");
    await button(wrapper, "Mark reviewed").trigger("click");
    expect(wrapper.text()).toContain(
      "You marked this reviewed. Jonas Brandt approves next.",
    );
    expect(wrapper.find(".chip").text()).toBe("Awaiting approval");
    await button(wrapper, "Reject").trigger("click");
    expect(wrapper.text()).toContain("Rejecting works in the sandbox.");
    await button(wrapper, "Approve").trigger("click");
    expect(wrapper.text()).toContain("Approving…");
    await vi.advanceTimersByTimeAsync(700);
    expect(wrapper.text()).toContain("You approved this on 09 Oct 2026.");
    expect(wrapper.find(".chip").text()).toBe("Approved");
    await vi.advanceTimersByTimeAsync(500);
    await nextTick();
    expect(wrapper.find(".chip").text()).toBe("Exported");
    expect(wrapper.find(".export--in").exists()).toBe(true);
    await button(wrapper, "Do it again").trigger("click");
    expect(wrapper.find(".chip").text()).toBe("Needs review");
  });

  it("marks the current step", async () => {
    const wrapper = mount(ActTwo);
    expect(wrapper.find('[aria-current="step"]').text()).toContain(
      "Resolve the check",
    );
    await button(wrapper, "Use example note").trigger("click");
    await wrapper.find("form").trigger("submit");
    expect(wrapper.find('[aria-current="step"]').text()).toContain(
      "Mark reviewed",
    );
  });
});
