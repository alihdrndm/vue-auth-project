// Loads PDF.js on demand (it is large) and opens a document from bytes. The worker runs from the
// app's own origin; nothing is fetched from a third party.
import type { PDFDocumentProxy } from "pdfjs-dist";

export type { PDFDocumentProxy, PDFPageProxy } from "pdfjs-dist";

let ready: Promise<typeof import("pdfjs-dist")> | null = null;

async function load(): Promise<typeof import("pdfjs-dist")> {
  const [pdfjs, worker] = await Promise.all([
    import("pdfjs-dist"),
    import("pdfjs-dist/build/pdf.worker.min.mjs?url"),
  ]);
  pdfjs.GlobalWorkerOptions.workerSrc = worker.default;
  return pdfjs;
}

/** Opens a PDF from its bytes. The bytes are not fetched again. */
export async function openPdf(data: ArrayBuffer): Promise<PDFDocumentProxy> {
  ready ??= load();
  const pdfjs = await ready;
  // PDF.js takes ownership of the buffer it is given, so it gets a copy.
  return pdfjs.getDocument({ data: new Uint8Array(data.slice(0)) }).promise;
}
