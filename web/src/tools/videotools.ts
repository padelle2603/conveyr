import { CATEGORY } from "../formats";
import { OutFile, formatBytes, stem, toAB } from "../download";
import { runFFmpeg, type FFmpegLog } from "../engines/ffmpeg";

export const VIDEO_TOOLS = ["trim"] as const;

export type VideoTool = (typeof VIDEO_TOOLS)[number];

export const VIDEO_TOOL_LABELS: Record<VideoTool, string> = {
  trim: "Trim video",
};

export const VIDEO_TOOL_HINTS: Record<VideoTool, string> = {
  trim: "Cut a portion of the video by start time and duration (fast, lossless).",
};

export interface VideoToolOptions {
  start?: string;
  duration?: string;
  onLog?: FFmpegLog;
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

export function isVideoName(name: string): boolean {
  const ext = name.split(".").pop()?.toLowerCase() ?? "";
  return ext in CATEGORY && CATEGORY[ext] === "video";
}

export async function runVideoTool(
  tool: VideoTool,
  files: File[],
  opts: VideoToolOptions = {},
): Promise<OutFile[]> {
  if (tool === "trim") {
    if (files.length !== 1) throw new Error("Trim works on a single video file");
    const file = files[0];
    if (!isVideoName(file.name)) throw new Error("Not a supported video file");
    const start = parseTime(opts.start ?? "0");
    const duration = parseTime(opts.duration ?? "0");
    if (start < 0) throw new Error("Start time must be >= 0");
    if (duration <= 0) throw new Error("Duration must be greater than 0");

    const ext = file.name.split(".").pop() ?? "mp4";
    const outName = `${stem(file.name)}-trimmed.${ext}`;
    const { files: out } = await runFFmpeg(
      file,
      ["-ss", start.toFixed(3), "-t", duration.toFixed(3), "-c", "copy"],
      [`out.${ext}`],
      opts.onLog,
    );
    const data = out.find((f) => f.name === `out.${ext}`);
    if (!data) throw new Error("ffmpeg produced no output");
    opts.onLog?.(`Trimmed ${formatBytes(data.data.length)}`);
    return [{ blob: new Blob([toAB(data.data)]), name: outName }];
  }
  throw new Error(`Unknown video tool: ${tool}`);
}

export function videoToolAcceptsVideo(tool: VideoTool): boolean {
  return tool === "trim";
}
