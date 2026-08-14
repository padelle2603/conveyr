export interface SvgSize {
  w: number;
  h: number;
}

function stripUnit(value: string): number | undefined {
  const v = value.trim();
  const trimmed = /(px|pt|mm|cm|in)$/.test(v) ? v.slice(0, -2) : v;
  const n = Number.parseFloat(trimmed);
  if (!Number.isFinite(n) || n <= 0) return undefined;
  return Math.round(n);
}

export function svgSize(text: string): SvgSize | undefined {
  const width = /<svg[^>]*\bwidth="([^"]+)"/.exec(text);
  const height = /<svg[^>]*\bheight="([^"]+)"/.exec(text);
  if (width && height) {
    const w = stripUnit(width[1]);
    const h = stripUnit(height[1]);
    if (w && h) return { w, h };
  }
  const viewBox = /\bviewBox="\s*[\d.-]+\s+[\d.-]+\s+([\d.-]+)\s+([\d.-]+)"/.exec(text);
  if (viewBox) {
    const w = Math.round(Number.parseFloat(viewBox[1]));
    const h = Math.round(Number.parseFloat(viewBox[2]));
    if (w > 0 && h > 0) return { w, h };
  }
  return undefined;
}

export function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("Failed to render SVG"));
    img.src = src;
  });
}

export function canvasToBlob(
  canvas: HTMLCanvasElement,
  mime: string,
  quality?: number,
): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (b) => (b ? resolve(b) : reject(new Error("Rendering produced no image"))),
      mime,
      quality,
    );
  });
}

const MIME_FOR: Record<string, string> = {
  png: "image/png",
  jpg: "image/jpeg",
  webp: "image/webp",
  bmp: "image/bmp",
  tiff: "image/tiff",
  gif: "image/gif",
};

export async function svgToRaster(svgText: string, target: string): Promise<Blob> {
  const mime = MIME_FOR[target];
  if (!mime) throw new Error(`Unsupported target: ${target}`);
  const url = URL.createObjectURL(new Blob([svgText], { type: "image/svg+xml" }));
  try {
    const img = await loadImage(url);
    const scale = 2;
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(img.width * scale));
    canvas.height = Math.max(1, Math.round(img.height * scale));
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("Canvas 2D context unavailable");
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    return await canvasToBlob(canvas, mime, target === "png" || target === "bmp" ? undefined : 0.92);
  } finally {
    URL.revokeObjectURL(url);
  }
}