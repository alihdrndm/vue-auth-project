import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import TextInput from "./TextInput.vue";

describe("TextInput", () => {
  it("has a visible label tied to the input and updates the model", async () => {
    const wrapper = mount(TextInput, {
      props: {
        label: "IBAN",
        modelValue: "",
        "onUpdate:modelValue": (value: string) =>
          wrapper.setProps({ modelValue: value }),
      },
    });
    const label = wrapper.get("label");
    const input = wrapper.get("input");
    expect(label.text()).toBe("IBAN");
    expect(label.attributes("for")).toBe(input.attributes("id"));
    await input.setValue("DE44 5001");
    expect(wrapper.props("modelValue")).toBe("DE44 5001");
  });

  it("shows the hint and links it", () => {
    const wrapper = mount(TextInput, {
      props: { label: "IBAN", hint: "22 characters, starts with DE." },
    });
    const hint = wrapper.get(".field-hint");
    expect(hint.text()).toBe("22 characters, starts with DE.");
    expect(wrapper.get("input").attributes("aria-describedby")).toBe(
      hint.attributes("id"),
    );
  });

  it("shows the error text instead of the hint and marks the input invalid", () => {
    const wrapper = mount(TextInput, {
      props: {
        label: "IBAN",
        hint: "22 characters, starts with DE.",
        error: "Enter all 22 characters of the IBAN.",
      },
    });
    const input = wrapper.get("input");
    const error = wrapper.get(".field-error");
    expect(error.text()).toBe("Enter all 22 characters of the IBAN.");
    expect(error.find("svg").exists()).toBe(true);
    expect(wrapper.find(".field-hint").exists()).toBe(false);
    expect(input.attributes("aria-invalid")).toBe("true");
    expect(input.attributes("aria-describedby")).toBe(error.attributes("id"));
  });

  it("can be disabled and uses mono for numbers", () => {
    const wrapper = mount(TextInput, {
      props: { label: "IBAN", disabled: true, mono: true },
    });
    const input = wrapper.get("input");
    expect(input.attributes("disabled")).toBeDefined();
    expect(input.classes()).toContain("field-control--mono");
  });
});
