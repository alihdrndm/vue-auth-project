import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import Toast from "./Toast.vue";
import { TOAST_DURATION_MS, useToast } from "./useToast";

describe("Toast", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    useToast().dismiss();
    vi.useRealTimers();
  });

  it("announces success politely and leaves after 4 s", async () => {
    const wrapper = mount(Toast);
    useToast().show({ message: "You approved RE-2026-0412." });
    await nextTick();
    const status = wrapper.get('[role="status"]');
    expect(status.attributes("aria-live")).toBe("polite");
    expect(status.text()).toContain("You approved RE-2026-0412.");
    expect(wrapper.get('[role="alert"]').text()).toBe("");

    vi.advanceTimersByTime(TOAST_DURATION_MS);
    await nextTick();
    expect(status.text()).toBe("");
  });

  it("shows errors as alerts that stay until dismissed, with an action", async () => {
    const wrapper = mount(Toast);
    const retry = vi.fn();
    useToast().show({
      kind: "error",
      message: "Export failed. No file was created.",
      action: { label: "Try again", run: retry },
    });
    await nextTick();
    const alert = wrapper.get('[role="alert"]');
    expect(alert.text()).toContain("Export failed. No file was created.");

    vi.advanceTimersByTime(TOAST_DURATION_MS * 10);
    await nextTick();
    expect(alert.text()).toContain("Export failed.");

    await alert.get(".toast-action").trigger("click");
    expect(retry).toHaveBeenCalledOnce();
    expect(alert.text()).toBe("");
  });

  it("shows one toast at a time and can be dismissed", async () => {
    const wrapper = mount(Toast);
    const { show } = useToast();
    show({ message: "First" });
    show({ kind: "info", message: "Exporting 7 invoices…" });
    await nextTick();
    expect(wrapper.findAll(".toast")).toHaveLength(1);
    expect(wrapper.text()).toContain("Exporting 7 invoices…");
    await wrapper.get('button[aria-label="Dismiss"]').trigger("click");
    expect(wrapper.findAll(".toast")).toHaveLength(0);
  });

  it("honours a custom duration", async () => {
    const wrapper = mount(Toast);
    useToast().show({ kind: "info", message: "Next invoice", duration: 2500 });
    await nextTick();
    vi.advanceTimersByTime(2500);
    await nextTick();
    expect(wrapper.findAll(".toast")).toHaveLength(0);
  });
});
