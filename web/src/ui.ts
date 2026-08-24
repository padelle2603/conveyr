import { categoryOf, CATEGORY_LABELS, canonical, detect, validTargets } from "./formats";
import { OutFile, downloadAll, downloadBlob, formatBytes, stem } from "./download";
import { convertFile, DEFAULT_QUALITY, type ConvertOptions } from "./tools/converter";
import {
  COMPRESS_PRESETS,
  PDF_TOOLS,
  PDF_TOOL_HINTS,
  PDF_TOOL_LABELS,
  isImageName,
  isPdfName,
  pdfToolAcceptsImages,
  pdfToolNeedsPassword,
  runPdfTool,
  type PdfTool,
} from "./tools/pdftools";
import {
  VIDEO_TOOLS,
  VIDEO_TOOL_HINTS,
  VIDEO_TOOL_LABELS,
  isVideoName,
  runVideoTool,
  type VideoTool,
} from "./tools/videotools";

type El = HTMLElement;

function h<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  attrs: Record<string, string | number | boolean> = {},
  children: (El | string)[] = [],
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") node.className = String(value);
    else if (typeof value === "boolean") {
      if (value) node.setAttribute(key, "");
    } else {
      node.setAttribute(key, String(value));
    }
  }
  for (const child of children) {
    node.append(typeof child === "string" ? document.createTextNode(child) : child);
  }
  return node;
}

class LogView {
  private root: HTMLElement;
  constructor(parent: HTMLElement) {
    this.root = h("div", { class: "log hidden" });
    parent.append(this.root);
  }
  clear(): void {
    this.root.textContent = "";
  }
  info(line: string): void {
    this.appendLine(line, "");
  }
  ok(line: string): void {
    this.appendLine(line, "line-ok");
  }
  err(line: string): void {
    this.appendLine(line, "line-err");
  }
  dim(line: string): void {
    this.appendLine(line, "line-dim");
  }
  private appendLine(text: string, cls: string): void {
    this.root.classList.remove("hidden");
    const div = h("div", cls ? { class: cls } : {}, [text]);
    this.root.append(div);
    this.root.scrollTop = this.root.scrollHeight;
  }
}

class StatusBar {
  private root: HTMLElement;
  private bar: HTMLElement;
  constructor(parent: HTMLElement) {
    this.root = h("p", { class: "status hidden" });
    this.bar = h("div", { class: "progress hidden" }, [h("div", { class: "progress-bar" })]);
    parent.append(this.root, this.bar);
  }
  running(msg: string): void {
    this.root.textContent = msg;
    this.root.className = "status running";
    this.bar.classList.remove("hidden");
    (this.bar.firstElementChild as HTMLElement).style.width = "0%";
  }
  ok(msg: string): void {
    this.root.textContent = msg;
    this.root.className = "status ok";
    this.bar.classList.add("hidden");
  }
  error(msg: string): void {
    this.root.textContent = msg;
    this.root.className = "status error";
    this.bar.classList.add("hidden");
  }
  progress(fraction: number): void {
    (this.bar.firstElementChild as HTMLElement).style.width = `${Math.round(fraction * 100)}%`;
  }
  hide(): void {
    this.root.classList.add("hidden");
  }
}

class ResultList {
  private root: HTMLElement;
  constructor(parent: HTMLElement) {
    this.root = h("div", { class: "results hidden" });
    parent.append(this.root);
  }
  show(results: OutFile[]): void {
    this.root.textContent = "";
    const allBtn = h(
      "button",
      { class: "btn btn-primary btn-small", type: "button" },
      [results.length === 1 ? "Download file" : `Download all (${results.length}) as ZIP`],
    );
    allBtn.addEventListener("click", () => void downloadAll(results));
    this.root.append(allBtn);
    for (const r of results) {
      const chip = h("button", { class: "result-chip", type: "button" }, [
        `${r.name} (${formatBytes(r.blob.size)})`,
      ]);
      chip.addEventListener("click", () => downloadBlob(r.blob, r.name));
      this.root.append(chip);
    }
    this.root.classList.remove("hidden");
  }
  hide(): void {
    this.root.classList.add("hidden");
  }
}

