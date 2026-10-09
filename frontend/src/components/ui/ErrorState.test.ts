import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ErrorState from "./ErrorState.vue";

describe("ErrorState", () => {
  it("shows the problem title and detail and emits retry", async () => {
    const wrapper = mount(ErrorState, {
      props: {
        title: "Couldn't load the inbox",
        detail: "The server didn't answer. Nothing was changed.",
      },
    });
    expect(wrapper.attributes("role")).toBe("alert");
    expect(wrapper.get("h2").text()).toBe("Couldn't load the inbox");
    expect(wrapper.get("p").text()).toBe(
      "The server didn't answer. Nothing was changed.",
    );
    const button = wrapper.get("button");
    expect(button.text()).toBe("Try again");
    await button.trigger("click");
    expect(wrapper.emitted("retry")).toHaveLength(1);
  });

  it("shows a spinner while retrying", () => {
    const wrapper = mount(ErrorState, {
      props: { title: "Couldn't load the inbox", retrying: true },
    });
    expect(wrapper.get("button").attributes("aria-busy")).toBe("true");
  });
});
