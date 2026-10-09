// Sending one file to `POST /documents`. XMLHttpRequest instead of fetch, because only it
// reports upload progress; like the API client it sends the CSRF header and turns
// problem+json answers into ApiError.
import { API_PREFIX, ApiError, currentCsrfToken } from "../../api/client";
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

export function createSender(
  createRequest: () => XMLHttpRequest = () => new XMLHttpRequest(),
): SendFile {
  return async (file, onProgress) => {
    const token = await currentCsrfToken();
    return new Promise<SendResult>((resolve, reject) => {
      const request = createRequest();
      request.open("POST", `${API_PREFIX}/documents`);
      request.withCredentials = true;
      if (token) request.setRequestHeader("X-CSRFToken", token);
      request.upload.onprogress = (event) => {
        if (event.lengthComputable && event.total > 0)
          onProgress(event.loaded / event.total);
      };
      request.onload = () => {
        const body = parse(request.responseText);
        if (request.status === 201) {
          try {
            resolve(resultOf(body as UploadResponse));
          } catch (error) {
            reject(error);
          }
          return;
        }
        reject(ApiError.fromBody(request.status, body));
      };
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
  };
}
