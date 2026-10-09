import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import Select from "./Select.vue";

const ROLES = [
  { value: "accountant", label: "Accountant" },
  { value: "approver", label: "Approver" },
  { value: "admin", label: "Admin" },
  { value: "viewer", label: "Viewer" },
];

describe("Select", () => {
  it("has a visible label and picks an option", async () => {
    const wrapper = mount(Select, {
      props: {
        label: "Role",
        options: ROLES,
        modelValue: "accountant",
        "onUpdate:modelValue": (value: string) =>
          wrapper.setProps({ modelValue: value }),
      },
    });
    const select = wrapper.get("select");
    expect(wrapper.get("label").attributes("for")).toBe(
      select.attributes("id"),
    );
    expect(select.findAll("option").map((o) => o.text())).toEqual([
      "Accountant",
      "Approver",
      "Admin",
      "Viewer",
    ]);
    await select.setValue("admin");
    expect(wrapper.props("modelValue")).toBe("admin");
  });

  it("offers a disabled placeholder option", () => {
    const wrapper = mount(Select, {
      props: { label: "Role", options: ROLES, placeholder: "Choose a role" },
    });
    const first = wrapper.get("option");
    expect(first.text()).toBe("Choose a role");
    expect(first.attributes("value")).toBe("");
    expect(first.attributes("disabled")).toBeDefined();
  });

  it("shows the error text", () => {
    const wrapper = mount(Select, {
      props: {
        label: "Role",
        options: ROLES,
        error: "Choose a role before you invite someone.",
      },
    });
    const error = wrapper.get(".field-error");
    expect(error.text()).toBe("Choose a role before you invite someone.");
    expect(wrapper.get("select").attributes("aria-invalid")).toBe("true");
    expect(wrapper.get("select").attributes("aria-describedby")).toBe(
      error.attributes("id"),
    );
  });

  it("shows why it is disabled", () => {
    const wrapper = mount(Select, {
      props: {
        label: "Role",
        options: ROLES,
        modelValue: "admin",
        disabled: true,
        hint: "You can't change your own role.",
      },
    });
    expect(wrapper.get("select").attributes("disabled")).toBeDefined();
    expect(wrapper.get(".field-hint").text()).toBe(
      "You can't change your own role.",
    );
  });
});