interface FileEntry {
  file: File;
  ext: string;
}

interface ConverterState {
  entries: FileEntry[];
  target: string;
}

interface PdfState {
  files: File[];
  tool: PdfTool;
}

interface AppState {
  tab: "converter" | "pdf" | "video";
  converter: ConverterState;
  pdf: PdfState;
  video: VideoState;
}

interface VideoState {
  files: File[];
  tool: VideoTool;
}

function fileExt(file: File): string {
  return canonical(file.name.split(".").pop() ?? "");
}

async function detectEntry(file: File): Promise<FileEntry> {
  return { file, ext: (await detect(file)) ?? fileExt(file) };
}

function dropZone(
  label: string,
  hint: string,
  onFiles: (files: File[]) => void,
): El {
  const zone = h("div", { class: "dropzone" }, [
    h("div", { class: "dz-title" }, [label]),
    h("div", { class: "dz-hint" }, [hint]),
  ]);
  const input = h("input", { type: "file", multiple: true, class: "hidden" }) as HTMLInputElement;
  zone.append(input);

  zone.addEventListener("click", () => input.click());
  input.addEventListener("change", () => {
    if (input.files) {
      onFiles([...input.files]);
      input.value = "";
    }
  });

  zone.addEventListener("dragover", (e) => {
    e.preventDefault();
    zone.classList.add("is-dragover");
  });
  zone.addEventListener("dragleave", () => zone.classList.remove("is-dragover"));
  zone.addEventListener("drop", (e) => {
    e.preventDefault();
    zone.classList.remove("is-dragover");
    onFiles([...(e.dataTransfer?.files ?? [])]);
  });
  return zone;
}

function fileList(entries: FileEntry[], onRemove: (index: number) => void): El {
  const list = h("div", { class: "files" });
  for (const [i, entry] of entries.entries()) {
    const cat = categoryOf(entry.ext);
    const meta = `${formatBytes(entry.file.size)}${cat ? ` · ${CATEGORY_LABELS[cat]}` : ""}`;
    const remove = h("button", { type: "button", title: "Remove" }, ["✕"]);
    remove.addEventListener("click", () => onRemove(i));
    list.append(
      h("div", { class: "file-item" }, [
        h("span", { class: "fext" }, [entry.ext]),
        h("span", { class: "fname", title: entry.file.name }, [entry.file.name]),
        h("span", { class: "fmeta" }, [meta]),
        h("span", { class: "fdrop" }, [remove]),
      ]),
    );
  }
  return list;
}

function converterTargets(entries: FileEntry[]): string[] {
  let common: Set<string> | null = null;
  for (const entry of entries) {
    const targets = validTargets(entry.ext);
    if (targets.length === 0) continue;
    if (common === null) common = new Set(targets);
    else common = new Set(targets.filter((t) => common!.has(t)));
  }
  return common ? [...common].sort() : [];
}

function uniqueName(name: string, used: Set<string>): string {
  let candidate = name;
  let i = 2;
  while (used.has(candidate)) {
    const dot = name.lastIndexOf(".");
    candidate = dot > 0 ? `${name.slice(0, dot)}-${i}${name.slice(dot)}` : `${name}-${i}`;
    i++;
  }
  used.add(candidate);
  return candidate;
}

function optNumber(label: string, defaultValue: number, placeholder: string, min?: number, max?: number): HTMLInputElement {
  const input = h("input", { type: "number", class: "opt", value: defaultValue, placeholder }) as HTMLInputElement;
  input.dataset.opt = label;
  if (min !== undefined) input.min = String(min);
  if (max !== undefined) input.max = String(max);
  return input;
}

