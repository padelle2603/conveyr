import {
  AlphaAction,
  ColorSpace,
  ImageMagick,
  MagickColor,
  MagickFormat,
  Percentage,
  initializeImageMagick,
} from "@imagemagick/magick-wasm";

const FORMAT: Record<string, MagickFormat> = {
  jpg: MagickFormat.Jpg,
  jpeg: MagickFormat.Jpg,
  png: MagickFormat.Png,
  webp: MagickFormat.WebP,
  bmp: MagickFormat.Bmp,
  tiff: MagickFormat.Tiff,
  gif: MagickFormat.Gif,
};

let initPromise: Promise<void> | null = null;

export function initMagickWithBytes(bytes: Uint8Array): Promise<void> {
  if (!initPromise) {
    initPromise = initializeImageMagick(bytes).catch((err) => {
      initPromise = null;
      throw err;
    });
  }
  return initPromise;
}

export function initMagick(): Promise<void> {
  if (!initPromise) {
    initPromise = (async () => {
      const url = `${import.meta.env.BASE_URL}magick/magick.wasm`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`magick.wasm fetch failed: ${res.status}`);
      await initializeImageMagick(new Uint8Array(await res.arrayBuffer()));
    })().catch((err) => {
      initPromise = null;
      throw err;
    });
  }
  return initPromise;
}

export async function magickConvert(input: Uint8Array, target: string): Promise<Uint8Array> {
  await initMagick();
  const fmt = FORMAT[target];
  if (!fmt) throw new Error(`Unsupported target format: ${target}`);
  return ImageMagick.read(input, (image) => image.write(fmt, (data) => data));
}

export async function magickThresholdGray(
  input: Uint8Array,
  thresholdPct: number,
): Promise<Uint8Array> {
  await initMagick();
  const pct = Math.max(0, Math.min(100, thresholdPct));
  return ImageMagick.read(input, (image) => {
    image.backgroundColor = new MagickColor("#ffffff");
    image.alpha(AlphaAction.Remove);
    image.alpha(AlphaAction.Off);
    image.colorSpace = ColorSpace.Gray;
    image.threshold(new Percentage(pct));
    return image.write(MagickFormat.Png, (data) => data);
  });
}

export function isImageFormat(ext: string): boolean {
  return ext in FORMAT;
}