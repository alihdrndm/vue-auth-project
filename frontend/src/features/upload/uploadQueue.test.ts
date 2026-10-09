import { describe, expect, it } from "vitest";
import { nextTick } from "vue";

import {
  createUploadQueue,
  MAX_PARALLEL_UPLOADS,
  type SendResult,
} from "./uploadQueue";

interface Pending {
  file: File;
  progress: (share: number) => void;
  resolve: (result: SendResult) => void;
  reject: (error: unknown) => void;
}

function fakeSender() {
  const pending: Pending[] = [];
  const send = (file: File, progress: (share: number) => void) =>
    new Promise<SendResult>((resolve, reject) => {
      pending.push({ file, progress, resolve, reject });
    });
  return { pending, send };
}

function at<T>(list: readonly T[], index: number): T {
  const item = list[index];
  if (item === undefined) throw new Error(`no item ${index}`);
  return item;
}

const file = (name: string) =>
  new File(["x"], name, { type: "application/pdf" });
const flush = async () => {
  await Promise.resolve();
  await nextTick();
};

describe("upload queue", () => {
  it("sends one file per request, at most three at once", async () => {
    const { pending, send } = fakeSender();
    const queue = createUploadQueue(send);
    queue.add([
      file("a.pdf"),
      file("b.pdf"),
      file("c.pdf"),
      file("d.pdf"),
      file("e.pdf"),
    ]);
    expect(pending).toHaveLength(MAX_PARALLEL_UPLOADS);
    expect(queue.rows.map((row) => row.state)).toEqual([
      "uploading",
      "uploading",
      "uploading",
      "queued",
      "queued",
    ]);
    at(pending, 0).resolve({ kind: "created", documentId: "doc-a" });
    await flush();
    expect(pending).toHaveLength(4);
    expect(queue.rows[0]).toMatchObject({
      state: "done",
      documentId: "doc-a",
      progress: 1,
    });
  });

  it("keeps each file's progress and error on its own row", async () => {
    const { pending, send } = fakeSender();
    const queue = createUploadQueue(send);
    queue.add([file("good.pdf"), file("bad.txt")]);
    at(pending, 0).progress(0.5);
    at(pending, 1).reject({
      title: "Unsupported file",
      detail: "Only PDF and XML invoices.",
    });
    await flush();
    expect(queue.rows[0]).toMatchObject({
      state: "uploading",
      progress: 0.5,
      error: null,
    });
    expect(queue.rows[1]).toMatchObject({
      state: "failed",
      error: {
        title: "Unsupported file",
        detail: "Only PDF and XML invoices.",
      },
    });
  });

  it("marks duplicates with the existing document", async () => {
    const { pending, send } = fakeSender();
    const queue = createUploadQueue(send);
    queue.add([file("again.pdf")]);
    at(pending, 0).resolve({ kind: "duplicate", documentId: "doc-old" });
    await flush();
    expect(queue.rows[0]).toMatchObject({
      state: "duplicate",
      documentId: "doc-old",
    });
  });

  it("retries a failed file and dismisses settled rows", async () => {
    const { pending, send } = fakeSender();
    const settled: string[] = [];
    const queue = createUploadQueue(send, (row) =>
      settled.push(`${row.name}:${row.state}`),
    );
    queue.add([file("flaky.pdf")]);
    at(pending, 0).reject(new Error("offline"));
    await flush();
    expect(at(queue.rows, 0).error?.title).toBe("Upload failed");
    queue.retry(at(queue.rows, 0).id);
    expect(pending).toHaveLength(2);
    at(pending, 1).resolve({ kind: "created", documentId: "doc-f" });
    await flush();
    expect(settled).toEqual(["flaky.pdf:failed", "flaky.pdf:done"]);
    queue.dismiss(at(queue.rows, 0).id);
    expect(queue.rows).toHaveLength(0);
  });

  it("does not dismiss a file while it uploads", () => {
    const { send } = fakeSender();
    const queue = createUploadQueue(send);
    queue.add([file("busy.pdf")]);
    queue.dismiss(at(queue.rows, 0).id);
    expect(queue.rows).toHaveLength(1);
  });
});

describe("refused files", () => {
  it("adds a failed row that is never sent and cannot be retried", () => {
    const { pending, send } = fakeSender();
    const queue = createUploadQueue(send);
    queue.addRejected("notes.txt", 10, {
      title: "Not a PDF or XML file",
      detail: "Only PDF and XML invoices can be uploaded.",
    });
    queue.retry(at(queue.rows, 0).id);
    expect(pending).toHaveLength(0);
    expect(at(queue.rows, 0)).toMatchObject({
      state: "failed",
      name: "notes.txt",
    });
  });
});
