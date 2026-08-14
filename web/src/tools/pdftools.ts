import { CATEGORY, MIME } from "../formats";
import { OutFile, formatBytes, stem, toAB } from "../download";
import {
  compressPdf,
  imagesToPdf,
  mergePdfs,
  pdfToImages,
  pdfToText,
  protectPdf,
  rotatePdf,
  splitPdf,
  unlockPdf,
} from "../engines/pdf";
import { magickConvert } from "../engines/magick";
import { svgToRaster } from "../engines/svg";

export const PDF_TOOLS = [
  "merge",
  "split",
  "compress",
  "rotate",
  "protect",
  "unlock",
  "to-images",
  "from-images",
  "to-text",
] as const;

export type PdfTool = (typeof PDF_TOOLS)[number];

export const PDF_TOOL_LABELS: Record<PdfTool, string> = {
  merge: "Merge PDFs",
  split: "Split PDF",
  compress: "Compress PDF",
  rotate: "Rotate PDF",
  protect: "Protect PDF",
  unlock: "Unlock PDF",
  "to-images": "PDF to Images",
  "from-images": "Images to PDF",
  "to-text": "PDF to Text",
};

export const PDF_TOOL_HINTS: Record<PdfTool, string> = {
  merge: "Combine several PDFs into a single document, in the order listed.",
  split: "Split a PDF into one file per page.",
  compress: "Rebuild the PDF with a quality preset. Pages are re-rendered to images, so the text becomes non-selectable.",
  rotate: "Rotate every page of a PDF clockwise by 90, 180 or 270 degrees.",
  protect: "Encrypt the PDF with a password (128-bit RC4 encryption).",
  unlock: "Remove the password protection from a PDF.",
  "to-images": "Render each page of a PDF to a PNG or JPG image.",
  "from-images": "Combine images into a single PDF, preserving the order listed.",
  "to-text": "Extract the text content of a PDF into a .txt file.",
};

export const COMPRESS_PRESETS = [
  { key: "screen", label: "Screen (72 dpi)", scale: 0.75, quality: 0.5 },
  { key: "ebook", label: "eBook (150 dpi)", scale: 1.56, quality: 0.7 },
  { key: "printer", label: "Printer (300 dpi)", scale: 3.12, quality: 0.9 },
] as const;

export interface PdfToolOptions {
  angle?: number;
  format?: "png" | "jpg";
  dpi?: number;
  preset?: string;
  password?: string;
  onLog?: (line: string) => void;
}

const IMAGE_EXTS = ["jpg", "jpeg", "png", "webp", "bmp", "tiff", "tif", "gif", "svg"];

export function isPdfName(name: string): boolean {
  const ext = name.split(".").pop()?.toLowerCase();
  return ext === "pdf";
}

export function isImageName(name: string): boolean {
  const ext = name.split(".").pop()?.toLowerCase();
  return IMAGE_EXTS.includes(ext ?? "");
}

function dpiToScale(dpi: number): number {
  return dpi / 96;
}

async function readBytes(file: File): Promise<Uint8Array> {
  return new Uint8Array(await file.arrayBuffer());
}

async function normalizeImage(file: File): Promise<{ bytes: Uint8Array; ext: string }> {
  const name = file.name.toLowerCase();
  if (/\.(jpe?g)$/.test(name)) return { bytes: await readBytes(file), ext: "jpg" };
  if (/\.png$/.test(name)) return { bytes: await readBytes(file), ext: "png" };
  if (/\.svg$/.test(name)) {
    const blob = await svgToRaster(await file.text(), "png");
    return { bytes: new Uint8Array(await blob.arrayBuffer()), ext: "png" };
  }
  const data = await magickConvert(await readBytes(file), "png");
  return { bytes: data, ext: "png" };
}

function uniqueName(name: string, used: Set<string>): string {
  let candidate = name;
  let i = 2;
  while (used.has(candidate)) {
    const dot = name.lastIndexOf(".");
    candidate = dot > 0 ? `${name.slice(0, dot)}-${i}${name.slice(dot)}` : `${name}-${i}`;
    i++;
  }
  used.add(candidate);
  return candidate;
}

