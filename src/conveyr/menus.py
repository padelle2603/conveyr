"""Dolphin "Convert" service menus, registered by Conveyr itself.

Directly patterned after arkx::core::menus:
- An AppImage cannot write into ~/.local/share/kio/servicemenus/ on its own.
- When running as an AppImage ($APPIMAGE is set), Conveyr auto-installs the service
  menus pointing directly to the real AppImage executable.
- The icons are copied to ~/.local/share/icons/hicolor/256x256/apps/conveyr.png so they
  outlive temporary mounts.
- Files are marked chmod 0o755 (otherwise Dolphin rejects user-local service menus).
- kbuildsycoca6 / kbuildsycoca5 is invoked to refresh Dolphin cache.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

# Templates stored inside packaging/servicemenus or embedded as strings
MENU_DIR = Path(__file__).resolve().parents[2] / "packaging" / "servicemenus"


def _data_home() -> Path:
    val = os.environ.get("XDG_DATA_HOME")
    if val and val.strip():
        return Path(val)
    home = os.environ.get("HOME")
    return Path(home, ".local", "share") if home else Path(".")


def dest_dir() -> Path:
    """Where KIO looks for user-local service menus."""
    return _data_home() / "kio" / "servicemenus"


def appimage_path() -> Path | None:
    """Path of the running AppImage, or None outside one."""
    val = os.environ.get("APPIMAGE")
    return Path(val) if val else None


def stable_icon_path() -> Path | None:
    """Copy the bundle's icon somewhere that outlives the temporary mount."""
    appdir = os.environ.get("APPDIR")
    src = None
    if appdir:
        candidate = Path(appdir) / "conveyr.png"
        if candidate.is_file():
            src = candidate

    if not src:
        assets = Path(__file__).resolve().parents[2] / "assets" / "icons" / "conveyr_256x256.png"
        if assets.is_file():
            src = assets

    if not src:
        return None

    dest = _data_home() / "icons" / "hicolor" / "256x256" / "apps" / "conveyr.png"
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        return dest
    except OSError:
        return None


def _quote_exec(path: str) -> str:
    """Quote a path for Exec= desktop entries only when needed."""
    if not any(c in path for c in (" ", "\t", '"', "'", "\\")):
        return path
    escaped = path.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _rewrite(template: str, exe: str, icon: str | None = None) -> str:
    """Point template at the real executable and icon."""
    quoted = _quote_exec(exe)
    out: list[str] = []
    for line in template.splitlines():
        if line.startswith("TryExec="):
            continue
        if line == "Exec=conveyr" or line.startswith("Exec=conveyr "):
            rest = line[len("Exec=conveyr"):]
            out.append(f"Exec={quoted}{rest}")
            continue
        if icon and line.startswith("Icon=conveyr"):
            rest = line[len("Icon=conveyr"):]
            out.append(f"Icon={icon}{rest}")
            continue
        out.append(line)
    return "\n".join(out) + "\n"


def _read_templates() -> list[tuple[str, str]]:
    """Read service menu templates from bundle or source directory."""
    items: list[tuple[str, str]] = []
    names = ["conveyr-image.desktop", "conveyr-video.desktop", "conveyr-audio.desktop"]

    # In PyInstaller, data files may be extracted to sys._MEIPASS
    meipass = getattr(__import__("sys"), "_MEIPASS", None)
    search_dirs = []
    if meipass:
        search_dirs.append(Path(meipass) / "packaging" / "servicemenus")
    search_dirs.append(MENU_DIR)

    for name in names:
        found = False
        for sdir in search_dirs:
            p = sdir / name
            if p.is_file():
                try:
                    items.append((name, p.read_text(encoding="utf-8")))
                    found = True
                    break
                except OSError:
                    pass
    return items


def install(exe: Path, icon: Path | None = None) -> list[Path]:
    """Install service menus for exe. Returns files written."""
    dir_path = dest_dir()
    dir_path.mkdir(parents=True, exist_ok=True)

    exe_str = str(exe)
    icon_str = str(icon) if icon else None

    written: list[Path] = []
    for name, content in _read_templates():
        target = dir_path / name
        rewritten = _rewrite(content, exe_str, icon_str)
        target.write_text(rewritten, encoding="utf-8")
        try:
            target.chmod(0o755)
        except OSError:
            pass
        written.append(target)

    refresh_kio()
    return written


def uninstall() -> list[Path]:
    """Remove all Conveyr service menus."""
    dir_path = dest_dir()
    removed: list[Path] = []
    names = ["conveyr-image.desktop", "conveyr-video.desktop", "conveyr-audio.desktop"]
    for name in names:
        target = dir_path / name
        if target.is_file():
            try:
                target.unlink()
                removed.append(target)
            except OSError:
                pass
    refresh_kio()
    return removed


def refresh_kio() -> None:
    """Ask KIO/Dolphin to re-scan service menus. Best effort."""
    for cmd in ["kbuildsycoca6", "kbuildsycoca5"]:
        if shutil.which(cmd):
            try:
                subprocess.run(
                    [cmd, "--noincremental"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
                return
            except OSError:
                pass


def auto_install() -> bool:
    """Register the service menus once at launch when running as an AppImage."""
    exe = appimage_path()
    if not exe:
        return False

    # Check if marker already exists or if menus are installed
    marker = _data_home() / "conveyr" / ".servicemenus_installed"
    if marker.is_file():
        return False

    icon = stable_icon_path()
    try:
        written = install(exe, icon)
        if written:
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text("1\n", encoding="utf-8")
            return True
    except OSError:
        pass
    return False
