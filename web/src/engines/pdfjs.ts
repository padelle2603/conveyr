import { GlobalWorkerOptions, getDocument } from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";

GlobalWorkerOptions.workerSrc = workerUrl;

export function openPdf(data: Uint8Array) {
  return getDocument({
    data,
    standardFontDataUrl: `${import.meta.env.BASE_URL}pdfjs-standard-fonts/`,
  }).promise;
}

export type PDFDocumentProxy = import("pdfjs-dist").PDFDocumentProxy;
export type PDFPageProxy = import("pdfjs-dist").PDFPageProxy;
export type PageViewport = import("pdfjs-dist").PageViewport;