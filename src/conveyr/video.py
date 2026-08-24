"""Video tools: trim, crop, rotate, resize, speed, mute, extract audio/frame.

Everything runs locally using ffmpeg. No cloud, no servers.
"""

from __future__ import annotations

from pathlib import Path

from .backends import BackendError, ffprobe, require_ffmpeg, run
from .core import VIDEO, canonical

_TIMEOUT = 600

ROTATE_ANGLES = ("90", "180", "270")

_AUDIO_EXT_BY_CODEC = {
    "aac": "m4a",
    "mp3": "mp3",
    "opus": "opus",
    "vorbis": "ogg",
    "ac3": "ac3",
    "eac3": "ec3",
    "flac": "flac",
    "pcm_s16le": "wav",
    "pcm_s24le": "wav",
    "pcm_f32le": "wav",
}


def is_video(path) -> bool:
    """Return True when the file extension is a supported video format."""
    try:
        ext = canonical(Path(path).suffix)
    except Exception:
        return False
    return ext in VIDEO


def _require_video(path) -> None:
    if not is_video(path):
        raise ValueError(f"Not a supported video file: {path}")


def _check_output(out: str, opts: dict) -> None:
    if not opts.get("force") and Path(out).exists():
        raise FileExistsError(
            f"Output already exists: {out} (use --force to overwrite)"
        )


def _resolve_out(out: str | None, src: str, suffix: str, opts: dict, ext: str | None = None) -> str:
    if out:
        return out
    base = Path(opts.get("out_dir") or Path(src).parent)
    suffix_ext = Path(src).suffix if ext is None else f".{ext}"
    return str(base / f"{Path(src).stem}{suffix}{suffix_ext}")


def _parse_time(value) -> float:
    """Parse a time in seconds (int/float) or HH:MM:SS[.xxx] into seconds."""
    if value is None or value == "":
        return 0.0
    text = str(value).strip()
    if ":" in text:
        parts = text.split(":")
        try:
            parts = [float(p) for p in parts]
        except ValueError:
            raise ValueError(f"Invalid time: {value}")
        seconds = 0.0
        for part in parts:
            seconds = seconds * 60 + part
        return seconds
    try:
        return float(text)
    except ValueError:
        raise ValueError(f"Invalid time: {value}")


def _audio_codec(path) -> str | None:
    info = ffprobe(path)
    if not info:
        return None
    raw = info.get("raw", "")
    for line in raw.splitlines():
        if line.strip():
            return line.strip()
    return None


def trim(path, out: str | None = None, opts: dict | None = None) -> str:
    """Trim a video to [start, start+duration] using stream copy (fast, lossless)."""
    opts = opts or {}
    _require_video(path)
    start = _parse_time(opts.get("start"))
    duration = _parse_time(opts.get("duration"))
    if start < 0:
        raise ValueError("Start time must be >= 0")
    if duration <= 0:
        raise ValueError("Duration must be greater than 0")

    output = _resolve_out(out, str(path), "-trimmed", opts)
    _check_output(output, opts)

    ff = require_ffmpeg()
    run(
        [
            ff, "-n",
            "-ss", f"{start:.3f}",
            "-i", str(path),
            "-t", f"{duration:.3f}",
            "-c", "copy",
            output,
        ],
        opts.get("quiet"),
        timeout=_TIMEOUT,
    )
    return output


def crop(path, out: str | None = None, opts: dict | None = None) -> str:
    """Crop the video to a rectangle (x, y, width, height)."""
    opts = opts or {}
    _require_video(path)
    try:
        x = int(opts.get("x", 0))
        y = int(opts.get("y", 0))
        width = int(opts.get("width"))
        height = int(opts.get("height"))
    except (TypeError, ValueError):
        raise ValueError("Crop needs integer x, y, width and height")
    if width <= 0 or height <= 0:
        raise ValueError("Crop width and height must be greater than 0")
    if x < 0 or y < 0:
        raise ValueError("Crop x and y must be >= 0")

    output = _resolve_out(out, str(path), "-cropped", opts)
    _check_output(output, opts)

    ff = require_ffmpeg()
    vf = f"crop={width}:{height}:{x}:{y}"
    run([ff, "-n", "-i", str(path), "-vf", vf, "-c:a", "copy", output],
        opts.get("quiet"), timeout=_TIMEOUT)
    return output


def rotate(path, out: str | None = None, opts: dict | None = None) -> str:
    """Rotate by 90/180/270 degrees and optionally flip horizontally/vertically."""
    opts = opts or {}
    _require_video(path)
    angle = str(opts.get("angle") or "90")
    if angle not in ROTATE_ANGLES:
        raise ValueError(f"Invalid angle: {angle} (choose from {'/'.join(ROTATE_ANGLES)})")

    transpose = {"90": "transpose=1", "180": "transpose=2,transpose=2", "270": "transpose=2"}[angle]
    filters = [transpose]
    if opts.get("flip_h"):
        filters.append("hflip")
    if opts.get("flip_v"):
        filters.append("vflip")
    vf = ",".join(filters)

    output = _resolve_out(out, str(path), f"-rotated{angle}", opts)
    _check_output(output, opts)

    ff = require_ffmpeg()
    run([ff, "-n", "-i", str(path), "-vf", vf, "-c:a", "copy", output],
        opts.get("quiet"), timeout=_TIMEOUT)
    return output


