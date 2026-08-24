"""Conversion core: format matrix, real format detection and dispatch.

The heavy lifting is delegated to the backends module; this module decides
*what* a file is and *how* it can be converted.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from . import __version__
from .backends import (
    BackendError,
    ffprobe,
    find_rsvg,
    require_ffmpeg,
    require_image_magick,
    require_potrace,
    run,
)

RASTER = {"jpg", "png", "webp", "bmp", "tiff"}
VECTOR = {"svg"}
VIDEO = {"mp4", "webm", "mkv", "avi", "mov", "mpg"}
AUDIO = {"wav", "mp3", "flac", "ogg", "m4a", "opus", "aac"}
ALL = RASTER | VECTOR | VIDEO | AUDIO | {"gif"}

ALIASES = {
    "jpeg": "jpg",
    "jpe": "jpg",
    "tif": "tiff",
    "mpeg": "mpg",
    "m4v": "mp4",
    "mp4v": "mp4",
    "oga": "ogg",
    "m4b": "m4a",
    "m4a3": "m4a",
}

CATEGORY: dict[str, str] = {}
for _ext in RASTER:
    CATEGORY[_ext] = "image"
CATEGORY["svg"] = "vector"
for _ext in VIDEO:
    CATEGORY[_ext] = "video"
for _ext in AUDIO:
    CATEGORY[_ext] = "audio"
CATEGORY["gif"] = "gif"

CATEGORY_LABELS = {
    "image": "Images",
    "vector": "Vector graphics",
    "gif": "Animated GIF",
    "video": "Video",
    "audio": "Audio",
}

_FORMAT_PROBE_MAP = {
    "gif": "gif",
    "mov,mp4,m4a,3gp,3g2,mj2": "mp4",
    "matroska,webm": "mkv",
    "avi": "avi",
    "wav": "wav",
    "mp3": "mp3",
    "flac": "flac",
    "ogg": "ogg",
    "opus": "opus",
    "aac": "aac",
    "mpeg": "mpg",
}


def canonical(ext: str) -> str:
    """Normalize an extension to a canonical, lower-case token."""
    if not ext:
        return ""
    ext = ext.lstrip(".").lower()
    return ALIASES.get(ext, ext)


def category_of(ext: str) -> str | None:
    return CATEGORY.get(ext)


def is_supported(ext: str) -> bool:
    return ext in ALL


def valid_targets(src_ext: str) -> list[str]:
    """Return the target formats a given source format can become."""
    if src_ext not in CATEGORY:
        return []
    cat = CATEGORY[src_ext]
    if cat == "image":
        return sorted((RASTER | {"svg", "gif"}) - {src_ext})
    if cat == "vector":
        return sorted(RASTER | {"gif"})
    if cat == "gif":
        return sorted(RASTER | VIDEO)
    if cat == "video":
        return sorted((VIDEO | {"gif"}) - {src_ext})
    if cat == "audio":
        return sorted(AUDIO - {src_ext})
    return []


def list_formats() -> dict[str, list[str]]:
    """Map every supported format to its valid targets."""
    return {ext: valid_targets(ext) for ext in sorted(ALL, key=lambda e: CATEGORY_LABELS.get(CATEGORY.get(e, ""), ""))}


def detect(path) -> str | None:
    """Detect the real format of a file via magic bytes, ffprobe, then extension."""
    p = Path(path)
    if not p.is_file():
        return None

    magic = _magic_detect(p)
    if magic:
        return magic

    probed = _probe_detect(p)
    if probed:
        return probed

    ext = canonical(p.suffix)
    return ext if ext in ALL else None


def _magic_detect(p: Path) -> str | None:
    try:
        with open(p, "rb") as fh:
            head = fh.read(64)
    except OSError:
        return None

    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    if head[:2] == b"BM":
        return "bmp"
    if head[:4] in (b"II*\x00", b"MM\x00*"):
        return "tiff"

    try:
        with open(p, "rb") as fh:
            blob = fh.read(8192)
    except OSError:
        return None
    lowered = blob.lower()
    if b"<svg" in lowered or (lowered.startswith(b"<?xml") and b"<svg" in lowered):
        return "svg"
    return None


def _probe_detect(p: Path) -> str | None:
    info = ffprobe(p)
    if not info:
        return None
    fmt = info["format_name"].lower()
    if fmt not in _FORMAT_PROBE_MAP:
        return None
    ext = _FORMAT_PROBE_MAP[fmt]
    ext_hint = canonical(p.suffix)
    if ext == "mp4" and info["has_audio"] and not info["has_video"] and ext_hint == "m4a":
        return "m4a"
    if ext == "mkv" and ext_hint == "webm":
        return "webm"
    return ext


def convert(src_path, src_ext: str, target: str, opts: dict | None = None) -> str:
    """Convert one file and return the path of the produced file."""
    opts = opts or {}
    src = str(Path(src_path).resolve())
    if target not in valid_targets(src_ext):
        raise ValueError(f"Cannot convert {src_ext} to {target}")

    out = _resolve_output(src, target, opts)
    if not opts.get("force") and Path(out).exists():
        raise FileExistsError(
            f"Output already exists: {out} (use --force to overwrite)"
        )

    src_cat = CATEGORY[src_ext]
    tgt_cat = CATEGORY[target]

    if src_cat in ("image", "gif") and tgt_cat == "image":
        _convert_image_raster(src, src_ext, out, opts)
    elif src_cat in ("image", "gif") and target == "svg":
        _convert_to_svg(src, out, opts)
    elif src_cat == "vector" and target == "gif":
        _convert_svg_to_raster(src, out, opts)
    elif src_cat == "vector" and tgt_cat == "image":
        _convert_svg_to_raster(src, out, opts)
    elif src_cat == "gif" and tgt_cat == "video":
        _convert_gif_to_video(src, target, out, opts)
    elif src_cat == "video" and target == "gif":
        _convert_video_to_gif(src, out, opts)
    elif src_cat == "video" and tgt_cat == "video":
        _convert_video(src, target, out, opts)
    elif src_cat == "audio" and tgt_cat == "audio":
        _convert_audio(src, target, out, opts)
    else:
        raise ValueError(f"No conversion path from {src_ext} to {target}")

    return out


def _resolve_output(src: str, target: str, opts: dict) -> str:
    explicit = opts.get("output")
    if explicit:
        return str(Path(explicit))
    base = Path(opts.get("out_dir") or Path(src).parent)
    return str(base / f"{Path(src).stem}.{target}")


# --------------------------------------------------------------------------- #
# Quality: a single 1-100 slider mapped to sensible per-format encode params.
# --------------------------------------------------------------------------- #

DEFAULT_QUALITY = 80


def _clamp_quality(value) -> int:
    try:
        q = int(value)
    except (TypeError, ValueError):
        return DEFAULT_QUALITY
    return max(1, min(100, q))


def quality_to_crf(value) -> int:
    """Map quality (1-100) to an H.264/VP9 CRF (lower = better)."""
    q = _clamp_quality(value)
    return max(17, min(51, round(51 - 0.33 * q)))


def quality_to_bitrate(value) -> int:
    """Map quality (1-100) to an audio bitrate in kbit/s."""
    q = _clamp_quality(value)
    return max(64, min(320, round(64 + 2.56 * q)))


def quality_to_gif(value) -> tuple[int, int]:
    """Map quality (1-100) to (fps, width) for GIF output."""
    q = _clamp_quality(value)
    fps = max(1, min(30, round(5 + 0.25 * q)))
    width = max(160, min(1280, round(360 + 4.8 * q)))
    return fps, width


# --------------------------------------------------------------------------- #
# Image conversions
# --------------------------------------------------------------------------- #


def _convert_image_raster(src, src_ext, out, opts):
    im = require_image_magick()
    inp = src + "[0]" if src_ext == "gif" else src
    cmd = [im, inp]
    target_ext = Path(out).suffix.lstrip(".").lower()
    if target_ext in ("jpg", "webp"):
        cmd += ["-quality", str(_clamp_quality(opts.get("quality")))]
    cmd.append(out)
    run(cmd, opts.get("quiet"), timeout=600)


def _convert_to_svg(src, out, opts):
    im = require_image_magick()
    potrace = require_potrace()
    threshold = int(opts.get("threshold", 50))
    threshold = max(0, min(100, threshold))

    tmp = tempfile.mktemp(suffix=".pbm")
    try:
        run(
            [
                im, src,
                "-background", "white",
                "-alpha", "remove",
                "-alpha", "off",
                "-colorspace", "Gray",
                "-threshold", f"{threshold}%",
                tmp,
            ],
            opts.get("quiet"),
        )
        run([potrace, "--svg", "-o", out, tmp], opts.get("quiet"), timeout=600)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def _svg_size(p: Path) -> tuple[int, int] | None:
    try:
        text = p.read_text(errors="ignore")[:65536]
    except OSError:
        return None
    width = re.search(r"<svg[^>]*\bwidth=\"([^\"]+)\"", text)
    height = re.search(r"<svg[^>]*\bheight=\"([^\"]+)\"", text)
    if width and height:
        w, h = _strip_unit(width.group(1)), _strip_unit(height.group(1))
        if w and h:
            return w, h
    view_box = re.search(r"\bviewBox=\"\s*[\d.-]+\s+[\d.-]+\s+([\d.-]+)\s+([\d.-]+)\"", text)
    if view_box:
        try:
            return int(float(view_box.group(1))), int(float(view_box.group(2)))
        except ValueError:
            return None
    return None


def _strip_unit(value: str) -> int | None:
    value = value.strip()
    if value.endswith(("px", "pt", "mm", "cm", "in")):
        value = value[:-2]
    try:
        return int(float(value))
    except ValueError:
        return None


def _convert_svg_to_raster(src, out, opts):
    rsvg = find_rsvg()
    im = require_image_magick()
    target_ext = Path(out).suffix.lstrip(".").lower()

    if rsvg:
        size = _svg_size(Path(src))
        tmp = tempfile.mktemp(suffix=".png")
        cmd = [rsvg, "-o", tmp]
        if size:
            cmd += ["-w", str(size[0]), "-h", str(size[1])]
        cmd.append(src)
        run(cmd, opts.get("quiet"))
        try:
            if target_ext == "png":
                os.replace(tmp, out)
            else:
                run([im, tmp, out], opts.get("quiet"), timeout=600)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
    else:
        run([im, src, out], opts.get("quiet"), timeout=600)


# --------------------------------------------------------------------------- #
# Video conversions
# --------------------------------------------------------------------------- #


def _convert_gif_to_video(src, target, out, opts):
    ff = require_ffmpeg()
    crf = int(opts.get("crf") or quality_to_crf(opts.get("quality"))) if target == "webm" else None
    cmd = [ff, "-n", "-i", src]
    if target == "mp4":
        cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
    elif target == "mov":
        cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
    elif target == "webm":
        cmd += ["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", str(crf)]
    elif target == "mkv":
        cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
    elif target == "avi":
        cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
    elif target == "mpg":
        cmd += ["-c:v", "mpeg2video", "-qscale:v", "3"]
    cmd.append(out)
    run(cmd, opts.get("quiet"))


def _convert_video_to_gif(src, out, opts):
    ff = require_ffmpeg()
    if opts.get("quality") is not None:
        fps, width = quality_to_gif(opts["quality"])
    else:
        fps = int(opts.get("fps", 10))
        width = int(opts.get("width", 480))
    if width < 16 or width > 10000:
        width = 480
    if fps < 1 or fps > 60:
        fps = 10
    vf = (
        f"fps={fps},scale={width}:-1:flags=lanczos,"
        "split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse"
    )
    run([ff, "-n", "-i", src, "-vf", vf, "-loop", "0", out], opts.get("quiet"))


_VIDEO_CODECS = {
    "mp4": {"v": "libx264", "a": "aac", "vextra": ["-pix_fmt", "yuv420p", "-movflags", "+faststart"]},
    "mov": {"v": "libx264", "a": "aac", "vextra": ["-pix_fmt", "yuv420p"]},
    "webm": {"v": "libvpx-vp9", "a": "libopus", "vextra": ["-b:v", "0"]},
    "mkv": {"v": "libx264", "a": "libopus", "vextra": ["-pix_fmt", "yuv420p"]},
    "avi": {"v": "libx264", "a": "libmp3lame", "vextra": ["-pix_fmt", "yuv420p"]},
    "mpg": {"v": "mpeg2video", "a": "mp2", "vextra": ["-qscale:v", "3"]},
}


def _convert_video(src, target, out, opts):
    ff = require_ffmpeg()
    codec = _VIDEO_CODECS[target]
    crf = opts.get("crf")
    if crf is None and opts.get("quality") is not None:
        crf = quality_to_crf(opts["quality"])
    cmd = [ff, "-n", "-i", src, "-c:v", codec["v"]]
    if crf is not None and codec["v"] in ("libx264", "libvpx-vp9"):
        cmd += ["-crf", str(int(crf))]
    cmd += codec["vextra"]
    cmd += ["-c:a", codec["a"]]
    cmd += ["-b:a", "128k" if target == "webm" else "192k"]
    cmd.append(out)
    run(cmd, opts.get("quiet"))


# --------------------------------------------------------------------------- #
# Audio conversions
# --------------------------------------------------------------------------- #


def _normalize_bitrate(value) -> str | None:
    if value is None or value == "":
        return None
    value = str(value).strip()
    if value.lower().endswith("k"):
        return f"{int(value[:-1])}k"
    try:
        return f"{int(value)}k"
    except ValueError:
        return None


def _convert_audio(src, target, out, opts):
    ff = require_ffmpeg()
    bitrate = _normalize_bitrate(opts.get("bitrate"))
    if bitrate is None and opts.get("quality") is not None:
        bitrate = f"{quality_to_bitrate(opts['quality'])}k"
    cmd = [ff, "-n", "-i", src, "-vn"]
    if target == "wav":
        cmd += ["-c:a", "pcm_s16le"]
    elif target == "mp3":
        cmd += ["-c:a", "libmp3lame"]
        cmd += ["-b:a", bitrate] if bitrate else ["-qscale:a", "2"]
    elif target == "flac":
        cmd += ["-c:a", "flac"]
    elif target == "ogg":
        cmd += ["-c:a", "libvorbis"]
        cmd += ["-b:a", bitrate] if bitrate else ["-qscale:a", "4"]
    elif target == "m4a":
        cmd += ["-c:a", "aac", "-b:a", bitrate or "192k"]
    elif target == "aac":
        cmd += ["-c:a", "aac", "-b:a", bitrate or "192k"]
    elif target == "opus":
        cmd += ["-c:a", "libopus", "-b:a", bitrate or "128k"]
    cmd.append(out)
    run(cmd, opts.get("quiet"))


__all__ = [
    "RASTER", "VECTOR", "VIDEO", "AUDIO", "ALL", "ALIASES",
    "CATEGORY", "CATEGORY_LABELS",
    "canonical", "category_of", "is_supported", "valid_targets",
    "list_formats", "detect", "convert", "BackendError", "__version__",
    "DEFAULT_QUALITY", "quality_to_crf", "quality_to_bitrate", "quality_to_gif",
]