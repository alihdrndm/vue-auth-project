import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { defineComponent, h, ref } from "vue";

import Dialog from "./Dialog.vue";

const Host = defineComponent({
  setup() {
    const open = ref(false);
    return () =>
      h("div", [
        h(
          "button",
          { id: "opener", onClick: () => (open.value = true) },
          "Reject…",
        ),
        h(
          Dialog,
          {
            open: open.value,
            "onUpdate:open": (value: boolean) => (open.value = value),
            title: "Reject invoice SW-2026-77812?",
            description: "Stadtwerke Leipzig GmbH",
          },
          {
            default: () => [
              h("label", { for: "reason" }, "Reason"),
              h("textarea", { id: "reason" }),
            ],
            footer: () => [
              h(
                "button",
                { id: "cancel", onClick: () => (open.value = false) },
                "Cancel",
              ),
              h("button", { id: "confirm" }, "Reject invoice"),
            ],
          },
        ),
      ]);
  },
});

async function openDialog() {
  const wrapper = mount(Host, { attachTo: document.body });
  const opener = wrapper.get<HTMLButtonElement>("#opener");
  opener.element.focus();
  await opener.trigger("click");
  await flushPromises();
  return wrapper;
}

describe("Dialog", () => {
  it("is a labelled modal dialog and moves focus to the first field", async () => {
    const wrapper = await openDialog();
    const dialog = wrapper.get("dialog");
    expect(dialog.attributes("open")).toBeDefined();
    expect(dialog.attributes("aria-modal")).toBe("true");
    const title = wrapper.get("h2");
    expect(title.text()).toBe("Reject invoice SW-2026-77812?");
    expect(dialog.attributes("aria-labelledby")).toBe(title.attributes("id"));
    expect(wrapper.get(".dialog-description").text()).toBe(
      "Stadtwerke Leipzig GmbH",
    );
    expect(document.activeElement?.id).toBe("reason");
    wrapper.unmount();
  });

  it("closes on Escape and returns focus to the opener", async () => {
    const wrapper = await openDialog();
    await wrapper.get("dialog").trigger("keydown", { key: "Escape" });
    await flushPromises();
    expect(wrapper.find("#reason").exists()).toBe(false);
    expect(wrapper.get("dialog").attributes("open")).toBeUndefined();
    expect(document.activeElement?.id).toBe("opener");
    wrapper.unmount();
  });

  it("closes with the Close button and with Cancel", async () => {
    const wrapper = await openDialog();
    await wrapper.get('button[aria-label="Close"]').trigger("click");
    await flushPromises();
    expect(wrapper.find("#reason").exists()).toBe(false);

    await wrapper.get("#opener").trigger("click");
    await flushPromises();
    await wrapper.get("#cancel").trigger("click");
    await flushPromises();
    expect(wrapper.find("#reason").exists()).toBe(false);
    wrapper.unmount();
  });

  it("keeps Tab inside the dialog", async () => {
    const wrapper = await openDialog();
    const confirm = wrapper.get<HTMLButtonElement>("#confirm");
    confirm.element.focus();
    await wrapper.get("dialog").trigger("keydown", { key: "Tab" });
    expect(document.activeElement?.getAttribute("aria-label")).toBe("Close");
    await wrapper
      .get("dialog")
      .trigger("keydown", { key: "Tab", shiftKey: true });
    expect(document.activeElement?.id).toBe("confirm");
    wrapper.unmount();
  });
});
