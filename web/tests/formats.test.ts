import { describe, expect, it } from "vitest";
import {
  CATEGORY,
  CATEGORY_LABELS,
  RASTER,
  VIDEO,
  canonical,
  categoryOf,
  detect,
  isSupported,
  listFormats,
  validTargets,
} from "../src/formats";
import { blobPart, fixture } from "./helpers";

function bytesOf(name: string): Uint8Array {
  return fixture(name);
}

function fileOf(name: string): File {
  return new File([blobPart(bytesOf(name))], name);
}

describe("canonical", () => {
  it("normalizes extensions", () => {
    expect(canonical("JPG")).toBe("jpg");
    expect(canonical(".Jpeg")).toBe("jpg");
    expect(canonical("tif")).toBe("tiff");
    expect(canonical("m4v")).toBe("mp4");
    expect(canonical("pdf")).toBe("pdf");
    expect(canonical("")).toBe("");
  });
});

describe("categoryOf / isSupported", () => {
  it("classifies every supported format", () => {
    expect(CATEGORY.png).toBe("image");
    expect(CATEGORY.svg).toBe("vector");
    expect(CATEGORY.gif).toBe("gif");
    expect(CATEGORY.mp4).toBe("video");
  });

  it("knows category labels", () => {
    expect(CATEGORY_LABELS.image).toBe("Images");
    expect(CATEGORY_LABELS.video).toBe("Video");
  });

  it("rejects unknown formats", () => {
    expect(categoryOf("docx")).toBeUndefined();
    expect(isSupported("docx")).toBe(false);
  });
});

describe("validTargets", () => {
  it("image → raster + svg + gif, excluding self", () => {
    expect(validTargets("png")).toEqual(["bmp", "gif", "jpg", "svg", "tiff", "webp"]);
    expect(validTargets("jpg")).toEqual(["bmp", "gif", "png", "svg", "tiff", "webp"]);
  });

  it("vector → raster + gif", () => {
    expect(validTargets("svg")).toEqual(["bmp", "gif", "jpg", "png", "tiff", "webp"]);
  });

  it("gif → raster + video", () => {
    expect(validTargets("gif")).toEqual([
      "avi", "bmp", "jpg", "mkv", "mov", "mp4", "mpg", "png", "tiff", "webm", "webp",
    ]);
  });

  it("video → video + gif, excluding self", () => {
    expect(validTargets("mp4")).toEqual(["avi", "gif", "mkv", "mov", "mpg", "webm"]);
    expect(validTargets("webm")).toEqual(["avi", "gif", "mkv", "mov", "mp4", "mpg"]);
  });

  it("unknown format has no targets", () => {
    expect(validTargets("docx")).toEqual([]);
  });
});

describe("listFormats", () => {
  it("covers every supported format with non-empty targets", () => {
    const all = listFormats();
    const keys = Object.keys(all);
    expect(keys).toContain("jpg");
    expect(keys).toContain("svg");
    expect(keys).toContain("gif");
    expect(keys).toContain("mp4");
    for (const [ext, targets] of Object.entries(all)) {
      expect(targets.length, ext).toBeGreaterThan(0);
    }
  });

  it("matches the CLI matrix for every format", () => {
    const all = listFormats();
    for (const [ext, targets] of Object.entries(all)) {
      expect(validTargets(ext)).toEqual(targets);
    }
  });
});

describe("detect", () => {
  it("detects png by magic bytes", async () => {
    expect(await detect(fileOf("src.png"))).toBe("png");
  });
  it("detects jpg by magic bytes", async () => {
    expect(await detect(fileOf("src.jpg"))).toBe("jpg");
  });
  it("detects gif by magic bytes", async () => {
    expect(await detect(fileOf("src.gif"))).toBe("gif");
  });
  it("detects webp by magic bytes", async () => {
    expect(await detect(fileOf("src.webp"))).toBe("webp");
  });
  it("detects bmp by magic bytes", async () => {
    expect(await detect(fileOf("src.bmp"))).toBe("bmp");
  });
  it("detects tiff by magic bytes", async () => {
    expect(await detect(fileOf("src.tiff"))).toBe("tiff");
  });
  it("falls back to the extension for unsniffed formats", async () => {
    expect(await detect(fileOf("src.mp4"))).toBe("mp4");
  });
  it("returns undefined for unknown formats", async () => {
    expect(await detect(new File([new Uint8Array([1, 2, 3])], "file.xyz"))).toBeUndefined();
  });
  it("exposes the full CLI format set", () => {
    expect(RASTER).toContain("tiff");
    expect(VIDEO).toContain("mpg");
  });
});