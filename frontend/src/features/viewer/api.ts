// Fetches the document's representations for the viewer. The original file, the XML and the text
// are sent as attachments by the API; the viewer reads their bytes and never navigates to them.
import { api, ApiError, unwrap } from "../../api/client";

export type Representation = "xml" | "text" | "visualization";

function isNotAvailable(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404;
}

/** The XML, the PDF text or the visualisation HTML, or null when the document has none. */
export async function fetchRepresentation(
  id: string,
  kind: Representation,
): Promise<string | null> {
  const params = {
    params: { path: { document_id: id } },
    parseAs: "text" as const,
  };
  try {
    switch (kind) {
      case "xml":
        return (
          unwrap(
            await api.GET("/api/v1/documents/{document_id}/xml", params),
          ) ?? ""
        );
      case "text":
        return (
          unwrap(
            await api.GET("/api/v1/documents/{document_id}/text", params),
          ) ?? ""
        );
      case "visualization":
        return (
          unwrap(
            await api.GET(
              "/api/v1/documents/{document_id}/visualization",
              params,
            ),
          ) ?? ""
        );
    }
  } catch (error) {
    if (isNotAvailable(error)) return null;
    throw error;
  }
}

/** The original file's bytes. */
export async function fetchFile(id: string): Promise<ArrayBuffer> {
  return unwrap(
    await api.GET("/api/v1/documents/{document_id}/file", {
      params: { path: { document_id: id } },
      parseAs: "arrayBuffer",
    }),
  );
}

/** Same-origin URL of an API path (download link, visualisation iframe). */
export function documentUrl(
  id: string,
  suffix: "file" | "visualization",
): string {
  return `/api/v1/documents/${encodeURIComponent(id)}/${suffix}`;
}
