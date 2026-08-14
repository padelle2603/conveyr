import { FFmpeg } from "@ffmpeg/ffmpeg";
import { fetchFile, toBlobURL } from "@ffmpeg/util";

let initPromise: Promise<FFmpeg> | null = null;

export type FFmpegLog = (line: string) => void;

export function initFFmpeg(onLog?: FFmpegLog): Promise<FFmpeg> {
  if (!initPromise) {
    initPromise = (async () => {
      const base = `${import.meta.env.BASE_URL}ffmpeg/`;
      const coreURL = await toBlobURL(`${base}ffmpeg-core.js`, "text/javascript");
      const wasmURL = await toBlobURL(`${base}ffmpeg-core.wasm`, "application/wasm");
      const ff = new FFmpeg();
      if (onLog) ff.on("log", ({ message }) => onLog(message));
      await ff.load({ coreURL, wasmURL });
      return ff;
    })().catch((err) => {
      initPromise = null;
      throw err;
    });
  }
  return initPromise;
}

const INPUT = "input.bin";

export interface FFmpegResult {
  files: { name: string; data: Uint8Array }[];
}

export async function runFFmpeg(
  input: Blob,
  args: string[],
  outputs: string[],
  onLog?: FFmpegLog,
): Promise<FFmpegResult> {
  const ff = await initFFmpeg(onLog);
  await ff.writeFile(INPUT, await fetchFile(input));
  try {
    const full = [...args, INPUT];
    await ff.exec([...full, ...outputs]);
    const files = [];
    for (const name of outputs) {
      const data = (await ff.readFile(name)) as Uint8Array;
      if (data instanceof Uint8Array && data.length) files.push({ name, data });
    }
    return { files };
  } finally {
    for (const name of [INPUT, ...outputs]) {
      try {
        await ff.deleteFile(name);
      } catch {
        /* file may not exist */
      }
    }
  }
}