export async function runPdfTool(
  tool: PdfTool,
  files: File[],
  opts: PdfToolOptions = {},
): Promise<OutFile[]> {
  const used = new Set<string>();
  const out = (blob: Blob, name: string): OutFile => ({
    blob,
    name: uniqueName(name, used),
  });

  switch (tool) {
    case "merge": {
      if (files.length < 2) throw new Error("Merge needs at least two PDFs");
      const inputs = await Promise.all(files.map(readBytes));
      const bytes = await mergePdfs(inputs);
      opts.onLog?.(`Merged ${inputs.length} PDFs (${formatBytes(bytes.length)})`);
      return [out(new Blob([toAB(bytes)], { type: "application/pdf" }), `${stem(files[0].name)}-merged.pdf`)];
    }
    case "split": {
      if (files.length !== 1) throw new Error("Split needs exactly one PDF");
      const bytes = await splitPdf(await readBytes(files[0]));
      opts.onLog?.(`Split into ${bytes.length} pages`);
      return bytes.map((b, i) =>
        out(new Blob([toAB(b)], { type: "application/pdf" }), `${stem(files[0].name)}-page-${i + 1}.pdf`),
      );
    }
    case "rotate": {
      if (files.length !== 1) throw new Error("Rotate needs exactly one PDF");
      const angle = opts.angle ?? 90;
      const bytes = await rotatePdf(await readBytes(files[0]), angle);
      opts.onLog?.(`Rotated every page by ${angle} degrees`);
      return [out(new Blob([toAB(bytes)], { type: "application/pdf" }), `${stem(files[0].name)}-rotated${angle}.pdf`)];
    }
    case "protect": {
      if (files.length !== 1) throw new Error("Protect needs exactly one PDF");
      const password = opts.password ?? "";
      if (!password) throw new Error("A password is required to protect the PDF");
      const bytes = await protectPdf(await readBytes(files[0]), password);
      opts.onLog?.("PDF encrypted");
      return [out(new Blob([toAB(bytes)], { type: "application/pdf" }), `${stem(files[0].name)}-protected.pdf`)];
    }
    case "unlock": {
      if (files.length !== 1) throw new Error("Unlock needs exactly one PDF");
      const bytes = await unlockPdf(await readBytes(files[0]), opts.password ?? "");
      opts.onLog?.("PDF decrypted");
      return [out(new Blob([toAB(bytes)], { type: "application/pdf" }), `${stem(files[0].name)}-unlocked.pdf`)];
    }
    case "to-images": {
      if (files.length !== 1) throw new Error("PDF to Images needs exactly one PDF");
      const format = opts.format ?? "png";
      const dpi = Math.max(36, Math.min(600, Math.round(opts.dpi ?? 150)));
      const pages = await pdfToImages(
        await readBytes(files[0]),
        { format, scale: dpiToScale(dpi), quality: 0.92 },
        (done, total) => opts.onLog?.(`Rendered page ${done}/${total}`),
      );
      return pages.map((p) =>
        out(
          new Blob([p.blob], { type: MIME[format] }),
          `${stem(files[0].name)}-${p.page}.${format}`,
        ),
      );
    }
    case "from-images": {
      if (files.length === 0) throw new Error("Need at least one image");
      const images = await Promise.all(files.map(normalizeImage));
      const bytes = await imagesToPdf(images);
      opts.onLog?.(`Built PDF from ${images.length} images (${formatBytes(bytes.length)})`);
      return [out(new Blob([toAB(bytes)], { type: "application/pdf" }), `${stem(files[0].name)}.pdf`)];
    }
    case "to-text": {
      if (files.length !== 1) throw new Error("PDF to Text needs exactly one PDF");
      const pages = await pdfToText(await readBytes(files[0]));
      const text = pages.map((p, i) => `--- page ${i + 1} ---\n${p}`).join("\n\n");
      opts.onLog?.(`Extracted text from ${pages.length} pages`);
      return [out(new Blob([text], { type: "text/plain" }), `${stem(files[0].name)}.txt`)];
    }
    case "compress": {
      if (files.length !== 1) throw new Error("Compress needs exactly one PDF");
      const preset =
        COMPRESS_PRESETS.find((p) => p.key === opts.preset) ?? COMPRESS_PRESETS[1];
      const bytes = await compressPdf(
        await readBytes(files[0]),
        { scale: preset.scale, quality: preset.quality },
        (done, total) => opts.onLog?.(`Compressed page ${done}/${total}`),
      );
      opts.onLog?.(`Compressed PDF (${formatBytes(bytes.length)})`);
      return [out(new Blob([toAB(bytes)], { type: "application/pdf" }), `${stem(files[0].name)}-compressed.pdf`)];
    }
    default:
      throw new Error(`Unknown PDF tool: ${tool}`);
  }
}

export function pdfToolNeedsPassword(tool: PdfTool): boolean {
  return tool === "protect" || tool === "unlock";
}

export function pdfToolAcceptsPdf(tool: PdfTool): boolean {
  return tool !== "from-images";
}

export function pdfToolAcceptsImages(tool: PdfTool): boolean {
  return tool === "from-images";
}

export function isImageExt(ext: string): boolean {
  const e = ext.replace(/^\./, "").toLowerCase();
  return e in CATEGORY && CATEGORY[e] !== "video";
}