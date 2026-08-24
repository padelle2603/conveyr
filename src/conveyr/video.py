"""Video tools: trim/cut and other local operations.

Everything runs locally using ffmpeg. No cloud, no servers.
"""

from __future__ import annotations

from pathlib import Path

from .backends import BackendError, require_ffmpeg, run
from .core import VIDEO, canonical

_TIMEOUT = 600


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


def _resolve_out(out: str | None, src: str, opts: dict) -> str:
    if out:
        return out
    base = Path(opts.get("out_dir") or Path(src).parent)
    return str(base / f"{Path(src).stem}-trimmed{Path(src).suffix}")


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

    output = _resolve_out(out, str(path), opts)
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


def run_tool(name: str, paths, out: str | None, out_dir: str | None, opts: dict) -> str:
    """Dispatch a video tool by name; used by the CLI and GUI."""
    options = dict(opts or {})
    if out_dir:
        options["out_dir"] = out_dir
    if out:
        options["output"] = out
    if name == "trim":
        if len(paths) != 1:
            raise ValueError("Trim works on a single video file")
        return trim(paths[0], out, options)
    raise ValueError(f"Unknown video tool: {name}")


__all__ = [
    "is_video", "trim", "run_tool", "BackendError",
]
