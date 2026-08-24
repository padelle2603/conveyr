import { CATEGORY } from "../formats";
import { OutFile, formatBytes, stem, toAB } from "../download";
import { runFFmpeg, type FFmpegLog } from "../engines/ffmpeg";

export const VIDEO_TOOLS = [
  "trim",
  "crop",
  "rotate",
  "resize",
  "speed",
  "mute",
  "extract-audio",
  "extract-frame",
] as const;

export type VideoTool = (typeof VIDEO_TOOLS)[number];

export const VIDEO_TOOL_LABELS: Record<VideoTool, string> = {
  trim: "Trim video",
  crop: "Crop video",
  rotate: "Rotate / flip",
  resize: "Resize video",
  speed: "Change speed",
  mute: "Mute (remove audio)",
  "extract-audio": "Extract audio",
  "extract-frame": "Extract frame",
};

export const VIDEO_TOOL_HINTS: Record<VideoTool, string> = {
  trim: "Cut a portion of the video by start time and duration (fast, lossless).",
  crop: "Crop the video to a rectangle defined by offset and size.",
  rotate: "Rotate the video 90/180/270 degrees and optionally flip it.",
  resize: "Scale the video to a target width, keeping the aspect ratio.",
  speed: "Speed up (factor > 1) or slow down (factor < 1) playback.",
  mute: "Remove the audio track, keeping the video as-is.",
  "extract-audio": "Save the audio track as an .m4a file.",
  "extract-frame": "Grab a single image snapshot at the given timestamp.",
};

export type VideoToolFieldType = "text" | "int" | "angle" | "check";

export interface VideoToolField {
  key: string;
  label: string;
  type: VideoToolFieldType;
  placeholder?: string;
  default?: string;
}

export const VIDEO_TOOL_FIELDS: Record<VideoTool, VideoToolField[]> = {
  trim: [
    { key: "start", label: "Start (s or HH:MM:SS)", type: "text", placeholder: "0" },
    { key: "duration", label: "Duration (s or HH:MM:SS)", type: "text", placeholder: "e.g. 30" },
  ],
  crop: [
    { key: "x", label: "X offset (px)", type: "int", placeholder: "0" },
    { key: "y", label: "Y offset (px)", type: "int", placeholder: "0" },
    { key: "width", label: "Width (px)", type: "int", placeholder: "" },
    { key: "height", label: "Height (px)", type: "int", placeholder: "" },
  ],
  rotate: [
    { key: "angle", label: "Angle", type: "angle", default: "90" },
    { key: "flip_h", label: "Flip horizontally", type: "check" },
    { key: "flip_v", label: "Flip vertically", type: "check" },
  ],
  resize: [{ key: "width", label: "Width (px)", type: "int", placeholder: "" }],
  speed: [{ key: "factor", label: "Speed factor (0.25-4)", type: "text", placeholder: "2" }],
  mute: [],
  "extract-audio": [],
  "extract-frame": [{ key: "time", label: "Time (s or HH:MM:SS)", type: "text", placeholder: "0" }],
};

export interface VideoToolOptions {
  onLog?: FFmpegLog;
  [key: string]: string | boolean | undefined | FFmpegLog;
}

function parseTime(value: string): number {
  const text = (value ?? "").trim();
  if (!text) return 0;
  if (text.includes(":")) {
    const parts = text.split(":").map(Number);
    let seconds = 0;
    for (const p of parts) seconds = seconds * 60 + (Number.isFinite(p) ? p : 0);
    return seconds;
  }
  const n = Number.parseFloat(text);
  return Number.isFinite(n) ? n : 0;
}

function atempoChain(factor: number): string {
  let remaining = factor;
  const parts: string[] = [];
  while (remaining > 2.0) {
    parts.push("atempo=2.0");
    remaining /= 2.0;
  }
  while (remaining < 0.5) {
    parts.push("atempo=0.5");
    remaining *= 2.0;
  }
  parts.push(`atempo=${remaining.toFixed(4)}`);
  return parts.join(",");
}

function srcExt(name: string): string {
  return name.split(".").pop() ?? "mp4";
}

export function isVideoName(name: string): boolean {
  const ext = name.split(".").pop()?.toLowerCase() ?? "";
  return ext in CATEGORY && CATEGORY[ext] === "video";
}

