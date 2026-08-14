"""Native system file pickers.

The Tk file dialog is dated and can be glitchy under Wayland, so Conveyr
prefers the desktop's own file chooser: ``kdialog`` on KDE, ``zenity`` on
GNOME. When neither is installed the caller falls back to the built-in Tk
dialog.

All selection is 100% local - these tools just ask the desktop to pick files.
"""

from __future__ import annotations

import shutil
import subprocess


def native_picker() -> str | None:
    """Return the name of the preferred native picker, or None."""
    if shutil.which("kdialog"):
        return "kdialog"
    if shutil.which("zenity"):
        return "zenity"
    return None


def _build_files_cmd(picker: str, title: str, multiple: bool) -> list[str]:
    if picker == "kdialog":
        cmd = ["kdialog", "--title", title, "--getopenfilename"]
        if multiple:
            cmd.append("--multiple")
        return cmd
    cmd = ["zenity", "--file-selection", "--title", title]
    if multiple:
        cmd += ["--multiple", "--separator=\n"]
    return cmd


def _build_dir_cmd(picker: str, title: str) -> list[str]:
    if picker == "kdialog":
        return ["kdialog", "--title", title, "--getexistingdirectory"]
    return ["zenity", "--file-selection", "--directory", "--title", title]


def _run(cmd: list[str]) -> str:
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=300,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if proc.returncode != 0:
        return ""
    return (proc.stdout or "").strip()


def pick_files(title: str, multiple: bool = False) -> list[str] | None:
    """Pick one or more files.

    Returns ``None`` when no native picker is available (caller should fall
    back to Tk), an empty list when the user cancelled, or the chosen paths.
    """
    picker = native_picker()
    if picker is None:
        return None
    output = _run(_build_files_cmd(picker, title, multiple))
    if not output:
        return []
    paths = [line.strip() for line in output.splitlines() if line.strip()]
    return paths


def pick_directory(title: str) -> str | None:
    """Pick a directory. Returns None on cancel or if no native picker exists."""
    picker = native_picker()
    if picker is None:
        return None
    output = _run(_build_dir_cmd(picker, title))
    if not output:
        return None
    return output.splitlines()[0].strip() or None