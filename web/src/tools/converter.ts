import { CATEGORY, MIME, validTargets } from "../formats";
import { toAB } from "../download";
import { runFFmpeg, type FFmpegLog } from "../engines/ffmpeg";
import { magickConvert, magickThresholdGray } from "../engines/magick";
import { rasterToSvg } from "../engines/potrace";
import { svgToRaster } from "../engines/svg";

export interface ConvertOptions {
  fps?: number;
  width?: number;
  crf?: number;
  threshold?: number;
  bitrate?: number;
  onLog?: FFmpegLog;
}

const GIF_VIDEO_ARGS: Record<string, string[]> = {
  mp4: ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart"],
  mov: ["-c:v", "libx264", "-pix_fmt", "yuv420p"],
  webm: ["-c:v", "libvpx-vp9", "-b:v", "0"],
  mkv: ["-c:v", "libx264", "-pix_fmt", "yuv420p"],
  avi: ["-c:v", "libx264", "-pix_fmt", "yuv420p"],
  mpg: ["-c:v", "mpeg2video", "-qscale:v", "3"],
};

const VIDEO_CODECS: Record<string, { v: string; a: string; vextra: string[] }> = {
  mp4: { v: "libx264", a: "aac", vextra: ["-pix_fmt", "yuv420p", "-movflags", "+faststart"] },
  mov: { v: "libx264", a: "aac", vextra: ["-pix_fmt", "yuv420p"] },
  webm: { v: "libvpx-vp9", a: "libopus", vextra: ["-b:v", "0"] },
  mkv: { v: "libx264", a: "libopus", vextra: ["-pix_fmt", "yuv420p"] },
  avi: { v: "libx264", a: "libmp3lame", vextra: ["-pix_fmt", "yuv420p"] },
  mpg: { v: "mpeg2video", a: "mp2", vextra: ["-qscale:v", "3"] },
};

async function gifToVideo(file: Blob, target: string, opts: ConvertOptions): Promise<Blob> {
  const args = [...GIF_VIDEO_ARGS[target]];
  if (target === "webm") args.push("-crf", String(opts.crf ?? 31));
  const { files } = await runFFmpeg(file, args, [`out.${target}`], opts.onLog);
  const data = files.find((f) => f.name === `out.${target}`);
  if (!data) throw new Error(`ffmpeg produced no output for ${target}`);
  return new Blob([toAB(data.data)], { type: MIME[target] });
}

async function videoToGif(file: Blob, opts: ConvertOptions): Promise<Blob> {
  let fps = Math.round(opts.fps ?? 10);
  let width = Math.round(opts.width ?? 480);
  if (fps < 1 || fps > 60) fps = 10;
  if (width < 16 || width > 10000) width = 480;
  const vf =
    `fps=${fps},scale=${width}:-1:flags=lanczos,` +
    "split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse";
  const { files } = await runFFmpeg(file, ["-vf", vf, "-loop", "0"], ["out.gif"], opts.onLog);
  const data = files.find((f) => f.name === "out.gif");
  if (!data) throw new Error("ffmpeg produced no output for gif");
  return new Blob([toAB(data.data)], { type: MIME.gif });
}

async function videoToVideo(file: Blob, target: string, opts: ConvertOptions): Promise<Blob> {
  const codec = VIDEO_CODECS[target];
  if (!codec) throw new Error(`Unsupported target: ${target}`);
  const args = ["-c:v", codec.v];
  const crf = opts.crf;
  if (crf !== undefined && (codec.v === "libx264" || codec.v === "libvpx-vp9")) {
    args.push("-crf", String(Math.round(crf)));
  }
  args.push(...codec.vextra, "-c:a", codec.a, "-b:a", target === "webm" ? "128k" : "192k");
  const { files } = await runFFmpeg(file, args, [`out.${target}`], opts.onLog);
  const data = files.find((f) => f.name === `out.${target}`);
  if (!data) throw new Error(`ffmpeg produced no output for ${target}`);
  return new Blob([toAB(data.data)], { type: MIME[target] });
}

const AUDIO_CODECS: Record<string, { a: string; vqscale?: string; defaultBitrate?: string }> = {
  wav: { a: "pcm_s16le" },
  mp3: { a: "libmp3lame", vqscale: "2" },
  flac: { a: "flac" },
  ogg: { a: "libvorbis", vqscale: "4" },
  m4a: { a: "aac", defaultBitrate: "192k" },
  aac: { a: "aac", defaultBitrate: "192k" },
  opus: { a: "libopus", defaultBitrate: "128k" },
};

async function audioToAudio(file: Blob, target: string, opts: ConvertOptions): Promise<Blob> {
  const codec = AUDIO_CODECS[target];
  if (!codec) throw new Error(`Unsupported target: ${target}`);
  const bitrate = opts.bitrate !== undefined ? `${Math.round(opts.bitrate)}k` : undefined;
  const args = ["-vn"];
  if (codec.a === "libmp3lame" || codec.a === "libvorbis") {
    args.push("-c:a", codec.a);
    if (bitrate) args.push("-b:a", bitrate);
    else if (codec.vqscale) args.push("-qscale:a", codec.vqscale);
  } else if (codec.a === "pcm_s16le" || codec.a === "flac") {
    args.push("-c:a", codec.a);
  } else {
    args.push("-c:a", codec.a, "-b:a", bitrate ?? codec.defaultBitrate!);
  }
  const { files } = await runFFmpeg(file, args, [`out.${target}`], opts.onLog);
  const data = files.find((f) => f.name === `out.${target}`);
  if (!data) throw new Error(`ffmpeg produced no output for ${target}`);
  return new Blob([toAB(data.data)], { type: MIME[target] });
}

export async function convertFile(
  file: Blob,
  srcExt: string,
  target: string,
  opts: ConvertOptions = {},
): Promise<Blob> {
  if (!validTargets(srcExt).includes(target)) {
    throw new Error(`Cannot convert ${srcExt} to ${target}`);
  }
  const srcCat = CATEGORY[srcExt];
  const tgtCat = CATEGORY[target];

  if (srcCat === "vector") {
    return svgToRaster(await file.text(), target);
  }
  if (target === "svg") {
    const input = new Uint8Array(await file.arrayBuffer());
    const bw = await magickThresholdGray(input, opts.threshold ?? 50);
    const svg = await rasterToSvg(bw);
    return new Blob([svg], { type: MIME.svg });
  }
  if (tgtCat === "image" || target === "gif") {
    const input = new Uint8Array(await file.arrayBuffer());
    const data = await magickConvert(input, target);
    return new Blob([toAB(data)], { type: MIME[target] });
  }
  if (srcCat === "gif" && tgtCat === "video") return gifToVideo(file, target, opts);
  if (srcCat === "video" && target === "gif") return videoToGif(file, opts);
  if (srcCat === "video" && tgtCat === "video") return videoToVideo(file, target, opts);
  if (srcCat === "audio" && tgtCat === "audio") return audioToAudio(file, target, opts);

  throw new Error(`No conversion path from ${srcExt} to ${target}`);
}