import { PDFDocument } from "pdf-lib";
import { encryptPDF } from "@pdfsmaller/pdf-encrypt";
import { decryptPDF, isEncrypted } from "@pdfsmaller/pdf-decrypt";

export interface PagedImage {
  page: number;
  blob: Blob;
}

export interface CompressOptions {
  scale: number;
  quality: number;
}

type PDFPageProxy = import("./pdfjs").PDFPageProxy;
type PageViewport = import("./pdfjs").PageViewport;

let pdfjsPromise: Promise<typeof import("./pdfjs")> | null = null;
function loadPdfjs(): Promise<typeof import("./pdfjs")> {
  if (!pdfjsPromise) pdfjsPromise = import("./pdfjs");
  return pdfjsPromise;
}

async function loadDoc(bytes: Uint8Array): Promise<PDFDocument> {
  return PDFDocument.load(bytes, {
    ignoreEncryption: true,
    updateMetadata: false,
  });
}

export async function mergePdfs(inputs: Uint8Array[]): Promise<Uint8Array> {
  const out = await PDFDocument.create();
  for (const input of inputs) {
    const src = await loadDoc(input);
    const pages = await out.copyPages(src, src.getPageIndices());
    for (const page of pages) out.addPage(page);
  }
  return out.save();
}

export async function splitPdf(input: Uint8Array): Promise<Uint8Array[]> {
  const src = await loadDoc(input);
  const outs: Uint8Array[] = [];
  for (let i = 0; i < src.getPageCount(); i++) {
    const doc = await PDFDocument.create();
    const [page] = await doc.copyPages(src, [i]);
    doc.addPage(page);
    outs.push(await doc.save());
  }
  return outs;
}

export async function rotatePdf(input: Uint8Array, angle: number): Promise<Uint8Array> {
  const doc = await loadDoc(input);
  const { degrees } = await import("pdf-lib");
  const rot = degrees(((angle % 360) + 360) % 360);
  for (const page of doc.getPages()) page.setRotation(rot);
  return doc.save();
}

export async function protectPdf(input: Uint8Array, password: string): Promise<Uint8Array> {
  return encryptPDF(input, password, {
    ownerPassword: password,
    algorithm: "AES-256",
    allowPrinting: true,
    allowModifying: true,
    allowCopying: true,
    allowAnnotating: true,
    allowFillingForms: true,
    allowExtraction: true,
    allowAssembly: true,
    allowHighQualityPrint: true,
  });
}

export async function unlockPdf(input: Uint8Array, password: string): Promise<Uint8Array> {
  const info = await isEncrypted(input);
  if (!info.encrypted) return input;
  return decryptPDF(input, password);
}

export async function imagesToPdf(images: { bytes: Uint8Array; ext: string }[]): Promise<Uint8Array> {
  const doc = await PDFDocument.create();
  for (const img of images) {
    let size: { width: number; height: number } | undefined;
    if (img.ext === "jpg") {
      const embedded = await doc.embedJpg(img.bytes);
      size = { width: embedded.width, height: embedded.height };
      const page = doc.addPage([size.width, size.height]);
      page.drawImage(embedded, { x: 0, y: 0, width: size.width, height: size.height });
    } else if (img.ext === "png") {
      const embedded = await doc.embedPng(img.bytes);
      size = { width: embedded.width, height: embedded.height };
      const page = doc.addPage([size.width, size.height]);
      page.drawImage(embedded, { x: 0, y: 0, width: size.width, height: size.height });
    } else {
      throw new Error(`Unsupported image for PDF: ${img.ext}`);
    }
  }
  return doc.save();
}

async function renderPage(
  page: PDFPageProxy,
  scale: number,
): Promise<{ canvas: HTMLCanvasElement; viewport: PageViewport }> {
  const viewport = page.getViewport({ scale });
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.floor(viewport.width));
  canvas.height = Math.max(1, Math.floor(viewport.height));
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas 2D context unavailable");
  await page.render({ canvasContext: ctx, viewport }).promise;
  return { canvas, viewport };
}

async function renderToBlob(
  canvas: HTMLCanvasElement,
  format: "png" | "jpg",
  quality: number,
): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (b) => (b ? resolve(b) : reject(new Error("Rendering produced no image"))),
      format === "png" ? "image/png" : "image/jpeg",
      quality,
    );
  });
}

export async function pdfToImages(
  input: Uint8Array,
  opts: { format: "png" | "jpg"; scale: number; quality: number },
  onPage?: (done: number, total: number) => void,
): Promise<PagedImage[]> {
  const { openPdf } = await loadPdfjs();
  const pdf = await openPdf(input);
  const out: PagedImage[] = [];
  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i);
    const { canvas } = await renderPage(page, opts.scale);
    out.push({ page: i, blob: await renderToBlob(canvas, opts.format, opts.quality) });
    onPage?.(i, pdf.numPages);
  }
  return out;
}

export async function pdfToText(input: Uint8Array): Promise<string[]> {
  const { openPdf } = await loadPdfjs();
  const pdf = await openPdf(input);
  const pages: string[] = [];
  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i);
    const content = await page.getTextContent();
    pages.push(
      content.items
        .map((item) => ("str" in item && typeof item.str === "string" ? item.str : ""))
        .join(" "),
    );
  }
  return pages;
}

export async function compressPdf(
  input: Uint8Array,
  opts: CompressOptions,
  onPage?: (done: number, total: number) => void,
): Promise<Uint8Array> {
  const { openPdf } = await loadPdfjs();
  const pdf = await openPdf(input);
  const out = await PDFDocument.create();
  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i);
    const { canvas, viewport } = await renderPage(page, opts.scale);
    const blob = await renderToBlob(canvas, "jpg", opts.quality);
    const jpg = await out.embedJpg(new Uint8Array(await blob.arrayBuffer()));
    const np = out.addPage([viewport.width, viewport.height]);
    np.drawImage(jpg, { x: 0, y: 0, width: viewport.width, height: viewport.height });
    onPage?.(i, pdf.numPages);
  }
  return out.save();
}