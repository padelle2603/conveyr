import { describe, expect, it } from "vitest";
import { PDFDocument } from "pdf-lib";
import { isEncrypted } from "@pdfsmaller/pdf-decrypt";
import { getDocument } from "pdfjs-dist/legacy/build/pdf.mjs";
import {
  imagesToPdf,
  mergePdfs,
  protectPdf,
  rotatePdf,
  splitPdf,
  unlockPdf,
} from "../src/engines/pdf";
import { fixture, makePdf } from "./helpers";

async function pageCount(bytes: Uint8Array): Promise<number> {
  const doc = await PDFDocument.load(bytes);
  return doc.getPageCount();
}

describe("pdf-lib tools", () => {
  it("merges multiple PDFs preserving order", async () => {
    const a = await makePdf(1);
    const b = await makePdf(2);
    const merged = await mergePdfs([a, b]);
    expect(await pageCount(merged)).toBe(3);
  });

  it("splits a PDF into one file per page", async () => {
    const src = await makePdf(3);
    const parts = await splitPdf(src);
    expect(parts.length).toBe(3);
    for (const part of parts) expect(await pageCount(part)).toBe(1);
  });

  it("rotates every page by the requested angle", async () => {
    const src = await makePdf(1);
    const rotated = await rotatePdf(src, 90);
    const doc = await PDFDocument.load(rotated);
    expect(doc.getPage(0).getRotation().angle).toBe(90);
  });

  it("builds a PDF from images preserving order", async () => {
    const png = fixture("src.png");
    const jpg = fixture("src.jpg");
    const out = await imagesToPdf([
      { bytes: png, ext: "png" },
      { bytes: jpg, ext: "jpg" },
    ]);
    const doc = await PDFDocument.load(out);
    expect(doc.getPageCount()).toBe(2);
  });

  it("rejects unsupported image types", async () => {
    await expect(
      imagesToPdf([{ bytes: new Uint8Array([1, 2, 3]), ext: "webp" }]),
    ).rejects.toThrow();
  });
});

describe("protect / unlock", () => {
  it("encrypts with a password and decrypts back", async () => {
    const src = await makePdf(1);
    const encrypted = await protectPdf(src, "secret");
    expect((await isEncrypted(encrypted)).encrypted).toBe(true);

    const decrypted = await unlockPdf(encrypted, "secret");
    expect((await isEncrypted(decrypted)).encrypted).toBe(false);
    expect(await pageCount(decrypted)).toBe(1);
  });

  it("unlock is a no-op for an unencrypted PDF", async () => {
    const src = await makePdf(1);
    const out = await unlockPdf(src, "");
    expect(out).toEqual(src);
  });
});

describe("pdf.js text extraction", () => {
  it("extracts text from a generated PDF", async () => {
    const src = await makePdf(2, "conveyr test");
    const pdf = await getDocument({ data: src }).promise;
    expect(pdf.numPages).toBe(2);
    const page = await pdf.getPage(1);
    const content = await page.getTextContent();
    const text = content.items.map((i) => ("str" in i ? i.str : "")).join(" ");
    expect(text).toContain("conveyr");
  });
});