function optRange(label: string, defaultValue: number): { wrap: El; input: HTMLInputElement; value: HTMLElement } {
  const input = h("input", {
    type: "range", class: "opt-range", min: "1", max: "100", value: defaultValue,
  }) as HTMLInputElement;
  input.dataset.opt = label;
  const value = h("span", { class: "opt-value" }, [String(defaultValue)]);
  input.addEventListener("input", () => {
    value.textContent = input.value;
  });
  const wrap = h("div", { class: "field range-field" }, [
    h("span", {}, [label]),
    input,
    value,
  ]);
  return { wrap, input, value };
}

function optSelect(label: string, options: [string, string][]): HTMLSelectElement {
  const select = h("select") as HTMLSelectElement;
  select.dataset.opt = label;
  for (const [value, text] of options) select.append(h("option", { value }, [text]));
  return select;
}

function field(label: string, input: HTMLElement): El {
  const wrap = h("div", { class: "field" });
  wrap.append(h("span", {}, [label]), input);
  return wrap;
}

export function renderApp(): void {
  const main = document.getElementById("main");
  if (!main) return;

  const state: AppState = {
    tab: "converter",
    converter: { entries: [], target: "" },
    pdf: { files: [], tool: "merge" },
    video: { files: [], tool: "trim" },
  };

  const converterPanel = buildConverter(main, state);
  const pdfPanel = buildPdf(main, state);
  const videoPanel = buildVideo(main, state);

  const showTab = (tab: "converter" | "pdf" | "video"): void => {
    state.tab = tab;
    converterPanel.root.classList.toggle("hidden", tab !== "converter");
    pdfPanel.root.classList.toggle("hidden", tab !== "pdf");
    videoPanel.root.classList.toggle("hidden", tab !== "video");
    document.getElementById("tab-converter")?.classList.toggle("is-active", tab === "converter");
    document.getElementById("tab-pdf")?.classList.toggle("is-active", tab === "pdf");
    document.getElementById("tab-video")?.classList.toggle("is-active", tab === "video");
  };

  document.getElementById("tab-converter")?.addEventListener("click", () => showTab("converter"));
  document.getElementById("tab-pdf")?.addEventListener("click", () => showTab("pdf"));
  document.getElementById("tab-video")?.addEventListener("click", () => showTab("video"));
  showTab("converter");
}

