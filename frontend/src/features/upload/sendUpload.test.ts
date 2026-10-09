import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  resetCsrfToken,
  setAuthFailureHandler,
} from "../../api/client";
import { createSender } from "./sendUpload";

class FakeRequest {
  method = "";
  url = "";
  withCredentials = false;
  headers: Record<string, string> = {};
  status = 0;
  responseText = "";
  body: FormData | null = null;
  upload: { onprogress: ((event: ProgressEvent) => void) | null } = {
    onprogress: null,
  };
  onload: (() => void) | null = null;
  onerror: (() => void) | null = null;

  open(method: string, url: string): void {
    this.method = method;
    this.url = url;
  }

  setRequestHeader(name: string, value: string): void {
    this.headers[name] = value;
  }

  send(body: FormData): void {
    this.body = body;
  }

  respond(status: number, body: unknown): void {
    this.status = status;
    this.responseText = JSON.stringify(body);
    this.onload?.();
  }
}

function setup() {
  document.cookie = "csrftoken=token-1";
  const requests: FakeRequest[] = [];
  const send = createSender(() => {
    const request = new FakeRequest();
    requests.push(request);
    return request as unknown as XMLHttpRequest;
  });
  return { requests, send };
}

const file = new File(["%PDF-"], "a.pdf", { type: "application/pdf" });
const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

afterEach(() => {
  document.cookie = "csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT";
  resetCsrfToken();
});

describe("sendUpload", () => {
  it("posts one file with the CSRF header and reports progress", async () => {
    const { requests, send } = setup();
    const progress: number[] = [];
    const result = send(file, (share) => progress.push(share));
    await flush();
    const request = requests[0];
    if (!request) throw new Error("no request");
    expect(request.method).toBe("POST");
    expect(request.url).toBe("/api/v1/documents");
    expect(request.headers["X-CSRFToken"]).toBe("token-1");
    expect(request.body?.getAll("files")).toHaveLength(1);
    request.upload.onprogress?.({
      lengthComputable: true,
      loaded: 5,
      total: 10,
    } as ProgressEvent);
    request.respond(201, { created: [{ id: "doc-1" }], duplicates: [] });
    await expect(result).resolves.toEqual({
      kind: "created",
      documentId: "doc-1",
    });
    expect(progress).toEqual([0.5]);
  });

  it("reports a duplicate with the existing document", async () => {
    const { requests, send } = setup();
    const result = send(file, () => undefined);
    await flush();
    requests[0]?.respond(201, {
      created: [],
      duplicates: [{ filename: "a.pdf", existing_document_id: "doc-old" }],
    });
    await expect(result).resolves.toEqual({
      kind: "duplicate",
      documentId: "doc-old",
    });
  });

  it("turns a problem answer into an ApiError", async () => {
    const { requests, send } = setup();
    const result = send(file, () => undefined);
    await flush();
    requests[0]?.respond(415, {
      status: 415,
      code: "UNSUPPORTED_FILE",
      title: "Unsupported file",
      detail: "Only PDF and XML invoices.",
    });
    const error = await result.catch((caught: unknown) => caught);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      code: "UNSUPPORTED_FILE",
      title: "Unsupported file",
    });
  });

  it("reports a network failure", async () => {
    const { requests, send } = setup();
    const result = send(file, () => undefined);
    await flush();
    requests[0]?.onerror?.();
    await expect(result).rejects.toMatchObject({ code: "NETWORK" });
  });

  it("retries once with a fresh token on CSRF_FAILED", async () => {
    const { requests, send } = setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        document.cookie = "csrftoken=token-2";
        return new Response(null, { status: 204 });
      }),
    );
    const result = send(file, () => undefined);
    await flush();
    requests[0]?.respond(403, {
      code: "CSRF_FAILED",
      title: "t",
      detail: "d",
      status: 403,
    });
    await flush();
    await flush();
    expect(requests[1]?.headers["X-CSRFToken"]).toBe("token-2");
    requests[1]?.respond(201, { created: [{ id: "doc-2" }], duplicates: [] });
    await expect(result).resolves.toEqual({
      kind: "created",
      documentId: "doc-2",
    });
    vi.unstubAllGlobals();
  });

  it("reports a 401 to the session handler", async () => {
    const codes: string[] = [];
    setAuthFailureHandler((code) => codes.push(code));
    const { requests, send } = setup();
    const result = send(file, () => undefined);
    await flush();
    requests[0]?.respond(401, {
      code: "SANDBOX_EXPIRED",
      title: "t",
      detail: "d",
      status: 401,
    });
    await expect(result).rejects.toMatchObject({ code: "SANDBOX_EXPIRED" });
    expect(codes).toEqual(["SANDBOX_EXPIRED"]);
    setAuthFailureHandler(null);
  });
});
