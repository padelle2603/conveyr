import { chromium } from "playwright";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { dirname } from "node:path";
import { PDFDocument } from "pdf-lib";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..");
const URL = process.env.SMOKE_URL ?? "http://localhost:4173/";

const tmp = mkdtempSync(join(tmpdir(), "conveyr-smoke-"));

function fixture(name) {
  return join(root, "tests", "fixtures", name);
}

async function makePdf(path, text) {
  const doc = await PDFDocument.create();
  const font = await doc.embedFont("Helvetica");
  const page = doc.addPage([200, 200]);
  page.drawText(text ?? "conveyr smoke", { x: 20, y: 100, size: 12, font });
  writeFileSync(path, await doc.save());
}

async function main() {
  await makePdf(join(tmp, "one.pdf"), "first");
  await makePdf(join(tmp, "two.pdf"), "second");

  const browser = await chromium.launch({ channel: process.env.SMOKE_CHANNEL || undefined });
  const page = await browser.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
  page.on("console", (m) => {
    if (m.type() === "error") errors.push(`console: ${m.text()}`);
  });

  async function dumpDiagnostics(page, label) {
    const status = await page.locator("#main section:not(.hidden) .status:not(.hidden)").textContent().catch(() => "?");
    const log = await page.locator("#main section:not(.hidden) .log").textContent().catch(() => "?");
    console.log(`${label} STATUS:`, status);
    console.log(`${label} LOG:\n`, log);
    if (errors.length) console.log(`${label} CONSOLE/PAGE ERRORS:\n` + errors.join("\n"));
  }

  console.log("loading…");
  await page.goto(URL, { waitUntil: "networkidle" });

  // ---- Converter: images ----
  console.log("converter: adding png + jpg…");
  const convInput = page.locator("#main section:not(.hidden) input[type=file]").first();
  await convInput.setInputFiles([fixture("src.png"), fixture("src.jpg")]);
  await page.waitForFunction(() => {
    const sel = document.querySelector("#main section:not(.hidden) select");
    return sel && sel.options.length > 0;
  });

  const target = page.locator("#main section:not(.hidden) select").first();
  const targetValue = await target.inputValue();
  console.log("converter: target select =", targetValue);
  if (!targetValue) throw new Error("converter target not selected");

  console.log("converter: converting png+jpg →", targetValue, "(loads magick wasm)…");
  await page.locator("#main section:not(.hidden)").getByRole("button", { name: "Convert" }).click();
  try {
    await page.waitForSelector("#main section:not(.hidden) .result-chip:not(.hidden)", { timeout: 120000 });
  } catch (e) {
    await dumpDiagnostics(page, "MAGICK");
    throw e;
  }
  const chips = await page.locator("#main section:not(.hidden) .result-chip").count();
  console.log(`converter: ${chips} result chip(s)`);
  if (chips < 2) throw new Error("expected 2 converted files");

  // ---- PDF: merge ----
  console.log("pdf: switching tab…");
  await page.click("#tab-pdf");
  await page.waitForSelector("#main section:not(.hidden) .dropzone");
  const pdfInput = page.locator("#main section:not(.hidden) input[type=file]").first();
  await pdfInput.setInputFiles([join(tmp, "one.pdf"), join(tmp, "two.pdf")]);
  await page.waitForFunction(() =>
    document.querySelectorAll("#main section:not(.hidden) .file-item").length === 2,
  );
  console.log("pdf: running merge…");
  await page.locator("#main section:not(.hidden)").getByRole("button", { name: "Run" }).click();
  await page.waitForSelector("#main section:not(.hidden) .result-chip", { timeout: 60000 });
  const pdfChip = await page.locator("#main section:not(.hidden) .result-chip").first().innerText();
  console.log("pdf: result =", pdfChip);

  const pageErrors = errors.filter((e) => !e.includes("favicon") && !e.includes("Download the React DevTools"));
  if (pageErrors.length) {
    console.error("PAGE ERRORS:\n" + pageErrors.join("\n"));
    throw new Error("console/page errors detected");
  }

  console.log("SMOKE OK");
  await browser.close();
}

main().then(
  () => process.exit(0),
  (err) => {
    console.error("SMOKE FAILED:", err.message);
    process.exit(1);
  },
);