export async function runVideoTool(
  tool: VideoTool,
  files: File[],
  opts: VideoToolOptions = {},
): Promise<OutFile[]> {
  if (files.length !== 1) throw new Error("Video tools work on a single video file");
  const file = files[0];
  if (!isVideoName(file.name)) throw new Error("Not a supported video file");

  const ext = srcExt(file.name);

  switch (tool) {
    case "trim": {
      const start = parseTime(String(opts.start ?? "0"));
      const duration = parseTime(String(opts.duration ?? "0"));
      if (start < 0) throw new Error("Start time must be >= 0");
      if (duration <= 0) throw new Error("Duration must be greater than 0");
      return runSimple(
        file,
        ["-ss", start.toFixed(3), "-t", duration.toFixed(3), "-c", "copy"],
        `out.${ext}`,
        `${stem(file.name)}-trimmed.${ext}`,
        opts.onLog,
      );
    }
    case "crop": {
      const x = clampInt(opts.x, 0);
      const y = clampInt(opts.y, 0);
      const width = Number.parseInt(String(opts.width ?? ""), 10);
      const height = Number.parseInt(String(opts.height ?? ""), 10);
      if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0)
        throw new Error("Crop needs a width and height greater than 0");
      return runSimple(
        file,
        ["-vf", `crop=${width}:${height}:${x}:${y}`, "-c:a", "copy"],
        `out.${ext}`,
        `${stem(file.name)}-cropped.${ext}`,
        opts.onLog,
      );
    }
    case "rotate": {
      const angle = String(opts.angle ?? "90");
      const transpose =
        angle === "90" ? "transpose=1" : angle === "180" ? "transpose=2,transpose=2" : "transpose=2";
      const filters = [transpose];
      if (opts.flip_h) filters.push("hflip");
      if (opts.flip_v) filters.push("vflip");
      return runSimple(
        file,
        ["-vf", filters.join(","), "-c:a", "copy"],
        `out.${ext}`,
        `${stem(file.name)}-rotated${angle}.${ext}`,
        opts.onLog,
      );
    }
    case "resize": {
      const width = Number.parseInt(String(opts.width ?? ""), 10);
      if (!Number.isFinite(width) || width <= 0) throw new Error("Resize needs a width greater than 0");
      return runSimple(
        file,
        ["-vf", `scale=${width}:-2`, "-c:a", "copy"],
        `out.${ext}`,
        `${stem(file.name)}-${width}w.${ext}`,
        opts.onLog,
      );
    }
    case "speed": {
      const factor = Number.parseFloat(String(opts.factor ?? ""));
      if (!Number.isFinite(factor) || factor <= 0) throw new Error("Speed needs a factor greater than 0");
      const f = Math.max(0.25, Math.min(4.0, factor));
      const vfilter = `setpts=${(1 / f).toFixed(4)}*PTS`;
      const afilter = atempoChain(f);
      const args = ["-filter:v", vfilter];
      if (afilter) args.push("-filter:a", afilter);
      else args.push("-an");
      return runSimple(
        file,
        args,
        `out.${ext}`,
        `${stem(file.name)}-x${f}.${ext}`,
        opts.onLog,
      );
    }
    case "mute": {
      return runSimple(
        file,
        ["-c:v", "copy", "-an"],
        `out.${ext}`,
        `${stem(file.name)}-muted.${ext}`,
        opts.onLog,
      );
    }
    case "extract-audio": {
      const { files: out } = await runFFmpeg(file, ["-vn", "-c:a", "aac"], ["out.m4a"], opts.onLog);
      const data = out.find((f) => f.name === "out.m4a");
      if (!data) throw new Error("ffmpeg produced no output");
      opts.onLog?.(`Extracted audio (${formatBytes(data.data.length)})`);
      return [{ blob: new Blob([toAB(data.data)], { type: "audio/mp4" }), name: `${stem(file.name)}-audio.m4a` }];
    }
    case "extract-frame": {
      const time = parseTime(String(opts.time ?? "0"));
      const { files: out } = await runFFmpeg(
        file,
        ["-ss", time.toFixed(3), "-frames:v", "1", "-q:v", "2"],
        ["out.png"],
        opts.onLog,
      );
      const data = out.find((f) => f.name === "out.png");
      if (!data) throw new Error("ffmpeg produced no output");
      opts.onLog?.(`Extracted frame (${formatBytes(data.data.length)})`);
      return [{ blob: new Blob([toAB(data.data)], { type: "image/png" }), name: `${stem(file.name)}-frame.png` }];
    }
    default:
      throw new Error(`Unknown video tool: ${tool}`);
  }
}

function clampInt(value: unknown, fallback: number): number {
  const n = Number.parseInt(String(value ?? ""), 10);
  return Number.isFinite(n) ? n : fallback;
}

async function runSimple(
  file: File,
  args: string[],
  outName: string,
  displayName: string,
  onLog?: FFmpegLog,
): Promise<OutFile[]> {
  const { files: out } = await runFFmpeg(file, args, [outName], onLog);
  const data = out.find((f) => f.name === outName);
  if (!data) throw new Error("ffmpeg produced no output");
  onLog?.(`Done (${formatBytes(data.data.length)})`);
  return [{ blob: new Blob([toAB(data.data)]), name: displayName }];
}

export function videoToolAcceptsVideo(tool: VideoTool): boolean {
  return VIDEO_TOOLS.includes(tool);
}
