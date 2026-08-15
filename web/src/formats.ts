export const RASTER = ["jpg", "png", "webp", "bmp", "tiff"] as const;
export const VECTOR = ["svg"] as const;
export const VIDEO = ["mp4", "webm", "mkv", "avi", "mov", "mpg"] as const;
export const AUDIO = ["wav", "mp3", "flac", "ogg", "m4a", "aac", "opus"] as const;
export const ALL = [...RASTER, ...VECTOR, ...VIDEO, ...AUDIO, "gif"] as const;

export const ALIASES: Record<string, string> = {
  jpeg: "jpg",
  jpe: "jpg",
  tif: "tiff",
  mpeg: "mpg",
  m4v: "mp4",
  mp4v: "mp4",
  oga: "ogg",
  m4b: "m4a",
};

export type Category = "image" | "vector" | "gif" | "video" | "audio";

export const CATEGORY: Record<string, Category> = {
  jpg: "image",
  png: "image",
  webp: "image",
  bmp: "image",
  tiff: "image",
  svg: "vector",
  gif: "gif",
  mp4: "video",
  webm: "video",
  mkv: "video",
  avi: "video",
  mov: "video",
  mpg: "video",
  wav: "audio",
  mp3: "audio",
  flac: "audio",
  ogg: "audio",
  m4a: "audio",
  aac: "audio",
  opus: "audio",
};

export const CATEGORY_LABELS: Record<Category, string> = {
  image: "Images",
  vector: "Vector graphics",
  gif: "Animated GIF",
  video: "Video",
  audio: "Audio",
};

export function canonical(ext: string): string {
  if (!ext) return "";
  const e = ext.replace(/^\./, "").toLowerCase();
  return ALIASES[e] ?? e;
}

export function categoryOf(ext: string): Category | undefined {
  return CATEGORY[ext];
}

export function isSupported(ext: string): boolean {
  return ext in CATEGORY;
}

export function validTargets(srcExt: string): string[] {
  const cat = CATEGORY[srcExt];
  if (!cat) return [];
  const sorted = (list: string[]): string[] => [...list].sort();
  if (cat === "image") return sorted([...RASTER, "svg", "gif"].filter((e) => e !== srcExt));
  if (cat === "vector") return sorted([...RASTER, "gif"]);
  if (cat === "gif") return sorted([...RASTER, ...VIDEO]);
  if (cat === "video") return sorted([...VIDEO, "gif"].filter((e) => e !== srcExt));
  if (cat === "audio") return sorted(AUDIO.filter((e) => e !== srcExt));
  return [];
}

export function listFormats(): Record<string, string[]> {
  const order = [...ALL].sort(
    (a, b) =>
      CATEGORY_LABELS[CATEGORY[a]].localeCompare(CATEGORY_LABELS[CATEGORY[b]]) ||
      a.localeCompare(b),
  );
  const out: Record<string, string[]> = {};
  for (const ext of order) out[ext] = validTargets(ext);
  return out;
}

function isGifBytes(b: Uint8Array): boolean {
  const t = new TextDecoder().decode(b.slice(0, 6));
  return t === "GIF87a" || t === "GIF89a";
}

export async function detect(file: File): Promise<string | undefined> {
  const head = new Uint8Array(await file.slice(0, 8192).arrayBuffer());
  if (head[0] === 0x89 && head[1] === 0x50 && head[2] === 0x4e && head[3] === 0x47) return "png";
  if (head[0] === 0xff && head[1] === 0xd8 && head[2] === 0xff) return "jpg";
  if (isGifBytes(head)) return "gif";
  if (
    head[0] === 0x52 && head[1] === 0x49 && head[2] === 0x46 && head[3] === 0x46 &&
    head[8] === 0x57 && head[9] === 0x45 && head[10] === 0x42 && head[11] === 0x50
  ) {
    return "webp";
  }
  if (head[0] === 0x42 && head[1] === 0x4d) return "bmp";
  if (head[0] === 0x49 && head[1] === 0x49 && head[2] === 0x2a && head[3] === 0x00) return "tiff";
  if (head[0] === 0x4d && head[1] === 0x4d && head[2] === 0x00 && head[3] === 0x2a) return "tiff";
  if (head[0] === 0x52 && head[1] === 0x49 && head[2] === 0x46 && head[3] === 0x46 &&
    head[8] === 0x57 && head[9] === 0x41 && head[10] === 0x56 && head[11] === 0x45) {
    return "wav";
  }
  if (head[0] === 0x66 && head[1] === 0x4c && head[2] === 0x61 && head[3] === 0x43) return "flac";
  if (head[0] === 0x4f && head[1] === 0x67 && head[2] === 0x67 && head[3] === 0x53) {
    const ogg = new TextDecoder("utf-8", { fatal: false }).decode(head.slice(0, 64));
    return ogg.includes("OpusHead") ? "opus" : "ogg";
  }
  if (head[0] === 0x49 && head[1] === 0x44 && head[2] === 0x33) return "mp3";

  const lowered = new TextDecoder("utf-8", { fatal: false }).decode(head).toLowerCase();
  if (lowered.includes("<svg") || (lowered.trimStart().startsWith("<?xml") && lowered.includes("<svg"))) {
    return "svg";
  }

  const ext = canonical(file.name.split(".").pop() ?? "");
  return CATEGORY[ext] ? ext : undefined;
}

export const MIME: Record<string, string> = {
  jpg: "image/jpeg",
  png: "image/png",
  webp: "image/webp",
  bmp: "image/bmp",
  tiff: "image/tiff",
  gif: "image/gif",
  svg: "image/svg+xml",
  mp4: "video/mp4",
  webm: "video/webm",
  mkv: "video/x-matroska",
  avi: "video/x-msvideo",
  mov: "video/quicktime",
  mpg: "video/mpeg",
  wav: "audio/wav",
  mp3: "audio/mpeg",
  flac: "audio/flac",
  ogg: "audio/ogg",
  m4a: "audio/mp4",
  aac: "audio/aac",
  opus: "audio/opus",
};