def resize(path, out: str | None = None, opts: dict | None = None) -> str:
    """Scale the video to a target width, keeping aspect ratio (height auto)."""
    opts = opts or {}
    _require_video(path)
    try:
        width = int(opts.get("width"))
    except (TypeError, ValueError):
        raise ValueError("Resize needs an integer width")
    if width <= 0:
        raise ValueError("Resize width must be greater than 0")

    output = _resolve_out(out, str(path), f"-{width}w", opts)
    _check_output(output, opts)

    ff = require_ffmpeg()
    run([ff, "-n", "-i", str(path), "-vf", f"scale={width}:-2", "-c:a", "copy", output],
        opts.get("quiet"), timeout=_TIMEOUT)
    return output


def speed(path, out: str | None = None, opts: dict | None = None) -> str:
    """Change playback speed by a factor (e.g. 2 = twice as fast, 0.5 = half)."""
    opts = opts or {}
    _require_video(path)
    try:
        factor = float(opts.get("factor"))
    except (TypeError, ValueError):
        raise ValueError("Speed needs a numeric factor")
    if factor <= 0:
        raise ValueError("Speed factor must be greater than 0")
    factor = max(0.25, min(4.0, factor))

    output = _resolve_out(out, str(path), f"-x{factor:g}", opts)
    _check_output(output, opts)

    vfilter = f"setpts={1 / factor}*PTS"
    atempo = _atempo_chain(factor)

    ff = require_ffmpeg()
    cmd = [ff, "-n", "-i", str(path), "-filter:v", vfilter]
    if atempo:
        cmd += ["-filter:a", atempo]
    else:
        cmd += ["-an"]
    cmd.append(output)
    run(cmd, opts.get("quiet"), timeout=_TIMEOUT)
    return output


def _atempo_chain(factor: float) -> str:
    """Build an atempo filter chain supporting factors outside 0.5-2.0."""
    if factor == 1.0:
        return ""
    remaining = factor
    parts: list[str] = []
    while remaining > 2.0:
        parts.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        parts.append("atempo=0.5")
        remaining *= 2.0
    parts.append(f"atempo={remaining:.4f}")
    return ",".join(parts)


def mute(path, out: str | None = None, opts: dict | None = None) -> str:
    """Remove the audio track, keeping the video stream as-is."""
    opts = opts or {}
    _require_video(path)

    output = _resolve_out(out, str(path), "-muted", opts)
    _check_output(output, opts)

    ff = require_ffmpeg()
    run([ff, "-n", "-i", str(path), "-c:v", "copy", "-an", output],
        opts.get("quiet"), timeout=_TIMEOUT)
    return output


def extract_audio(path, out: str | None = None, opts: dict | None = None) -> str:
    """Save the audio track as a standalone audio file (codec preserved)."""
    opts = opts or {}
    _require_video(path)
    info = ffprobe(path)
    if not info or not info.get("has_audio"):
        raise ValueError("The video has no audio track to extract")

    codec = _audio_codec(str(path))
    ext = _AUDIO_EXT_BY_CODEC.get(codec, "m4a") if codec else "m4a"
    output = _resolve_out(out, str(path), "-audio", opts, ext=ext)
    _check_output(output, opts)

    ff = require_ffmpeg()
    if codec in _AUDIO_EXT_BY_CODEC:
        run([ff, "-n", "-i", str(path), "-vn", "-c:a", "copy", output],
            opts.get("quiet"), timeout=_TIMEOUT)
    else:
        run([ff, "-n", "-i", str(path), "-vn", "-c:a", "aac", output],
            opts.get("quiet"), timeout=_TIMEOUT)
    return output


def extract_frame(path, out: str | None = None, opts: dict | None = None) -> str:
    """Grab a single snapshot image at the given timestamp."""
    opts = opts or {}
    _require_video(path)
    time = _parse_time(opts.get("time"))

    output = _resolve_out(out, str(path), "-frame", opts, ext="png")
    _check_output(output, opts)

    ff = require_ffmpeg()
    run(
        [ff, "-n", "-ss", f"{time:.3f}", "-i", str(path), "-frames:v", "1", "-q:v", "2", output],
        opts.get("quiet"),
        timeout=_TIMEOUT,
    )
    return output


def run_tool(name: str, paths, out: str | None, out_dir: str | None, opts: dict) -> str:
    """Dispatch a video tool by name; used by the CLI and GUI."""
    options = dict(opts or {})
    if out_dir:
        options["out_dir"] = out_dir
    if out:
        options["output"] = out
    single = paths[0] if paths else None
    if name == "trim":
        if len(paths) != 1:
            raise ValueError("Trim works on a single video file")
        return trim(single, out, options)
    if name == "crop":
        if len(paths) != 1:
            raise ValueError("Crop works on a single video file")
        return crop(single, out, options)
    if name == "rotate":
        if len(paths) != 1:
            raise ValueError("Rotate works on a single video file")
        return rotate(single, out, options)
    if name == "resize":
        if len(paths) != 1:
            raise ValueError("Resize works on a single video file")
        return resize(single, out, options)
    if name == "speed":
        if len(paths) != 1:
            raise ValueError("Speed works on a single video file")
        return speed(single, out, options)
    if name == "mute":
        if len(paths) != 1:
            raise ValueError("Mute works on a single video file")
        return mute(single, out, options)
    if name == "extract-audio":
        if len(paths) != 1:
            raise ValueError("Extract audio works on a single video file")
        return extract_audio(single, out, options)
    if name == "extract-frame":
        if len(paths) != 1:
            raise ValueError("Extract frame works on a single video file")
        return extract_frame(single, out, options)
    raise ValueError(f"Unknown video tool: {name}")


__all__ = [
    "ROTATE_ANGLES", "is_video", "trim", "crop", "rotate", "resize",
    "speed", "mute", "extract_audio", "extract_frame", "run_tool", "BackendError",
]
