"""Thin wrappers around the external command-line backends.

Every subprocess is launched without a shell for safety. Missing binaries
produce a :class:`BackendError` carrying a per-distro install hint.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

_DISTRO_ID = "unknown"


def _distro_id() -> str:
    global _DISTRO_ID
    if _DISTRO_ID != "unknown":
        return _DISTRO_ID
    try:
        for line in Path("/etc/os-release").read_text().splitlines():
            if line.startswith("ID="):
                _DISTRO_ID = line.split("=", 1)[1].strip().strip('"')
                break
    except OSError:
        pass
    return _DISTRO_ID


_PACKAGE_MANAGERS = {
    "debian": "apt",
    "ubuntu": "apt",
    "linuxmint": "apt",
    "fedora": "dnf",
    "rhel": "dnf",
    "centos": "dnf",
    "rocky": "dnf",
    "almalinux": "dnf",
    "arch": "pacman",
    "cachyos": "pacman",
    "manjaro": "pacman",
    "endeavouros": "pacman",
    "opensuse-leap": "zypper",
    "opensuse-tumbleweed": "zypper",
    "suse": "zypper",
}

_DISTRO_PACKAGES = {
    "debian": ("ffmpeg", "imagemagick", "potrace", "poppler-utils", "ghostscript", "qpdf"),
    "ubuntu": ("ffmpeg", "imagemagick", "potrace", "poppler-utils", "ghostscript", "qpdf"),
    "linuxmint": ("ffmpeg", "imagemagick", "potrace", "poppler-utils", "ghostscript", "qpdf"),
    "fedora": ("ffmpeg-free", "imagemagick", "potrace", "poppler-utils", "ghostscript", "qpdf"),
    "rhel": ("ffmpeg-free", "imagemagick", "potrace", "poppler-utils", "ghostscript", "qpdf"),
    "centos": ("ffmpeg-free", "imagemagick", "potrace", "poppler-utils", "ghostscript", "qpdf"),
    "rocky": ("ffmpeg-free", "imagemagick", "potrace", "poppler-utils", "ghostscript", "qpdf"),
    "almalinux": ("ffmpeg-free", "imagemagick", "potrace", "poppler-utils", "ghostscript", "qpdf"),
    "arch": ("ffmpeg", "imagemagick", "potrace", "poppler", "ghostscript", "qpdf"),
    "cachyos": ("ffmpeg", "imagemagick", "potrace", "poppler", "ghostscript", "qpdf"),
    "manjaro": ("ffmpeg", "imagemagick", "potrace", "poppler", "ghostscript", "qpdf"),
    "endeavouros": ("ffmpeg", "imagemagick", "potrace", "poppler", "ghostscript", "qpdf"),
    "opensuse-leap": ("ffmpeg", "imagemagick", "potrace", "poppler-tools", "ghostscript", "qpdf"),
    "opensuse-tumbleweed": ("ffmpeg", "imagemagick", "potrace", "poppler-tools", "ghostscript", "qpdf"),
    "suse": ("ffmpeg", "imagemagick", "potrace", "poppler-tools", "ghostscript", "qpdf"),
}


class BackendError(RuntimeError):
    """Raised when a backend binary is missing or a command fails."""

    def __init__(self, message: str, stderr: str = "") -> None:
        super().__init__(message)
        self.stderr = stderr


def install_hint() -> str:
    """Return a human-readable install command for this distro."""
    distro = _distro_id()
    pm = _PACKAGE_MANAGERS.get(distro)
    pkgs = _DISTRO_PACKAGES.get(distro)
    if pm and pkgs:
        return f"sudo {pm} install {' '.join(pkgs)}"
    return (
        "install ffmpeg, imagemagick, potrace, poppler-utils, "
        "ghostscript and qpdf for your distribution"
    )


def _find(*names: str):
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return None


def find_image_magick():
    """ImageMagick 7 ships `magick`; v6 ships `convert`."""
    return _find("magick", "convert")


def find_rsvg():
    return shutil.which("rsvg-convert")


def find_ffmpeg():
    return shutil.which("ffmpeg")


def find_ffprobe():
    return shutil.which("ffprobe")


def find_potrace():
    return shutil.which("potrace")


def find_gs():
    return shutil.which("gs")


def find_qpdf():
    return shutil.which("qpdf")


def find_pdfunite():
    return shutil.which("pdfunite")


def find_pdfseparate():
    return shutil.which("pdfseparate")


def find_pdftotext():
    return shutil.which("pdftotext")


def find_pdftoppm():
    return shutil.which("pdftoppm")


def require_ffmpeg() -> str:
    exe = find_ffmpeg()
    if not exe:
        raise BackendError(
            "ffmpeg is required for audio/video conversion.\n"
            f"Install it with: {install_hint()}"
        )
    return exe


def require_image_magick() -> str:
    exe = find_image_magick()
    if not exe:
        raise BackendError(
            "ImageMagick is required for image conversion.\n"
            f"Install it with: {install_hint()}"
        )
    return exe


def require_potrace() -> str:
    exe = find_potrace()
    if not exe:
        raise BackendError(
            "potrace is required for raster-to-SVG vector tracing.\n"
            f"Install it with: {install_hint()}"
        )
    return exe


def require_gs() -> str:
    exe = find_gs()
    if not exe:
        raise BackendError(
            "ghostscript (gs) is required for PDF compression.\n"
            f"Install it with: {install_hint()}"
        )
    return exe


def require_qpdf() -> str:
    exe = find_qpdf()
    if not exe:
        raise BackendError(
            "qpdf is required for PDF rotation and password protection.\n"
            f"Install it with: {install_hint()}"
        )
    return exe


def require_pdfunite() -> str:
    exe = find_pdfunite()
    if not exe:
        raise BackendError(
            "pdfunite (poppler-utils) is required for merging PDFs.\n"
            f"Install it with: {install_hint()}"
        )
    return exe


def require_pdfseparate() -> str:
    exe = find_pdfseparate()
    if not exe:
        raise BackendError(
            "pdfseparate (poppler-utils) is required for splitting PDFs.\n"
            f"Install it with: {install_hint()}"
        )
    return exe


def require_pdftotext() -> str:
    exe = find_pdftotext()
    if not exe:
        raise BackendError(
            "pdftotext (poppler-utils) is required for PDF text extraction.\n"
            f"Install it with: {install_hint()}"
        )
    return exe


def require_pdftoppm() -> str:
    exe = find_pdftoppm()
    if not exe:
        raise BackendError(
            "pdftoppm (poppler-utils) is required for PDF-to-image conversion.\n"
            f"Install it with: {install_hint()}"
        )
    return exe


def run(command, quiet: bool = False, ok_codes=(0,), timeout: float | None = None) -> subprocess.CompletedProcess:
    """Run a command list without a shell and surface failures.

    ``timeout`` guards against hung backends: when the command does not finish
    in time it is killed and a :class:`BackendError` is raised instead of the
    app waiting forever.
    """
    try:
        proc = subprocess.run(
            command,
            stdout=subprocess.PIPE if quiet else None,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise BackendError(
            f"Command timed out after {int(timeout or 0)}s: {' '.join(command)}"
        ) from exc
    except OSError as exc:
        raise BackendError(f"Failed to launch {' '.join(command)}: {exc}") from exc
    if proc.returncode not in ok_codes:
        stderr = (proc.stderr or "").strip()
        detail = stderr[-2000:] if stderr else "no error output"
        raise BackendError(
            f"Command failed ({proc.returncode}): {' '.join(command)}\n{detail}",
            stderr=stderr,
        )
    return proc


def ffprobe(path) -> dict | None:
    """Return container + stream summary via ffprobe, or None if unavailable."""
    exe = find_ffprobe()
    if not exe:
        return None
    probe = None

    def ask(selectors):
        nonlocal probe
        try:
            result = subprocess.run(
                [exe, "-v", "error", "-of", "default=nw=1:nk=1", *selectors, str(path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            probe = result.stdout.strip()
            return probe
        except OSError:
            return ""

    fmt = ask(["-show_entries", "format=format_name"])
    if not fmt:
        return None
    video = bool(ask(["-select_streams", "v:0", "-show_entries", "stream=codec_type"]))
    audio = bool(ask(["-select_streams", "a:0", "-show_entries", "stream=codec_type"]))
    return {
        "format_name": fmt,
        "has_video": video,
        "has_audio": audio,
        "raw": probe,
    }