"""PDF tools: merge, split, compress, rotate, protect, unlock and more.

Everything runs locally using poppler-utils (pdfunite, pdfseparate, pdftotext,
pdftoppm), ghostscript (gs) and qpdf. No cloud, no servers.
"""

from __future__ import annotations

import re
from pathlib import Path

from .backends import (
    BackendError,
    require_gs,
    require_image_magick,
    require_pdfseparate,
    require_pdftotext,
    require_pdftoppm,
    require_pdfunite,
    require_qpdf,
    run,
)

_PDF_MAGIC = b"%PDF"

# qpdf returns exit code 3 when the operation succeeds but with warnings
# (e.g. it repaired a slightly malformed document).
_QPDF_OK_CODES = (0, 3)

# PDF jobs normally finish in a blink; a generous cap still prevents a hung
# backend from freezing the app forever.
_TIMEOUT = 600

COMPRESS_PRESETS = ("screen", "ebook", "printer")
ROTATE_ANGLES = ("90", "180", "270")
IMAGE_FORMATS = ("png", "jpg")


def is_pdf(path) -> bool:
    """Return True when the file starts with the %PDF magic bytes."""
    try:
        with open(path, "rb") as fh:
            return fh.read(len(_PDF_MAGIC)) == _PDF_MAGIC
    except OSError:
        return False


def _check_output(out: str, opts: dict) -> None:
    if not opts.get("force") and Path(out).exists():
        raise FileExistsError(
            f"Output already exists: {out} (use --force to overwrite)"
        )


def _resolve_out(out: str | None, src: str, suffix: str, opts: dict) -> str:
    if out:
        return out
    base = Path(opts.get("out_dir") or Path(src).parent)
    return str(base / f"{Path(src).stem}{suffix}")


def _require_pdf(path) -> None:
    if not is_pdf(path):
        raise ValueError(f"Not a PDF file: {path}")


def merge(paths, out: str | None = None, opts: dict | None = None) -> str:
    """Merge several PDFs into one, in the given order."""
    opts = opts or {}
    if not paths:
        raise ValueError("Need at least one PDF to merge")
    for p in paths:
        _require_pdf(p)
    output = out or _resolve_out(None, str(paths[0]), "-merged.pdf", opts)
    _check_output(output, opts)
    exe = require_pdfunite()
    run([exe, *map(str, paths), output], opts.get("quiet"), timeout=_TIMEOUT)
    return output


def split(path, out_dir: str | None = None, opts: dict | None = None) -> list[str]:
    """Split a PDF into one file per page."""
    opts = opts or {}
    _require_pdf(path)
    src = Path(path)
    base = Path(out_dir or opts.get("out_dir") or src.parent)
    base.mkdir(parents=True, exist_ok=True)
    pattern = str(base / f"{src.stem}-page-%d.pdf")
    exe = require_pdfseparate()
    run([exe, str(src), pattern], opts.get("quiet"), timeout=_TIMEOUT)
    return sorted(base.glob(f"{src.stem}-page-*.pdf"), key=_page_key)


def _page_key(p: Path) -> int:
    try:
        return int(p.stem.rsplit("-", 1)[1])
    except (ValueError, IndexError):
        return 0


def compress(path, out: str | None = None, opts: dict | None = None) -> str:
    """Compress a PDF with a ghostscript quality preset."""
    opts = opts or {}
    _require_pdf(path)
    preset = str(opts.get("preset") or "ebook").lower()
    if preset not in COMPRESS_PRESETS:
        raise ValueError(
            f"Invalid compression preset: {preset} "
            f"(choose from {'/'.join(COMPRESS_PRESETS)})"
        )
    output = out or _resolve_out(None, str(path), "-compressed.pdf", opts)
    _check_output(output, opts)
    exe = require_gs()
    run(
        [
            exe, "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER",
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/" + preset,
            "-dDetectDuplicateImages=true",
            "-sOutputFile=" + output,
            str(path),
        ],
        opts.get("quiet"),
        timeout=_TIMEOUT,
    )
    return output


def rotate(path, out: str | None = None, opts: dict | None = None) -> str:
    """Rotate every page of a PDF by 90, 180 or 270 degrees clockwise."""
    opts = opts or {}
    _require_pdf(path)
    angle = str(opts.get("angle") or "90")
    if angle not in ROTATE_ANGLES:
        raise ValueError(
            f"Invalid rotation angle: {angle} (choose from {'/'.join(ROTATE_ANGLES)})"
        )
    output = out or _resolve_out(None, str(path), f"-rotated{angle}.pdf", opts)
    _check_output(output, opts)
    exe = require_qpdf()
    run(
        [exe, f"--rotate={angle}:1-z", "--", str(path), output],
        opts.get("quiet"),
        ok_codes=_QPDF_OK_CODES,
        timeout=_TIMEOUT,
    )
    return output


