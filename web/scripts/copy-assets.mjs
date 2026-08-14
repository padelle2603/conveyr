import { copyFileSync, mkdirSync, rmSync, existsSync, readdirSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");

function copyTree(srcDir, destDir) {
  const srcPath = join(root, srcDir);
  const destPath = join(root, destDir);
  if (!existsSync(srcPath)) {
    console.error(`missing asset dir: ${srcPath}`);
    process.exit(1);
  }
  mkdirSync(destPath, { recursive: true });
  for (const entry of readdirSync(srcPath)) {
    const from = join(srcPath, entry);
    const to = join(destPath, entry);
    if (statSync(from).isDirectory()) {
      copyTree(join(srcDir, entry), join(destDir, entry));
    } else {
      rmSync(to, { force: true });
      copyFileSync(from, to);
    }
  }
}

const assets = [
  ["node_modules/@ffmpeg/core/dist/umd/ffmpeg-core.js", "public/ffmpeg/ffmpeg-core.js"],
  ["node_modules/@ffmpeg/core/dist/umd/ffmpeg-core.wasm", "public/ffmpeg/ffmpeg-core.wasm"],
  ["node_modules/@imagemagick/magick-wasm/dist/magick.wasm", "public/magick/magick.wasm"],
  ["../assets/conveyr.png", "public/conveyr.png"],
];

for (const [src, dest] of assets) {
  const srcPath = join(root, src);
  const destPath = join(root, dest);
  if (!existsSync(srcPath)) {
    console.error(`missing asset: ${srcPath}`);
    process.exit(1);
  }
  mkdirSync(dirname(destPath), { recursive: true });
  rmSync(destPath, { force: true });
  copyFileSync(srcPath, destPath);
  console.log(`copied ${src} -> ${dest}`);
}

copyTree("node_modules/pdfjs-dist/standard_fonts", "public/pdfjs-standard-fonts");
console.log("copied standard_fonts -> public/pdfjs-standard-fonts");
console.log("assets OK");