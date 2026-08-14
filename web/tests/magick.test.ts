import { beforeAll, describe, expect, it } from "vitest";
import { magickConvert, magickThresholdGray } from "../src/engines/magick";
import { ensureMagick, fixture } from "./helpers";

function isPng(bytes: Uint8Array): boolean {
  return (
    bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4e && bytes[3] === 0x47
  );
}

function magic(bytes: Uint8Array): string {
  return `${bytes[0].toString(16)}${bytes[1].toString(16)}`;
}

describe("magick-wasm conversions", () => {
  beforeAll(async () => {
    await ensureMagick();
  });

  it("converts png to every raster target", async () => {
    const png = fixture("src.png");
    for (const target of ["jpg", "webp", "gif", "bmp", "tiff"]) {
      const out = await magickConvert(png, target);
      expect(out.length, target).toBeGreaterThan(0);
    }
  });

  it("reads gif, webp, tiff and bmp back to png", async () => {
    for (const src of ["gif", "webp", "tiff", "bmp"]) {
      const out = await magickConvert(fixture(`src.${src}`), "png");
      expect(isPng(out), src).toBe(true);
    }
  });

  it("converts jpg to png", async () => {
    const out = await magickConvert(fixture("src.jpg"), "png");
    expect(isPng(out)).toBe(true);
  });

  it("produces a valid jpeg (starts with ffd8)", async () => {
    const out = await magickConvert(fixture("src.png"), "jpg");
    expect(magic(out)).toBe("ffd8");
  });

  it("threshold + grayscale yields a small b/w png", async () => {
    const out = await magickThresholdGray(fixture("src.png"), 50);
    expect(isPng(out)).toBe(true);
    expect(out.length).toBeGreaterThan(0);
  });

  it("rejects unknown targets", async () => {
    await expect(magickConvert(fixture("src.png"), "xyz")).rejects.toThrow();
  });
});