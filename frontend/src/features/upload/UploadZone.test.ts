import { VueQueryPlugin } from "@tanstack/vue-query";
import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import type { SendFile } from "./uploadQueue";
import UploadZone from "./UploadZone.vue";

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

function pdf(name: string, bytes = 10): File {
  return new File([new Uint8Array(bytes)], name, { type: "application/pdf" });
}

function mountZone(send: SendFile) {
  return mount(UploadZone, {
    props: { send },
    global: { plugins: [router, VueQueryPlugin] },
    attachTo: document.body,
  });
}

async function pick(wrapper: ReturnType<typeof mountZone>, files: File[]) {
  const input = wrapper.find<HTMLInputElement>('input[type="file"]');
  Object.defineProperty(input.element, "files", {
    value: files,
    configurable: true,
  });
  await input.trigger("change");
  await flushPromises();
}

describe("UploadZone", () => {
  it("uploads each file and reports the new document", async () => {
    const sent: string[] = [];
    const send: SendFile = async (file) => {
      sent.push(file.name);
      return { kind: "created", documentId: `doc-${file.name}` };
    };
    const wrapper = mountZone(send);
    await pick(wrapper, [pdf("a.pdf"), pdf("b.pdf")]);
    expect(sent).toEqual(["a.pdf", "b.pdf"]);
    expect(wrapper.emitted("uploaded")).toEqual([["doc-a.pdf"], ["doc-b.pdf"]]);
    wrapper.unmount();
  });

  it("refuses other file types and files over 4 MB without sending them", async () => {
    const sent: string[] = [];
    const send: SendFile = async (file) => {
      sent.push(file.name);
      return { kind: "created", documentId: "x" };
    };
    const wrapper = mountZone(send);
    const text = new File(["x"], "notes.txt", { type: "text/plain" });
    await pick(wrapper, [
      text,
      pdf("big.pdf", 4 * 1024 * 1024 + 1),
      pdf("ok.pdf"),
    ]);
    expect(sent).toEqual(["ok.pdf"]);
    const body = document.body.textContent ?? "";
    expect(body).toContain("Not a PDF or XML file.");
    expect(body).toContain("Larger than 4 MB.");
    wrapper.unmount();
  });

  it("takes only the first 10 files and says so", async () => {
    const sent: string[] = [];
    const send: SendFile = async (file) => {
      sent.push(file.name);
      return { kind: "created", documentId: file.name };
    };
    const wrapper = mountZone(send);
    await pick(
      wrapper,
      Array.from({ length: 12 }, (_, index) => pdf(`f${index}.pdf`)),
    );
    expect(sent).toHaveLength(10);
    expect(document.body.textContent).toContain(
      "Only the first 10 files were added.",
    );
    wrapper.unmount();
  });

  it("shows each file's own error", async () => {
    const send: SendFile = async () => {
      throw {
        title: "Upload limit reached",
        detail: "This sandbox has used its uploads.",
      };
    };
    const wrapper = mountZone(send);
    await pick(wrapper, [pdf("late.pdf")]);
    expect(document.body.textContent).toContain("Upload limit reached");
    expect(document.body.textContent).toContain(
      "This sandbox has used its uploads.",
    );
    wrapper.unmount();
  });

  it("shows the drop overlay while files are dragged over the window", async () => {
    const wrapper = mountZone(async () => ({
      kind: "created",
      documentId: "x",
    }));
    const event = new Event("dragenter", { cancelable: true }) as DragEvent;
    Object.defineProperty(event, "dataTransfer", {
      value: { types: ["Files"], files: [] },
    });
    window.dispatchEvent(event);
    await flushPromises();
    expect(
      document.body.querySelector('[aria-label="Drop files to upload"]'),
    ).not.toBeNull();
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    await flushPromises();
    expect(
      document.body.querySelector('[aria-label="Drop files to upload"]'),
    ).toBeNull();
    wrapper.unmount();
  });
});