def protect(path, out: str | None = None, opts: dict | None = None) -> str:
    """Encrypt a PDF with a password (user and owner password share it)."""
    opts = opts or {}
    _require_pdf(path)
    password = str(opts.get("password") or "")
    if not password:
        raise ValueError("A password is required to protect the PDF")
    output = out or _resolve_out(None, str(path), "-protected.pdf", opts)
    _check_output(output, opts)
    exe = require_qpdf()
    run(
        [exe, "--encrypt", password, password, "256", "--", str(path), output],
        opts.get("quiet"),
        ok_codes=_QPDF_OK_CODES,
        timeout=_TIMEOUT,
    )
    return output


def unlock(path, out: str | None = None, opts: dict | None = None) -> str:
    """Remove the password protection from a PDF."""
    opts = opts or {}
    _require_pdf(path)
    output = out or _resolve_out(None, str(path), "-unlocked.pdf", opts)
    _check_output(output, opts)
    exe = require_qpdf()
    cmd = [exe]
    password = str(opts.get("password") or "")
    if password:
        cmd += [f"--password={password}"]
    cmd += ["--decrypt", str(path), output]
    run(cmd, opts.get("quiet"), ok_codes=_QPDF_OK_CODES, timeout=_TIMEOUT)
    return output


def to_images(
    path, out_dir: str | None = None, opts: dict | None = None
) -> list[str]:
    """Render a PDF to one image per page (png or jpg)."""
    opts = opts or {}
    _require_pdf(path)
    fmt = str(opts.get("format") or "png").lower().lstrip(".")
    if fmt not in IMAGE_FORMATS:
        raise ValueError(
            f"Invalid image format: {fmt} (choose from {'/'.join(IMAGE_FORMATS)})"
        )
    try:
        dpi = int(opts.get("dpi") or 150)
    except (TypeError, ValueError):
        dpi = 150
    dpi = max(36, min(600, dpi))
    src = Path(path)
    base = Path(out_dir or opts.get("out_dir") or src.parent)
    base.mkdir(parents=True, exist_ok=True)
    prefix = str(base / src.stem)
    exe = require_pdftoppm()
    flag = "-jpeg" if fmt == "jpg" else "-png"
    run([exe, flag, "-r", str(dpi), str(src), prefix], opts.get("quiet"), timeout=_TIMEOUT)
    return sorted(
        base.glob(f"{src.stem}-*[0-9].{fmt}"),
        key=lambda p: _trailing_number(p),
    )


def _trailing_number(p: Path) -> int:
    match = re.search(r"(\d+)\.(png|jpg)$", p.name)
    return int(match.group(1)) if match else 0


def from_images(paths, out: str | None = None, opts: dict | None = None) -> str:
    """Combine images into a PDF, preserving the given order."""
    opts = opts or {}
    if not paths:
        raise ValueError("Need at least one image to build a PDF")
    output = out or _resolve_out(None, str(paths[0]), ".pdf", opts)
    _check_output(output, opts)
    exe = require_image_magick()
    run([exe, *map(str, paths), output], opts.get("quiet"), timeout=_TIMEOUT)
    return output


def to_text(path, out: str | None = None, opts: dict | None = None) -> str:
    """Extract the text of a PDF into a .txt file."""
    opts = opts or {}
    _require_pdf(path)
    output = out or _resolve_out(None, str(path), ".txt", opts)
    _check_output(output, opts)
    exe = require_pdftotext()
    run([exe, str(path), output], opts.get("quiet"), timeout=_TIMEOUT)
    return output


def run_tool(name: str, paths, out: str | None, out_dir: str | None, opts: dict) -> str | list[str]:
    """Dispatch a PDF tool by name; used by the CLI and GUI."""
    options = dict(opts or {})
    if out_dir:
        options["out_dir"] = out_dir
    if out:
        options["output"] = out
    if name == "merge":
        return merge(paths, out, options)
    if name == "split":
        return split(paths[0], out_dir, options)
    if name == "compress":
        return compress(paths[0], out, options)
    if name == "rotate":
        return rotate(paths[0], out, options)
    if name == "protect":
        return protect(paths[0], out, options)
    if name == "unlock":
        return unlock(paths[0], out, options)
    if name == "to-images":
        return to_images(paths[0], out_dir, options)
    if name == "from-images":
        return from_images(paths, out, options)
    if name == "to-text":
        return to_text(paths[0], out, options)
    raise ValueError(f"Unknown PDF tool: {name}")


__all__ = [
    "COMPRESS_PRESETS", "ROTATE_ANGLES", "IMAGE_FORMATS",
    "is_pdf", "merge", "split", "compress", "rotate", "protect",
    "unlock", "to_images", "from_images", "to_text", "run_tool",
    "BackendError",
]