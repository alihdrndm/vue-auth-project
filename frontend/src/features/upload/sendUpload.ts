// Sending one file to `POST /documents`. XMLHttpRequest instead of fetch, because only it
// reports upload progress; like the API client it sends the CSRF header and turns
// problem+json answers into ApiError.
import {
  API_PREFIX,
  ApiError,
  currentCsrfToken,
  reportAuthFailure,
} from "../../api/client";
import type { components } from "../../api/schema";
import type { SendFile, SendResult } from "./uploadQueue";

type UploadResponse = components["schemas"]["UploadResponse"];

function parse(text: string): unknown {
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return null;
  }
}

/** The created document, or the existing one when the file was already uploaded. */
export function resultOf(body: UploadResponse): SendResult {
  const created = body.created[0];
  if (created) return { kind: "created", documentId: created.id };
  const duplicate = body.duplicates[0];
  if (duplicate)
    return { kind: "duplicate", documentId: duplicate.existing_document_id };
  throw new ApiError({
    status: 500,
    code: "INTERNAL",
    title: "Upload failed",
    detail: "The server accepted the file but returned no document.",
  });
}

interface Answer {
  status: number;
  body: unknown;
}

function codeOf(body: unknown): string | undefined {
  return typeof body === "object" && body !== null && "code" in body
    ? String((body as { code: unknown }).code)
    : undefined;
}

export function createSender(
  createRequest: () => XMLHttpRequest = () => new XMLHttpRequest(),
): SendFile {
  function attempt(
    file: File,
    onProgress: (share: number) => void,
    token: string | null,
  ): Promise<Answer> {
    return new Promise<Answer>((resolve, reject) => {
      const request = createRequest();
      request.open("POST", `${API_PREFIX}/documents`);
      request.withCredentials = true;
      if (token) request.setRequestHeader("X-CSRFToken", token);
      request.upload.onprogress = (event) => {
        if (event.lengthComputable && event.total > 0)
          onProgress(event.loaded / event.total);
      };
      request.onload = () =>
        resolve({ status: request.status, body: parse(request.responseText) });
      request.onerror = () =>
        reject(
          new ApiError({
            status: 0,
            code: "NETWORK",
            title: "Upload failed",
            detail: "Check your connection and try again.",
          }),
        );
      const form = new FormData();
      form.append("files", file, file.name);
      request.send(form);
    });
  }

  // Like the API client: the CSRF token is refreshed and the upload sent again once on
  // 403 CSRF_FAILED, and a 401 goes to the same handler (sign-in, or home when expired).
  return async (file, onProgress) => {
    let answer = await attempt(file, onProgress, await currentCsrfToken());
    if (answer.status === 403 && codeOf(answer.body) === "CSRF_FAILED") {
      answer = await attempt(file, onProgress, await currentCsrfToken(true));
    }
    if (answer.status === 401) reportAuthFailure(codeOf(answer.body));
    if (answer.status === 201) return resultOf(answer.body as UploadResponse);
    throw ApiError.fromBody(answer.status, answer.body);
  };
}
