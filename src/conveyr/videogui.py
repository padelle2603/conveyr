"""Video tools tab for the Conveyr GUI.

A small set of local video operations (currently Trim/cut) that run 100%
locally via ffmpeg.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

from .video import (
    is_video,
    run_tool,
)
from .picker import pick_directory, pick_files
from .theme import C, _FONT, _STATUS_STYLES

_EMPTY_STATE_TEXT = (
    "No files yet\n\n"
    "Add a video to trim it.\n"
    "Everything stays on this machine."
)

_HINTS = {
    "trim": "Cut a portion of the video by start time and duration (fast, lossless).",
}


class VideoToolsView(ttk.Frame):
    """The video tools screen, shown as its own notebook tab."""

    TOOLS = [
        ("trim", "Trim video"),
    ]
    TOOL_NAMES = {key: label for key, label in TOOLS}
    KEY_BY_LABEL = {label: key for key, label in TOOLS}

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent, padding=(14, 12))
        self.files: list[str] = []
        self.tool = tk.StringVar(value="Trim video")
        self.output_dir = tk.StringVar(value="")
        self.force = tk.BooleanVar(value=False)
        self.start = tk.StringVar(value="0")
        self.duration = tk.StringVar(value="")
        self.clear_on_switch = tk.BooleanVar(value=True)
        self.queue: "queue.Queue[tuple]" = queue.Queue()
        self.busy = False

        self._build()
        self._refresh_options()
        self.after(100, self._poll_queue)

    # ---------------------------------------------------------------- UI ----
    def _build(self) -> None:
        self.columnconfigure(0, weight=1)

        self._build_tool_row()
        files = self._build_files()
        files.grid(row=1, column=0, sticky="nsew", pady=(10, 8))
        self.rowconfigure(1, weight=1)
        self.rowconfigure(5, weight=1)
        self._build_options()
        self._build_output()
        self._build_actions()
        self._build_log()

    def _build_tool_row(self) -> None:
        row = ttk.Frame(self)
        row.grid(row=0, column=0, sticky="ew")
        row.columnconfigure(1, weight=1)

        ttk.Label(row, text="Tool", style="Muted.TLabel").grid(
            row=0, column=0, sticky="w", padx=(0, 8)
        )
        self.tool_combo = ttk.Combobox(
            row, textvariable=self.tool, state="readonly", width=20
        )
        self.tool_combo["values"] = [label for _key, label in self.TOOLS]
        self.tool_combo.grid(row=0, column=1, sticky="w")
        self.tool_combo.bind("<<ComboboxSelected>>", self._on_tool_changed)

        self.hint = ttk.Label(
            row,
            text=_HINTS.get(self._current_tool(), ""),
            style="Faint.TLabel",
        )
        self.hint.grid(row=1, column=1, sticky="w", pady=(4, 0))

    def _build_files(self) -> ttk.Labelframe:
        panel = ttk.Labelframe(self, text="Files", style="Panel.TLabelframe", padding=(10, 8))
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
            selectmode=tk.EXTENDED,
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
        self.remove_btn = ttk.Button(
            btn_row, text="Remove selected", command=self._remove_selected, state=tk.DISABLED
        )
        self.remove_btn.pack(side=tk.LEFT, padx=(8, 0))
        self.clear_btn = ttk.Button(btn_row, text="Clear", command=self._clear_files)
        self.clear_btn.pack(side=tk.LEFT, padx=(8, 0))

        return panel

    def _build_options(self) -> None:
        panel = ttk.Labelframe(self, text="Options", style="Panel.TLabelframe", padding=(10, 8))
        panel.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        panel.columnconfigure(1, weight=1)

        self.start_lbl, self.start_ent = self._option_entry(
            panel, 0, "Start (s or HH:MM:SS):", self.start
        )
        self.dur_lbl, self.dur_ent = self._option_entry(
            panel, 1, "Duration (s or HH:MM:SS):", self.duration
        )

    def _option_entry(self, panel, row, label, var) -> tuple[ttk.Label, ttk.Entry]:
        lbl = ttk.Label(panel, text=label, style="Muted.TLabel")
        lbl.grid(row=row, column=0, sticky="w", padx=(0, 8), pady=2)
        ent = ttk.Entry(panel, textvariable=var, width=18)
        ent.grid(row=row, column=1, sticky="w", pady=2)
        return lbl, ent

    def _build_output(self) -> None:
        row = ttk.Frame(self)
        row.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        row.columnconfigure(1, weight=1)

        ttk.Label(row, text="Output folder", style="Muted.TLabel").grid(
            row=0, column=0, sticky="w", padx=(0, 8)
        )
        ttk.Entry(row, textvariable=self.output_dir).grid(row=0, column=1, sticky="ew")
        ttk.Button(row, text="Browse…", command=self._browse_output).grid(
            row=0, column=2, padx=(8, 0)
        )
        ttk.Checkbutton(row, text="Overwrite", variable=self.force).grid(
            row=0, column=3, sticky="e", padx=(12, 0)
        )
        ttk.Label(row, text="empty = next to the source file", style="Faint.TLabel").grid(
            row=1, column=1, sticky="w", pady=(4, 0)
        )

    def _build_actions(self) -> None:
        action = ttk.Frame(self)
        action.grid(row=4, column=0, sticky="ew", pady=(0, 8))

        self.run_button = ttk.Button(
            action, text="Run", style="Primary.TButton", command=self._run
        )
        self.run_button.pack(side=tk.LEFT)

        self.status = ttk.Label(action, text="Ready", style="Muted.TLabel")
        self.status.pack(side=tk.LEFT, padx=12)

        self.progress = ttk.Progressbar(action, mode="indeterminate", length=200)

    def _build_log(self) -> None:
        panel = ttk.Labelframe(self, text="Activity", style="Panel.TLabelframe", padding=(10, 6))
        panel.grid(row=5, column=0, sticky="ew")
        panel.columnconfigure(0, weight=1)

        self.log = tk.Text(
            panel,
            height=6,
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

    # ------------------------------------------------------------ file list --
    def _add_files(self) -> None:
        paths = pick_files("Choose video files", multiple=True)
        if paths is None:
            paths = list(filedialog.askopenfilenames(title="Choose video files"))
        if not paths:
            return
        for path in paths:
            if path in self.files:
                continue
            self.files.append(path)
            self.file_list.insert(tk.END, Path(path).name)
        self._update_list_state()

    def _remove_selected(self) -> None:
        selection = self.file_list.curselection()
        if not selection:
            return
        for index in reversed(selection):
            del self.files[index]
            self.file_list.delete(index)
        self._update_list_state()

    def _clear_files(self) -> None:
        self.files = []
        self.file_list.delete(0, tk.END)
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

    def _current_tool(self) -> str:
        return self.KEY_BY_LABEL.get(self.tool.get(), self.tool.get())

    def _refresh_options(self) -> None:
        tool = self._current_tool()
        self.hint.config(text=_HINTS.get(tool, ""))

    def _on_tool_changed(self, _event=None) -> None:
        self._refresh_options()
        if self.busy:
            return
        if self.clear_on_switch.get() and self.files:
            self._clear_files()
            self._status(f"Files cleared for {self.TOOL_NAMES[self._current_tool()]}.", "muted")

    def _compatible(self, tool: str, paths: list[str]) -> bool:
        if tool != "trim":
            return False
        return len(paths) == 1 and is_video(paths[0])

    def _incompat_message(self, tool: str, paths: list[str]) -> str:
        if len(paths) != 1:
            return "Trim works on a single video file."
        return f"{Path(paths[0]).name}: not a supported video file."

    def _browse_output(self) -> None:
        chosen = pick_directory("Choose output folder")
        if chosen is None:
            chosen = filedialog.askdirectory(title="Choose output folder")
        if chosen:
            self.output_dir.set(chosen)

    # -------------------------------------------------------------- actions --
    def _gather_opts(self) -> dict:
        return {
            "force": self.force.get(),
            "quiet": False,
            "start": self.start.get().strip(),
            "duration": self.duration.get().strip(),
        }

    def _run(self) -> None:
        if self.busy:
            return
        tool = self._current_tool()
        paths = list(self.files)
        if not paths:
            self._status("Add at least one file first.", "error")
            return
        if not self._compatible(tool, paths):
            self._status(self._incompat_message(tool, paths), "error")
            return

        out = None
        out_dir = self.output_dir.get().strip() or None

        self.busy = True
        self.run_button.config(state=tk.DISABLED)
        self._status("Working…", "info")
        self.progress.pack(side=tk.RIGHT, padx=(12, 0))
        self.progress.start(12)

        self._clear_log()
        self._append_log("muted", f"-- {self.TOOL_NAMES[tool]} --")
        threading.Thread(
            target=self._worker, args=(tool, paths, out, out_dir, self._gather_opts()), daemon=True
        ).start()

    def _worker(self, tool, paths, out, out_dir, opts) -> None:
        try:
            result = run_tool(tool, paths, out, out_dir, opts)
            self.queue.put(("log", "ok", f"ok: {result}"))
            self.queue.put(("done", True))
        except Exception as exc:  # noqa: BLE001 - never leave the GUI stuck
            self.queue.put(("log", "err", f"err: {exc}"))
            self.queue.put(("done", False))

    def _poll_queue(self) -> None:
        try:
            while True:
                item = self.queue.get_nowait()
                if item[0] == "log":
                    _kind, tag, text = item
                    self._append_log(tag, text)
                elif item[0] == "done":
                    _kind, ok = item
                    self.busy = False
                    self.run_button.config(state=tk.NORMAL)
                    self.progress.stop()
                    self.progress.pack_forget()
                    self._status("Done" if ok else "Failed", "success" if ok else "error")
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    # ------------------------------------------------------------ utilities --
    def _status(self, text: str, kind: str = "muted") -> None:
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