function buildConverter(main: El, state: AppState): { root: El } {
  const root = h("section", { class: "panel" }, [
    h("h2", {}, ["Converter"]),
    h("p", { class: "subtitle" }, [
      "Convert images, video, audio and animated GIFs. Everything happens locally with WebAssembly.",
    ]),
  ]);
  main.append(root);

  const drop = dropZone(
    "Drop files here or click to choose",
    "Images, video, audio and animated GIFs — files are never uploaded",
    (files) => {
      void Promise.all(files.map(detectEntry)).then((entries) => {
        state.converter.entries = state.converter.entries.concat(entries);
        void refreshConverter();
      });
    },
  );
  root.append(drop);

  const listWrap = h("div", { class: "hidden" });
  root.append(listWrap);

  const row = h("div", { class: "row" });
  const targetSelect = h("select") as HTMLSelectElement;
  const convertBtn = h("button", { class: "btn btn-primary", type: "button", disabled: true }, ["Convert"]);
  const optionsWrap = h("div", { class: "row" });
  const note = h("p", { class: "hint hidden" });
  row.append(h("label", {}, ["Convert to"]), targetSelect, convertBtn);
  root.append(row, optionsWrap, note);

  const status = new StatusBar(root);
  const log = new LogView(root);
  const results = new ResultList(root);

  function refreshConverter(): void {
    const { entries } = state.converter;
    listWrap.textContent = "";
    listWrap.classList.toggle("hidden", entries.length === 0);
    if (entries.length) {
      listWrap.append(
        fileList(entries, (i) => {
          state.converter.entries.splice(i, 1);
          refreshConverter();
        }),
      );
    }

    const targets = converterTargets(entries);
    targetSelect.textContent = "";
    for (const t of targets) targetSelect.append(h("option", { value: t }, [t.toUpperCase()]));
    if (!targets.includes(state.converter.target)) state.converter.target = targets[0] ?? "";
    targetSelect.value = state.converter.target;
    convertBtn.disabled = targets.length === 0;

    note.textContent =
      targets.length === 0 && entries.length
        ? "The selected files can't be converted together — use files of the same type, or the same set of target formats."
        : "";
    note.classList.toggle("hidden", note.textContent === "");

    refreshOptions();
    results.hide();
    status.hide();
    log.clear();
  }

  function refreshOptions(): void {
    optionsWrap.textContent = "";
    const target = state.converter.target;
    const ext = state.converter.entries[0]?.ext;
    if (!target || !ext) return;

    if (target === "svg") {
      optionsWrap.append(field("Threshold", optNumber("Threshold", 50, "0–100", 0, 100)));
      return;
    }
    // A single quality slider drives CRF / bitrate / GIF fps+width / JPEG quality.
    const quality = optRange("Quality", DEFAULT_QUALITY);
    optionsWrap.append(quality.wrap);
  }

  targetSelect.addEventListener("change", () => {
    state.converter.target = targetSelect.value;
    refreshOptions();
  });

  convertBtn.addEventListener("click", () => void runConvert());

  async function runConvert(): Promise<void> {
    const { entries } = state.converter;
    const target = state.converter.target;
    if (entries.length === 0 || !target) return;
    convertBtn.disabled = true;
    results.hide();
    log.clear();
    status.running("Starting…");

    const opts = collectOptions();
    const outputs: OutFile[] = [];
    const used = new Set<string>();

    for (const [i, entry] of entries.entries()) {
      status.running(`Converting ${i + 1}/${entries.length}: ${entry.file.name}`);
      log.info(`→ ${entry.file.name} (${entry.ext}) → ${target}`);
      try {
        const blob = await convertFile(entry.file, entry.ext, target, {
          ...opts,
          onLog: (line) => log.dim(line),
        });
        outputs.push({ blob, name: uniqueName(`${stem(entry.file.name)}.${target}`, used) });
        log.ok(`✓ ${entry.file.name}`);
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        log.err(`✗ ${entry.file.name}: ${msg}`);
        status.error(`Failed: ${msg}`);
      }
      status.progress((i + 1) / entries.length);
    }

    if (outputs.length > 0) {
      status.ok(`Done — ${outputs.length} file${outputs.length > 1 ? "s" : ""} ready`);
      results.show(outputs);
    } else {
      status.error("No files were converted.");
    }
    convertBtn.disabled = false;
  }

  function collectOptions(): ConvertOptions {
    const opts: ConvertOptions = {};
    const num = (label: string): number | undefined => {
      const input = optionsWrap.querySelector(`input[data-opt="${label}"]`) as HTMLInputElement | null;
      if (!input || input.value === "") return undefined;
      const n = Number.parseFloat(input.value);
      return Number.isFinite(n) ? n : undefined;
    };
    const threshold = num("Threshold");
    if (threshold !== undefined) opts.threshold = threshold;
    const quality = num("Quality");
    if (quality !== undefined) opts.quality = quality;
    return opts;
  }

  refreshConverter();
  return { root };
}

