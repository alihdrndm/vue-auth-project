import { VueQueryPlugin } from "@tanstack/vue-query";
import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import { json, mockFetch } from "../../testing/http";
import UploadFileRow from "./UploadFileRow.vue";
import type { UploadRow } from "./uploadQueue";

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: "/", component: { template: "<div />" } },
    {
      path: "/app/invoices/:id",
      name: "invoice",
      component: { template: "<div />" },
    },
  ],
});

function row(overrides: Partial<UploadRow>): UploadRow {
  return {
    id: 1,
    name: "a.pdf",
    size: 10,
    state: "done",
    progress: 1,
    documentId: "doc-1",
    error: null,
    retryable: true,
    ...overrides,
  };
}

function mountRow(value: UploadRow) {
  return mount(UploadFileRow, {
    props: { row: value },
    global: { plugins: [router, VueQueryPlugin] },
  });
}

afterEach(() => vi.unstubAllGlobals());

describe("UploadFileRow", () => {
  it("shows where processing failed, not every step as done", async () => {
    mockFetch(() =>
      json(200, { id: "doc-1", status: "failed", processing_step: "validate" }),
    );
    const wrapper = mountRow(row({}));
    await flushPromises();
    expect(wrapper.find(".row__status").text()).toBe("Failed");
    const labels = wrapper.findAll(".steps__item").map((item) => item.text());
    expect(labels[0]).toContain("done");
    expect(labels[1]).toContain("failed");
    expect(labels[2]).toContain("not run");
  });

  it("offers Retry for a failed upload, but not for a refused file", async () => {
    const failed = mountRow(
      row({
        state: "failed",
        documentId: null,
        error: { title: "Upload failed", detail: "" },
      }),
    );
    await failed
      .findAll("button")
      .find((button) => button.text() === "Retry")
      ?.trigger("click");
    expect(failed.emitted("retry")).toHaveLength(1);
    const refused = mountRow(
      row({
        state: "failed",
        documentId: null,
        retryable: false,
        error: { title: "Not a PDF or XML file.", detail: "" },
      }),
    );
    expect(refused.findAll("button").map((button) => button.text())).toEqual([
      "Remove",
    ]);
  });
});
