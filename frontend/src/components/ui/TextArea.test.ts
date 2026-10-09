import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import TextArea from "./TextArea.vue";

describe("TextArea", () => {
  it("has a visible label and updates the model", async () => {
    const wrapper = mount(TextArea, {
      props: {
        label: "Note",
        modelValue: "",
        "onUpdate:modelValue": (value: string) =>
          wrapper.setProps({ modelValue: value }),
      },
    });
    const textarea = wrapper.get("textarea");
    expect(wrapper.get("label").attributes("for")).toBe(
      textarea.attributes("id"),
    );
    await textarea.setValue("Phoned the supplier.");
    expect(wrapper.props("modelValue")).toBe("Phoned the supplier.");
  });

  it("counts characters politely", () => {
    const wrapper = mount(TextArea, {
      props: {
        label: "Note",
        modelValue: "abc",
        counter: true,
        maxlength: 500,
      },
    });
    const counter = wrapper.get(".field-counter");
    expect(counter.text()).toBe("3 / 500");
    expect(counter.attributes("aria-live")).toBe("polite");
    expect(wrapper.get("textarea").attributes("maxlength")).toBe("500");
  });

  it("shows the error and the hint together", () => {
    const wrapper = mount(TextArea, {
      props: {
        label: "Note",
        error: "Add a note before you resolve this check.",
        hint: "5 to 500 characters.",
      },
    });
    const textarea = wrapper.get("textarea");
    const error = wrapper.get(".field-error");
    const hint = wrapper.get(".field-hint");
    expect(error.text()).toBe("Add a note before you resolve this check.");
    expect(error.attributes("role")).toBe("alert");
    expect(textarea.attributes("aria-invalid")).toBe("true");
    expect(textarea.attributes("aria-describedby")).toBe(
      `${error.attributes("id")} ${hint.attributes("id")}`,
    );
  });
});
