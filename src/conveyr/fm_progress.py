"""Standalone progress window for file manager launches (e.g. Dolphin).

Patterned after arkx::ui::fm_progress:
- Launches a compact, focused progress bar window without the main GUI.
- Runs conversions in a worker thread.
- If conversion is fast/instant, auto-closes immediately with desktop notification (or silent).
- On error, halts auto-close, shows the message and provides a Close button.
- Clean cancellation support.
"""

from __future__ import annotations

import os
import queue
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from .core import canonical, convert, detect, valid_targets
from .gui import _set_window_icon
from .theme import C, _FONT, setup_theme


def has_display() -> bool:
    """Return True if an X11 or Wayland display session is reachable."""
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def _send_notification(title: str, message: str) -> None:
    """Send a lightweight desktop notification if notify-send is available."""
    try:
        subprocess.run(
            ["notify-send", "-a", "Conveyr", "-i", "conveyr", title, message],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        pass


class FmProgressWindow:
    """Compact progress window for background conversions from file manager."""

    def __init__(
        self,
        files: list[str],
        target: str,
        opts: dict | None = None,
    ) -> None:
        self.files = [str(Path(f).resolve()) for f in files if Path(f).is_file()]
        self.target = target.lower().lstrip(".")
        self.opts = dict(opts or {})
        self.queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.cancelled = False
        self.thread: threading.Thread | None = None

        self.root = tk.Tk()
        self.root.title("Conveyr")
        self.root.geometry("420x150")
        self.root.minsize(360, 140)
        self.root.resizable(False, False)
        self.root.configure(background=C["surface"])
        _set_window_icon(self.root)
        setup_theme(self.root)

        # Center on screen
        self.root.eval("tk::PlaceWindow . center")

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(50, self._poll_queue)

    def _build_ui(self) -> None:
        pad = ttk.Frame(self.root, padding=16)
        pad.pack(fill=tk.BOTH, expand=True)

        self.title_lbl = ttk.Label(pad, text="Converting...", style="Title.TLabel")
        self.title_lbl.pack(anchor=tk.W, pady=(0, 4))

        count = len(self.files)
        first_name = Path(self.files[0]).name if count else ""
        sub = f"{first_name} → {self.target}" if count == 1 else f"{count} files → {self.target}"
        self.detail_lbl = ttk.Label(pad, text=sub, style="Muted.TLabel")
        self.detail_lbl.pack(anchor=tk.W, pady=(0, 12))

        self.progress = ttk.Progressbar(pad, mode="indeterminate")
        self.progress.pack(fill=tk.X, pady=(0, 12))
        self.progress.start(10)

        btn_row = ttk.Frame(pad)
        btn_row.pack(fill=tk.X)
        self.action_btn = ttk.Button(btn_row, text="Cancel", command=self._on_close)
        self.action_btn.pack(side=tk.RIGHT)

    def run(self) -> int:
        if not self.files:
            return 1
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()
        self.root.mainloop()
        return 0 if not self.cancelled else 1

    def _on_close(self) -> None:
        self.cancelled = True
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def _poll_queue(self) -> None:
        try:
            while True:
                msg, data = self.queue.get_nowait()
                if msg == "step":
                    filename = str(data)
                    self.detail_lbl.config(text=f"Converting {filename} → {self.target}")
                elif msg == "done":
                    out_paths = data if isinstance(data, list) else []
                    if len(out_paths) == 1:
                        _send_notification("Conveyr", f"Converted to {Path(out_paths[0]).name}")
                    elif len(out_paths) > 1:
                        _send_notification("Conveyr", f"Converted {len(out_paths)} files to {self.target}")
                    self.root.destroy()
                    return
                elif msg == "error":
                    err_msg = str(data)
                    self.progress.stop()
                    self.progress.pack_forget()
                    self.title_lbl.config(text="Conversion failed", style="Error.TLabel")
                    self.detail_lbl.config(text=err_msg)
                    self.action_btn.config(text="Close", command=self.root.destroy)
                    return
        except queue.Empty:
            pass
        self.root.after(50, self._poll_queue)

    def _worker(self) -> None:
        outputs: list[str] = []
        for file_path in self.files:
            if self.cancelled:
                return
            name = Path(file_path).name
            self.queue.put(("step", name))

            src = detect(file_path) or canonical(Path(file_path).suffix)
            if not src:
                self.queue.put(("error", f"Unrecognized format: {name}"))
                return
            if self.target not in valid_targets(src):
                self.queue.put(("error", f"Cannot convert {src} to {self.target}"))
                return

            try:
                out = convert(file_path, src, self.target, self.opts)
                outputs.append(out)
            except Exception as exc:
                self.queue.put(("error", f"{name}: {exc}"))
                return

        self.queue.put(("done", outputs))


def run_with_progress(files: list[str], target: str, opts: dict | None = None) -> int:
    """Entry point for running conversions with a standalone progress window."""
    app = FmProgressWindow(files, target, opts)
    return app.run()