function buildPdf(main: El, state: AppState): { root: El } {
  const root = h("section", { class: "panel hidden" }, [
    h("h2", {}, ["PDF tools"]),
    h("p", { class: "subtitle" }, [
      "Merge, split, compress, rotate, protect, unlock, extract — all in your browser.",
    ]),
  ]);
  main.append(root);

  const toolSelect = h("select") as HTMLSelectElement;
  for (const t of PDF_TOOLS) toolSelect.append(h("option", { value: t }, [PDF_TOOL_LABELS[t]]));
  const hint = h("p", { class: "hint" });
  root.append(h("div", { class: "row" }, [h("label", {}, ["Tool"]), toolSelect]));
  root.append(hint);

  const drop = dropZone(
    "Drop files here or click to choose",
    "",
    (files) => {
      const filtered = files.filter((f) =>
        pdfToolAcceptsImages(state.pdf.tool) ? isImageName(f.name) : isPdfName(f.name),
      );
      state.pdf.files = state.pdf.files.concat(filtered);
      refreshPdf();
    },
  );
  root.append(drop);

  const listWrap = h("div", { class: "hidden" });
  root.append(listWrap);

  const optionsWrap = h("div", { class: "row" });
  root.append(optionsWrap);

  const runBtn = h("button", { class: "btn btn-primary", type: "button" }, ["Run"]);
  root.append(h("div", { class: "row" }, [runBtn]));

  const status = new StatusBar(root);
  const log = new LogView(root);
  const results = new ResultList(root);

  function refreshPdf(): void {
    const { tool, files } = state.pdf;
    hint.textContent = PDF_TOOL_HINTS[tool];

    const entries: FileEntry[] = files.map((file) => ({ file, ext: fileExt(file) }));
    listWrap.textContent = "";
    listWrap.classList.toggle("hidden", entries.length === 0);
    if (entries.length) {
      listWrap.append(
        fileList(entries, (i) => {
          state.pdf.files.splice(i, 1);
          refreshPdf();
        }),
      );
    }

    optionsWrap.textContent = "";
    if (tool === "compress") {
      optionsWrap.append(
        field("Preset", optSelect("preset", COMPRESS_PRESETS.map((p) => [p.key, p.label] as [string, string]))),
      );
    } else if (tool === "rotate") {
      optionsWrap.append(field("Angle", optSelect("angle", [["90", "90°"], ["180", "180°"], ["270", "270°"]])));
    } else if (tool === "to-images") {
      optionsWrap.append(
        field("Format", optSelect("format", [["png", "PNG"], ["jpg", "JPG"]])),
        field("DPI", optNumber("DPI", 150, "36–600", 36, 600)),
      );
    } else if (pdfToolNeedsPassword(tool)) {
      const pw = h("input", {
        type: "password",
        placeholder: tool === "unlock" ? "password (optional)" : "password",
      }) as HTMLInputElement;
      optionsWrap.append(field("Password", pw));
    }

    status.hide();
    log.clear();
    results.hide();
  }

  function collectPdfOptions() {
    const opts: Record<string, unknown> = {};
    for (const select of optionsWrap.querySelectorAll("select")) {
      if (select.dataset.opt) opts[select.dataset.opt] = select.value;
    }
    const pw = optionsWrap.querySelector("input[type=password]") as HTMLInputElement | null;
    if (pw) opts.password = pw.value;
    const dpi = optionsWrap.querySelector("input[data-opt=DPI]") as HTMLInputElement | null;
    if (dpi) opts.dpi = Number.parseFloat(dpi.value) || 150;
    return opts;
  }

  toolSelect.addEventListener("change", () => {
    state.pdf.tool = toolSelect.value as PdfTool;
    state.pdf.files = [];
    refreshPdf();
  });

  runBtn.addEventListener("click", () => void runPdf());

  async function runPdf(): Promise<void> {
    const { tool, files } = state.pdf;
    runBtn.disabled = true;
    results.hide();
    log.clear();
    status.running("Working…");
    try {
      const o = collectPdfOptions();
      const outputs = await runPdfTool(tool, files, {
        angle: o.angle !== undefined ? Number(o.angle) : undefined,
        format: (o.format as "png" | "jpg") ?? "png",
        dpi: o.dpi as number,
        preset: o.preset as string,
        password: o.password as string,
        onLog: (line) => log.dim(line),
      });
      status.ok(`Done — ${outputs.length} file${outputs.length > 1 ? "s" : ""} ready`);
      results.show(outputs);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      log.err(msg);
      status.error(`Failed: ${msg}`);
    }
    runBtn.disabled = false;
  }

  refreshPdf();
  return { root };
}

