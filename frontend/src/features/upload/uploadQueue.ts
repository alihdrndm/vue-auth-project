// The upload queue (HANDOFF "Inbox"): every file is its own request, at most three run at
// once, and each file keeps its own progress and its own error, so one refused file never
// hides the others.
import { reactive, readonly } from "vue";

export const MAX_PARALLEL_UPLOADS = 3;

export type UploadState =
  "queued" | "uploading" | "done" | "duplicate" | "failed";

export interface UploadRow {
  id: number;
  name: string;
  size: number;
  state: UploadState;
  /** 0–1 while uploading. */
  progress: number;
  /** The new document, or the existing one for a duplicate. */
  documentId: string | null;
  /** A problem's title and detail, shown on the row. */
  error: { title: string; detail: string } | null;
  /** False for a file refused before sending: there is nothing to send again. */
  retryable: boolean;
}

export interface SendResult {
  kind: "created" | "duplicate";
  documentId: string;
}

/** Sends one file; reports upload progress (0–1); rejects with an error carrying title/detail. */
export type SendFile = (
  file: File,
  onProgress: (share: number) => void,
) => Promise<SendResult>;

function problemOf(error: unknown): { title: string; detail: string } {
  if (error && typeof error === "object" && "title" in error) {
    const { title, detail } = error as { title?: unknown; detail?: unknown };
    return {
      title: typeof title === "string" ? title : "Upload failed",
      detail: typeof detail === "string" ? detail : "",
    };
  }
  return {
    title: "Upload failed",
    detail: "Check your connection and try again.",
  };
}

export function createUploadQueue(
  send: SendFile,
  onSettled?: (row: UploadRow) => void,
) {
  const rows = reactive<UploadRow[]>([]);
  let nextId = 1;
  let running = 0;
  const files = new Map<number, File>();

  function pump(): void {
    while (running < MAX_PARALLEL_UPLOADS) {
      const row = rows.find((candidate) => candidate.state === "queued");
      if (!row) return;
      start(row);
    }
  }

  function start(row: UploadRow): void {
    const file = files.get(row.id);
    if (!file) return;
    running += 1;
    row.state = "uploading";
    row.progress = 0;
    row.error = null;
    send(file, (share) => {
      row.progress = Math.min(1, Math.max(0, share));
    })
      .then((result) => {
        row.state = result.kind === "created" ? "done" : "duplicate";
        row.progress = 1;
        row.documentId = result.documentId;
        files.delete(row.id);
      })
      .catch((error: unknown) => {
        row.state = "failed";
        row.error = problemOf(error);
      })
      .finally(() => {
        running -= 1;
        onSettled?.(row);
        pump();
      });
  }

  function add(list: Iterable<File>): void {
    for (const file of list) {
      const id = nextId++;
      files.set(id, file);
      rows.push({
        id,
        name: file.name,
        size: file.size,
        state: "queued",
        progress: 0,
        documentId: null,
        error: null,
        retryable: true,
      });
    }
    pump();
  }

  /** A file refused before sending (wrong type, too large): a failed row, no retry. */
  function addRejected(
    name: string,
    size: number,
    error: { title: string; detail: string },
  ): void {
    rows.push({
      id: nextId++,
      name,
      size,
      state: "failed",
      progress: 0,
      documentId: null,
      error,
      retryable: false,
    });
  }

  function retry(id: number): void {
    const row = rows.find((candidate) => candidate.id === id);
    if (row?.state === "failed" && files.has(id)) {
      row.state = "queued";
      pump();
    }
  }

  function dismiss(id: number): void {
    const index = rows.findIndex((candidate) => candidate.id === id);
    if (index >= 0 && rows[index]?.state !== "uploading") {
      files.delete(id);
      rows.splice(index, 1);
    }
  }

  return { rows: readonly(rows), add, addRejected, retry, dismiss };
}
