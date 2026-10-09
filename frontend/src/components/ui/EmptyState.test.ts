import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import EmptyState from "./EmptyState.vue";

describe("EmptyState", () => {
  it("says what the emptiness means and offers the one action", () => {
    const wrapper = mount(EmptyState, {
      props: {
        title: "Nothing needs review",
        body: "New invoices land here once their checks have run.",
      },
      slots: { action: "<button>Upload invoices</button>" },
    });
    expect(wrapper.get("h2").text()).toBe("Nothing needs review");
    expect(wrapper.get("p").text()).toBe(
      "New invoices land here once their checks have run.",
    );
    expect(wrapper.get("button").text()).toBe("Upload invoices");
  });

  it("uses the requested heading level", () => {
    const wrapper = mount(EmptyState, {
      props: { title: "Nothing ready to export", level: 3 },
    });
    expect(wrapper.find("h3").exists()).toBe(true);
  });
});