function buildVideo(main: El, state: AppState): { root: El } {
  const root = h("section", { class: "panel hidden" }, [
    h("h2", {}, ["Video tools"]),
    h("p", { class: "subtitle" }, [
      "Trim and edit video locally with WebAssembly. Nothing is ever uploaded.",
    ]),
  ]);
  main.append(root);

  const toolSelect = h("select") as HTMLSelectElement;
  for (const t of VIDEO_TOOLS) toolSelect.append(h("option", { value: t }, [VIDEO_TOOL_LABELS[t]]));
  const hint = h("p", { class: "hint" });
  root.append(h("div", { class: "row" }, [h("label", {}, ["Tool"]), toolSelect]));
  root.append(hint);

  const drop = dropZone(
    "Drop a video here or click to choose",
    "MP4, WebM, MKV, AVI, MOV, MPG — stays on your device",
    (files) => {
      const filtered = files.filter((f) => isVideoName(f.name));
      state.video.files = state.video.files.concat(filtered);
      refreshVideo();
    },
  );
  root.append(drop);

  const listWrap = h("div", { class: "hidden" });
  root.append(listWrap);

  const optionsWrap = h("div", { class: "row" });
  root.append(optionsWrap);

  const runBtn = h("button", { class: "btn btn-primary", type: "button" }, ["Run"]);
  root.append(h("div", { class: "row" }, [runBtn]));

  const status = new StatusBar(root);
  const log = new LogView(root);
  const results = new ResultList(root);

  function refreshVideo(): void {
    const { tool, files } = state.video;
    hint.textContent = VIDEO_TOOL_HINTS[tool];

    const entries: FileEntry[] = files.map((file) => ({ file, ext: fileExt(file) }));
    listWrap.textContent = "";
    listWrap.classList.toggle("hidden", entries.length === 0);
    if (entries.length) {
      listWrap.append(
        fileList(entries, (i) => {
          state.video.files.splice(i, 1);
          refreshVideo();
        }),
      );
    }

    optionsWrap.textContent = "";
    if (tool === "trim") {
      const startInput = h("input", { type: "text", class: "opt", placeholder: "0" }) as HTMLInputElement;
      startInput.dataset.opt = "start";
      const durInput = h("input", { type: "text", class: "opt", placeholder: "e.g. 30" }) as HTMLInputElement;
      durInput.dataset.opt = "duration";
      optionsWrap.append(
        field("Start (s or HH:MM:SS)", startInput),
        field("Duration (s or HH:MM:SS)", durInput),
      );
    }

    status.hide();
    log.clear();
    results.hide();
  }

  function collectVideoOptions(): { start: string; duration: string } {
    const opt = (label: string): string => {
      const input = optionsWrap.querySelector(`input[data-opt="${label}"]`) as HTMLInputElement | null;
      return input ? input.value.trim() : "";
    };
    return { start: opt("start"), duration: opt("duration") };
  }

  toolSelect.addEventListener("change", () => {
    state.video.tool = toolSelect.value as VideoTool;
    state.video.files = [];
    refreshVideo();
  });

  runBtn.addEventListener("click", () => void runVideo());

  async function runVideo(): Promise<void> {
    const { tool, files } = state.video;
    if (files.length === 0) {
      status.error("Add a video file first.");
      return;
    }
    runBtn.disabled = true;
    results.hide();
    log.clear();
    status.running("Working…");
    try {
      const o = collectVideoOptions();
      const outputs = await runVideoTool(tool, files, {
        start: o.start,
        duration: o.duration,
        onLog: (line) => log.dim(line),
      });
      status.ok(`Done — ${outputs.length} file${outputs.length > 1 ? "s" : ""} ready`);
      results.show(outputs);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      log.err(msg);
      status.error(`Failed: ${msg}`);
    }
    runBtn.disabled = false;
  }

  refreshVideo();
  return { root };
}