import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { PDFDocument, StandardFonts } from "pdf-lib";
import { initMagickWithBytes } from "../src/engines/magick";

const here = dirname(fileURLToPath(import.meta.url));

let magickReady: Promise<void> | null = null;

export function ensureMagick(): Promise<void> {
  if (!magickReady) {
    const wasm = readFileSync(join(here, "../node_modules/@imagemagick/magick-wasm/dist/magick.wasm"));
    magickReady = initMagickWithBytes(new Uint8Array(wasm));
  }
  return magickReady;
}

export function fixture(name: string): Uint8Array {
  return new Uint8Array(readFileSync(join(here, "fixtures", name)));
}

export function blobPart(bytes: Uint8Array): Uint8Array<ArrayBuffer> {
  const ab = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer;
  return new Uint8Array(ab);
}

export async function makePdf(pages: number, text?: string): Promise<Uint8Array> {
  const doc = await PDFDocument.create();
  const font = await doc.embedFont(StandardFonts.Helvetica);
  for (let i = 0; i < pages; i++) {
    const page = doc.addPage([200, 200]);
    if (text) {
      page.drawText(text, { x: 20, y: 100 + i * 10, size: 12, font });
    }
  }
  return doc.save();
}