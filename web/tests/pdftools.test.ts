import { describe, expect, it } from "vitest";
import { runPdfTool } from "../src/tools/pdftools";
import { blobPart, fixture, makePdf } from "./helpers";

function pdfFile(name: string, bytes: Uint8Array): File {
  return new File([blobPart(bytes)], name, { type: "application/pdf" });
}

function imageFile(name: string): File {
  return new File([blobPart(fixture(name))], name);
}

describe("runPdfTool", () => {
  it("merge combines PDFs in order", async () => {
    const a = pdfFile("a.pdf", await makePdf(1));
    const b = pdfFile("b.pdf", await makePdf(2));
    const outs = await runPdfTool("merge", [a, b]);
    expect(outs.length).toBe(1);
    expect(outs[0].name).toBe("a-merged.pdf");
    expect(outs[0].blob.size).toBeGreaterThan(0);
  });

  it("merge requires at least two PDFs", async () => {
    await expect(runPdfTool("merge", [pdfFile("a.pdf", await makePdf(1))])).rejects.toThrow();
  });

  it("split produces one file per page", async () => {
    const src = pdfFile("doc.pdf", await makePdf(3));
    const outs = await runPdfTool("split", [src]);
    expect(outs.map((o) => o.name)).toEqual([
      "doc-page-1.pdf",
      "doc-page-2.pdf",
      "doc-page-3.pdf",
    ]);
  });

  it("rotate names the output with the angle", async () => {
    const src = pdfFile("doc.pdf", await makePdf(1));
    const outs = await runPdfTool("rotate", [src], { angle: 270 });
    expect(outs[0].name).toBe("doc-rotated270.pdf");
  });

  it("protect requires a password", async () => {
    const src = pdfFile("doc.pdf", await makePdf(1));
    await expect(runPdfTool("protect", [src], { password: "" })).rejects.toThrow();
  });

  it("protect then unlock round-trips", async () => {
    const src = pdfFile("doc.pdf", await makePdf(1));
    const protectedOut = await runPdfTool("protect", [src], { password: "secret" });
    const enc = new Uint8Array(await protectedOut[0].blob.arrayBuffer());
    const unlockedOut = await runPdfTool("unlock", [pdfFile("enc.pdf", enc)], {
      password: "secret",
    });
    expect(unlockedOut[0].name).toBe("enc-unlocked.pdf");
    expect(unlockedOut[0].blob.size).toBeGreaterThan(0);
  });

  it("from-images combines images into a PDF", async () => {
    const outs = await runPdfTool("from-images", [imageFile("src.png"), imageFile("src.jpg")]);
    expect(outs.length).toBe(1);
    expect(outs[0].name).toBe("src.pdf");
    expect(outs[0].blob.size).toBeGreaterThan(0);
  });

  it("from-images needs at least one image", async () => {
    await expect(runPdfTool("from-images", [])).rejects.toThrow();
  });
});