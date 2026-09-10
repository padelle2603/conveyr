import { describe, it, expect, vi, afterEach } from "vitest";
import {
  RASTER,
  VECTOR,
  VIDEO,
  AUDIO,
  ALL,
  canonical,
  categoryOf,
  isSupported,
  validTargets,
  listFormats,
  detect,
  MIME,
} from "../src/formats";

describe("formats: constants", () => {
  it("exposes category lists", () => {
    expect(RASTER).toContain("jpg");
    expect(RASTER).toContain("png");
    expect(VECTOR).toEqual(["svg"]);
    expect(VIDEO).toContain("mp4");
    expect(AUDIO).toContain("mp3");
  });

  it("ALL unions everything plus gif", () => {
    expect([...RASTER, ...VECTOR, ...VIDEO, ...AUDIO, "gif"]).toEqual([...ALL]);
  });
});

describe("formats: canonical", () => {
  it("normalizes extension aliases", () => {
    expect(canonical("jpeg")).toBe("jpg");
    expect(canonical("tif")).toBe("tiff");
    expect(canonical("mpeg")).toBe("mpg");
    expect(canonical("m4v")).toBe("mp4");
    expect(canonical("oga")).toBe("ogg");
  });

  it("strips leading dot and lowercases", () => {
    expect(canonical(".PNG")).toBe("png");
    expect(canonical(".Jpeg")).toBe("jpg");
  });

  it("returns input for unknown extension", () => {
    expect(canonical("exotic")).toBe("exotic");
  });

  it("handles empty", () => {
    expect(canonical("")).toBe("");
    expect(canonical(null as unknown as string)).toBe("");
  });
});

describe("formats: categoryOf", () => {
  it("maps known extensions", () => {
    expect(categoryOf("jpg")).toBe("image");
    expect(categoryOf("svg")).toBe("vector");
    expect(categoryOf("gif")).toBe("gif");
    expect(categoryOf("mp4")).toBe("video");
    expect(categoryOf("mp3")).toBe("audio");
  });

  it("returns undefined for unknown", () => {
    expect(categoryOf("xyz")).toBeUndefined();
  });
});

describe("formats: isSupported", () => {
  it("accepts known extensions", () => {
    expect(isSupported("png")).toBe(true);
    expect(isSupported("webm")).toBe(true);
  });

  it("rejects unknown", () => {
    expect(isSupported("txt")).toBe(false);
  });
});

describe("formats: validTargets", () => {
  it("image targets exclude source", () => {
    const targets = validTargets("jpg");
    expect(targets).toContain("png");
    expect(targets).toContain("svg");
    expect(targets).toContain("gif");
    expect(targets).not.toContain("jpg");
  });

  it("video targets exclude source but include gif", () => {
    const targets = validTargets("mp4");
    expect(targets).toContain("webm");
    expect(targets).toContain("gif");
    expect(targets).not.toContain("mp4");
  });

  it("audio targets exclude source", () => {
    const targets = validTargets("mp3");
    expect(targets).toContain("flac");
    expect(targets).not.toContain("mp3");
  });

  it("returns empty for unknown", () => {
    expect(validTargets("txt")).toEqual([]);
  });
});

describe("formats: listFormats", () => {
  it("covers all known formats", () => {
    const fmts = listFormats();
    for (const ext of ALL) {
      expect(fmts[ext]).toBeDefined();
    }
  });
});

describe("formats: MIME", () => {
  it("maps common MIME types", () => {
    expect(MIME.jpg).toBe("image/jpeg");
    expect(MIME.png).toBe("image/png");
    expect(MIME.mp4).toBe("video/mp4");
    expect(MIME.mp3).toBe("audio/mpeg");
  });
});

describe("formats: detect", () => {
  function fakeFile(bytes: Uint8Array, name: string): File {
    return {
      name,
      slice: () =>
        new Blob([bytes]).slice(0, 8192) as unknown as Blob & { arrayBuffer: () => Promise<ArrayBuffer> },
      arrayBuffer: () => Promise.resolve(bytes.buffer),
    } as unknown as File;
  }

  it("detects PNG by magic bytes", async () => {
    const f = fakeFile(new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 1, 2]), "img");
    expect(await detect(f)).toBe("png");
  });

  it("detects JPEG by magic bytes", async () => {
    const f = fakeFile(new Uint8Array([0xff, 0xd8, 0xff, 0xe0, 1, 2, 3]), "photo");
    expect(await detect(f)).toBe("jpg");
  });

  it("detects GIF", async () => {
    const head = new TextEncoder().encode("GIF89a");
    const f = fakeFile(head, "anim");
    expect(await detect(f)).toBe("gif");
  });

  it("detects WebP", async () => {
    const f = fakeFile(new Uint8Array([0x52, 0x49, 0x46, 0x46, 0, 0, 0, 0, 0x57, 0x45, 0x42, 0x50]), "pic");
    expect(await detect(f)).toBe("webp");
  });

  it("detects MP3", async () => {
    const f = fakeFile(new Uint8Array([0x49, 0x44, 0x33, 4, 0]), "track");
    expect(await detect(f)).toBe("mp3");
  });

  it("falls back to extension when bytes are unknown", async () => {
    const f = fakeFile(new TextEncoder().encode("plain text"), "doc.png");
    expect(await detect(f)).toBe("png");
  });

  it("returns undefined for unknown bytes and extension", async () => {
    const f = fakeFile(new TextEncoder().encode("plain text"), "doc.xyz");
    expect(await detect(f)).toBeUndefined();
  });

  it("detects FLAC", async () => {
    const f = fakeFile(new TextEncoder().encode("fLaC data"), "audio");
    expect(await detect(f)).toBe("flac");
  });
});