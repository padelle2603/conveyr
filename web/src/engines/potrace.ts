import { init, potrace } from "esm-potrace-wasm";
import { toAB } from "../download";

let initPromise: Promise<void> | null = null;

async function ensureInit(): Promise<void> {
  if (!initPromise) {
    initPromise = init().catch((err) => {
      initPromise = null;
      throw err;
    });
  }
  await initPromise;
}

export async function rasterToSvg(input: Uint8Array): Promise<string> {
  await ensureInit();
  const blob = new Blob([toAB(input)], { type: "image/png" });
  const svg = await potrace(blob, {
    turdsize: 2,
    turnpolicy: 4,
    alphamax: 1,
    opticurve: 1,
    opttolerance: 0.2,
    pathonly: false,
    extractcolors: false,
  });
  return svg;
}