"""Tkinter GUI for Conveyr.

Everything is local: files are processed on this machine only.

The interface follows a restrained dark product theme built on the Conveyr
brand accent. All styling is done with the standard `ttk.Style` API, so no
third-party dependencies are required.
"""

from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .core import (
    convert,
    detect,
    valid_targets,
)
from .pdfgui import PdfToolsView
from .picker import pick_directory, pick_files
from .theme import C, _FONT, _STATUS_STYLES, setup_theme

_STATUS_STYLES = {
    "muted": "Muted.TLabel",
    "success": "Success.TLabel",
    "error": "Error.TLabel",
    "info": "Info.TLabel",
}

_EMPTY_STATE_TEXT = (
    "No files yet\n\n"
    "Add files to convert them.\n"
    "No uploads - everything stays on this machine."
)


def _data_home() -> str:
    return os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")


def _icon_path(size: int) -> str:
    return os.path.join(_data_home(), "icons", "hicolor", f"{size}x{size}", "apps", "conveyr.png")


def _installed_icon_paths() -> list[str]:
    """Locate the Conveyr icon installed by install.sh, best size first."""
    sizes = (128, 64, 48, 32, 256)
    return [_icon_path(size) for size in sizes]


def _set_window_icon(root: tk.Tk) -> None:
    for icon_path in _installed_icon_paths():
        if os.path.isfile(icon_path):
            try:
                root.iconphoto(True, tk.PhotoImage(file=icon_path))
                return
            except tk.TclError:
                continue


class ConverterApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(f"Conveyr {__version__} - local file converter")
        self.root.geometry("800x720")
        self.root.minsize(660, 620)
        self.root.configure(background=C["surface"])
        _set_window_icon(root)
        setup_theme(root)

        self.files: list[tuple[str, str]] = []  # (path, detected_format)
        self.target = tk.StringVar()
        self.force = tk.BooleanVar(value=False)
        self.output_dir = tk.StringVar(value="")
        self.queue: "queue.Queue[tuple]" = queue.Queue()
        self.busy = False
        self._logo_img: tk.PhotoImage | None = None

        self._build_ui()
        self._update_list_state()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(100, self._poll_queue)

    # ------------------------------------------------------------------ UI --
    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=14)
        main.pack(fill=tk.BOTH, expand=True)

        self._build_header(main)

        notebook = ttk.Notebook(main)
        notebook.pack(fill=tk.BOTH, expand=True)

        converter_tab = ttk.Frame(notebook, padding=(0, 10))
        notebook.add(converter_tab, text="Converter")

        files = self._build_files(converter_tab)
        files.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        self._build_conversion(converter_tab)
        self._build_output(converter_tab)
        self._build_actions(converter_tab)
        self._build_log(converter_tab)

        self.pdf_view = PdfToolsView(notebook)
        notebook.add(self.pdf_view, text="PDF tools")

    def _build_header(self, main: ttk.Frame) -> None:
        header = ttk.Frame(main)
        header.pack(fill=tk.X, pady=(0, 10))

        logo = self._load_logo()
        if logo is not None:
            ttk.Label(header, image=logo).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Label(header, text="Conveyr", style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Label(header, text="Local file converter", style="Muted.TLabel").pack(
            side=tk.LEFT, padx=(8, 0)
        )
        ttk.Label(header, text=f"v{__version__}", style="Faint.TLabel").pack(side=tk.RIGHT)

        ttk.Separator(main, orient="horizontal").pack(fill=tk.X, pady=(0, 10))

    def _load_logo(self) -> tk.PhotoImage | None:
        for icon_path in (self._icon_path_32(), _icon_path(48), _icon_path(64)):
            if os.path.isfile(icon_path):
                try:
                    self._logo_img = tk.PhotoImage(file=icon_path)
                    return self._logo_img
                except tk.TclError:
                    continue
        return None

    @staticmethod
    def _icon_path_32() -> str:
        return _icon_path(32)

    def _build_files(self, main: ttk.Frame) -> ttk.Labelframe:
        panel = ttk.Labelframe(main, text="Files", style="Panel.TLabelframe", padding=(10, 8))
        panel.rowconfigure(0, weight=1)
        panel.columnconfigure(0, weight=1)

        list_frame = ttk.Frame(panel)
        list_frame.grid(row=0, column=0, sticky="nsew")
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        self.file_list = tk.Listbox(
            list_frame,
            bg=C["field"],
            fg=C["text"],
            selectbackground=C["accent"],
            selectforeground="#ffffff",
            highlightthickness=1,
            highlightbackground=C["border"],
            highlightcolor=C["accent"],
            relief="flat",
            borderwidth=0,
            activestyle="none",
            font=_FONT,
            height=7,
        )
        self.file_list.grid(row=0, column=0, sticky="nsew")
        self.file_list.bind("<<ListboxSelect>>", self._on_select)

        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.file_list.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.file_list.config(yscrollcommand=scroll.set)

        self.empty_state = ttk.Label(
            list_frame, text=_EMPTY_STATE_TEXT, style="Faint.TLabel", justify=tk.CENTER
        )
        self.empty_state.place(relx=0.5, rely=0.45, anchor=tk.CENTER)

        btn_row = ttk.Frame(panel)
        btn_row.grid(row=1, column=0, sticky="ew", pady=(8, 0))

        self.add_btn = ttk.Button(btn_row, text="Add files…", command=self._add_files)
        self.add_btn.pack(side=tk.LEFT)
        self.remove_btn = ttk.Button(btn_row, text="Remove selected", command=self._remove_selected)
        self.remove_btn.pack(side=tk.LEFT, padx=(8, 0))
        self.clear_btn = ttk.Button(btn_row, text="Clear", command=self._clear_files)
        self.clear_btn.pack(side=tk.LEFT, padx=(8, 0))

        return panel

    def _build_conversion(self, main: ttk.Frame) -> None:
        panel = ttk.Labelframe(main, text="Conversion", style="Panel.TLabelframe", padding=(10, 8))
        panel.pack(fill=tk.X, pady=(0, 8))
        panel.columnconfigure(1, weight=1)

        self.source_label = ttk.Label(panel, text="Source: –", style="Muted.TLabel")
        self.source_label.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))

        ttk.Label(panel, text="Convert to", style="Muted.TLabel").grid(
            row=1, column=0, sticky="w", padx=(0, 8)
        )
        self.target_combo = ttk.Combobox(
            panel, textvariable=self.target, state="readonly", width=18
        )
        self.target_combo.grid(row=1, column=1, sticky="ew")

        self.force_check = ttk.Checkbutton(
            panel, text="Overwrite existing files", variable=self.force
        )
        self.force_check.grid(row=1, column=2, sticky="e", padx=(12, 0))

    def _build_output(self, main: ttk.Frame) -> None:
        row = ttk.Frame(main)
        row.pack(fill=tk.X, pady=(0, 8))
        row.columnconfigure(1, weight=1)

        ttk.Label(row, text="Output folder", style="Muted.TLabel").grid(
            row=0, column=0, sticky="w", padx=(0, 8)
        )
        ttk.Entry(row, textvariable=self.output_dir).grid(row=0, column=1, sticky="ew")
        ttk.Button(row, text="Browse…", command=self._browse_output).grid(
            row=0, column=2, padx=(8, 0)
        )
        ttk.Label(row, text="empty = next to the source file", style="Faint.TLabel").grid(
            row=1, column=1, sticky="w", pady=(4, 0)
        )

    def _build_actions(self, main: ttk.Frame) -> None:
        action = ttk.Frame(main)
        action.pack(fill=tk.X, pady=(0, 8))

        self.convert_button = ttk.Button(
            action, text="Convert", style="Primary.TButton", command=self._start_conversion
        )
        self.convert_button.pack(side=tk.LEFT)

        self.status = ttk.Label(action, text="Ready", style="Muted.TLabel")
        self.status.pack(side=tk.LEFT, padx=12)

        self.progress = ttk.Progressbar(action, mode="indeterminate", length=200)

    def _build_log(self, main: ttk.Frame) -> None:
        panel = ttk.Labelframe(main, text="Activity", style="Panel.TLabelframe", padding=(10, 6))
        panel.pack(fill=tk.X)
        panel.columnconfigure(0, weight=1)

        self.log = tk.Text(
            panel,
            height=7,
            bg=C["field"],
            fg=C["muted"],
            insertbackground=C["text"],
            relief="flat",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=C["border"],
            highlightcolor=C["accent"],
            wrap=tk.WORD,
            font=("sans", 9),
            padx=8,
            pady=6,
        )
        self.log.grid(row=0, column=0, sticky="nsew")
        log_scroll = ttk.Scrollbar(panel, orient=tk.VERTICAL, command=self.log.yview)
        log_scroll.grid(row=0, column=1, sticky="ns")
        self.log.config(yscrollcommand=log_scroll.set, state=tk.DISABLED)

        self.log.tag_configure("ok", foreground=C["success"])
        self.log.tag_configure("err", foreground=C["error"])
        self.log.tag_configure("muted", foreground=C["faint"])

    # --------------------------------------------------------------- actions --
    def _add_files(self) -> None:
        paths = pick_files("Choose files to convert", multiple=True)
        if paths is None:
            paths = list(filedialog.askopenfilenames(title="Choose files to convert"))
        if not paths:
            return
        self.file_list.delete(0, tk.END)
        self.files = []
        for path in paths:
            fmt = detect(path)
            if fmt is None:
                self.files.append((path, ""))
                self.file_list.insert(tk.END, f"{Path(path).name}  (unsupported)")
            else:
                self.files.append((path, fmt))
                self.file_list.insert(tk.END, f"{Path(path).name}  ({fmt})")
        self._refresh_targets()
        self._update_list_state()

    def _remove_selected(self) -> None:
        selection = self.file_list.curselection()
        if not selection:
            return
        for index in reversed(selection):
            del self.files[index]
            self.file_list.delete(index)
        self._refresh_targets()
        self._update_list_state()

    def _clear_files(self) -> None:
        self.files = []
        self.file_list.delete(0, tk.END)
        self._refresh_targets()
        self._update_list_state()
        self._clear_log()

    def _on_select(self, _event=None) -> None:
        self.remove_btn.config(state=tk.NORMAL if self.file_list.curselection() else tk.DISABLED)

    def _update_list_state(self) -> None:
        has_files = len(self.files) > 0
        if has_files:
            self.empty_state.place_forget()
        else:
            self.empty_state.place(relx=0.5, rely=0.45, anchor=tk.CENTER)
        self.clear_btn.config(state=tk.NORMAL if has_files else tk.DISABLED)
        self._on_select()

    def _refresh_targets(self) -> None:
        if not self.files:
            self.source_label.config(text="Source: –")
            self.target_combo.config(values=[])
            self.target.set("")
            return

        sources = {fmt for _path, fmt in self.files if fmt}
        label = ", ".join(sorted(sources)) if sources else "unsupported"
        self.source_label.config(text=f"Source: {label}")

        common: set[str] | None = None
        for _path, fmt in self.files:
            if not fmt:
                continue
            targets = set(valid_targets(fmt))
            common = targets if common is None else common & targets
        if not common:
            self.target_combo.config(values=[])
            self.target.set("")
            return

        values = sorted(common)
        self.target_combo.config(values=values)
        if self.target.get() not in values:
            self.target.set(values[0])

    def _browse_output(self) -> None:
        chosen = pick_directory("Choose output folder")
        if chosen is None:
            chosen = filedialog.askdirectory(title="Choose output folder")
        if chosen:
            self.output_dir.set(chosen)

    # ------------------------------------------------------------ conversion --
    def _gather_opts(self) -> dict:
        return {
            "out_dir": self.output_dir.get().strip() or None,
            "force": self.force.get(),
            "quiet": False,
        }

    def _start_conversion(self) -> None:
        if self.busy:
            return

        target = self.target.get()
        if not self.files:
            self._set_status("Add at least one file first.", "error")
            return
        if not target:
            self._set_status("Pick a target format first.", "error")
            return
        for path, fmt in self.files:
            if not fmt:
                self._set_status(f"{Path(path).name}: unsupported format.", "error")
                return
            if target not in valid_targets(fmt):
                self._set_status(
                    f"Cannot convert {Path(path).name} ({fmt}) to {target}.", "error"
                )
                return

        self.busy = True
        self.convert_button.config(state=tk.DISABLED)
        self._set_status("Converting…", "info")
        self.progress.pack(side=tk.RIGHT, padx=(12, 0))
        self.progress.start(12)

        self._clear_log()
        self._append_log("muted", f"-- Converting {len(self.files)} file(s) to {target} --")
        opts = self._gather_opts()
        jobs = list(self.files)
        threading.Thread(target=self._worker, args=(jobs, target, opts), daemon=True).start()

    def _worker(self, jobs, target, opts) -> None:
        converted = 0
        failed = 0
        for path, fmt in jobs:
            try:
                out = convert(path, fmt, target, opts)
                converted += 1
                self.queue.put(("log", "ok", f"ok:  {Path(path).name} -> {out}"))
            except Exception as exc:  # noqa: BLE001 - never leave the GUI stuck
                failed += 1
                self.queue.put(("log", "err", f"err: {Path(path).name}: {exc}"))
        self.queue.put(("done", converted, failed))

    def _poll_queue(self) -> None:
        try:
            while True:
                item = self.queue.get_nowait()
                if item[0] == "log":
                    _kind, tag, text = item
                    self._append_log(tag, text)
                elif item[0] == "done":
                    _kind, converted, failed = item
                    self.busy = False
                    self.convert_button.config(state=tk.NORMAL)
                    self.progress.stop()
                    self.progress.pack_forget()
                    if failed:
                        self._set_status(
                            f"Done: {converted} converted, {failed} failed", "error"
                        )
                    else:
                        self._set_status(f"Done: {converted} converted", "success")
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    def _set_status(self, text: str, kind: str = "muted") -> None:
        self.status.config(text=text, style=_STATUS_STYLES.get(kind, "Muted.TLabel"))

    def _append_log(self, tag: str, text: str) -> None:
        self.log.config(state=tk.NORMAL)
        self.log.insert(tk.END, text + "\n", tag)
        self.log.see(tk.END)
        self.log.config(state=tk.DISABLED)

    def _clear_log(self) -> None:
        self.log.config(state=tk.NORMAL)
        self.log.delete("1.0", tk.END)
        self.log.config(state=tk.DISABLED)

    def _on_close(self) -> None:
        if self.busy or getattr(self, "pdf_view", None) and self.pdf_view.busy:
            messagebox.showinfo("Conveyr", "Please wait for the current operation to finish.")
            return
        self.root.destroy()


def main() -> int:
    root = tk.Tk()
    ConverterApp(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
