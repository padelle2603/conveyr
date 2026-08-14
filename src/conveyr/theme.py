"""Shared dark theme used by every Conveyr GUI view.

Defined with the standard ``ttk.Style`` API so no third-party widgets are
required. Both the converter window and the PDF tools tab import from here.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

C = {
    "surface": "#1e1e22",      # main content surface
    "panel": "#232329",        # second neutral layer (panels, buttons)
    "field": "#18181b",        # text fields / log
    "border": "#33333a",       # hairline borders
    "text": "#e4e4e7",         # primary text
    "muted": "#a1a1aa",        # secondary text
    "faint": "#71717a",        # tertiary text / disabled hints
    "accent": "#4f46e5",       # brand accent (primary action, selection)
    "accent_hover": "#6366f1",
    "accent_press": "#4338ca",
    "success": "#22c55e",
    "error": "#f87171",
    "warning": "#f59e0b",
    "info": "#60a5fa",
    "btn_bg": "#2a2a30",
    "btn_hover": "#33333a",
    "btn_press": "#18181b",
    "disabled_fg": "#52525b",
}

_FONT = ("sans", 10)

_STATUS_STYLES = {
    "muted": "Muted.TLabel",
    "success": "Success.TLabel",
    "error": "Error.TLabel",
    "info": "Info.TLabel",
}


def setup_theme(root: tk.Tk) -> None:
    """Configure the dark product theme with full component states."""
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(
        ".",
        background=C["surface"],
        foreground=C["text"],
        fieldbackground=C["field"],
        bordercolor=C["border"],
        troughcolor=C["panel"],
        font=_FONT,
    )

    # Popdown list of every combobox follows the dark theme.
    root.option_add("*TCombobox*Listbox.background", C["field"])
    root.option_add("*TCombobox*Listbox.foreground", C["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", C["accent"])
    root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")

    style.configure("TFrame", background=C["surface"])
    style.configure("TLabel", background=C["surface"], foreground=C["text"])
    style.configure("Muted.TLabel", background=C["surface"], foreground=C["muted"])
    style.configure("Faint.TLabel", background=C["surface"], foreground=C["faint"])
    style.configure("Title.TLabel", background=C["surface"], foreground=C["text"], font=("sans", 13, "bold"))
    style.configure("Success.TLabel", background=C["surface"], foreground=C["success"])
    style.configure("Error.TLabel", background=C["surface"], foreground=C["error"])
    style.configure("Info.TLabel", background=C["surface"], foreground=C["info"])

    style.configure(
        "Panel.TLabelframe",
        background=C["surface"],
        bordercolor=C["border"],
        relief="flat",
    )
    style.configure(
        "Panel.TLabelframe.Label",
        background=C["surface"],
        foreground=C["muted"],
        font=("sans", 9, "bold"),
    )

    style.configure(
        "TButton",
        background=C["btn_bg"],
        foreground=C["text"],
        bordercolor=C["border"],
        focuscolor=C["accent"],
        padding=(12, 5),
    )
    style.map(
        "TButton",
        background=[("pressed", C["btn_press"]), ("active", C["btn_hover"])],
        bordercolor=[("focus", C["accent"])],
        foreground=[("disabled", C["disabled_fg"])],
    )

    style.configure(
        "Primary.TButton",
        background=C["accent"],
        foreground="#ffffff",
        bordercolor=C["accent"],
        focuscolor=C["accent_hover"],
        padding=(16, 5),
    )
    style.map(
        "Primary.TButton",
        background=[("pressed", C["accent_press"]), ("active", C["accent_hover"]), ("disabled", C["panel"])],
        bordercolor=[("focus", C["accent_hover"])],
        foreground=[("disabled", C["disabled_fg"])],
    )

    style.configure(
        "TEntry",
        fieldbackground=C["field"],
        foreground=C["text"],
        insertcolor=C["text"],
        bordercolor=C["border"],
        lightcolor=C["field"],
        darkcolor=C["field"],
    )
    style.map("TEntry", bordercolor=[("focus", C["accent"])])

    style.configure(
        "TCombobox",
        fieldbackground=C["field"],
        background=C["field"],
        foreground=C["text"],
        arrowcolor=C["muted"],
        bordercolor=C["border"],
        selectbackground=C["accent"],
        selectforeground="#ffffff",
        lightcolor=C["field"],
        darkcolor=C["field"],
    )
    style.map(
        "TCombobox",
        bordercolor=[("focus", C["accent"])],
        fieldbackground=[("readonly", C["field"])],
    )

    style.configure(
        "TCheckbutton",
        background=C["surface"],
        foreground=C["text"],
        indicatorbackground=C["field"],
        indicatorforeground=C["accent"],
        bordercolor=C["border"],
        lightcolor=C["field"],
        darkcolor=C["field"],
    )
    style.map("TCheckbutton", background=[("active", C["surface"])])

    style.configure(
        "Horizontal.TProgressbar",
        background=C["accent"],
        troughcolor=C["panel"],
        bordercolor=C["surface"],
        lightcolor=C["accent"],
        darkcolor=C["accent"],
    )

    style.configure(
        "Vertical.TScrollbar",
        background="#3f3f46",
        troughcolor=C["surface"],
        bordercolor=C["surface"],
        arrowcolor=C["muted"],
    )
    style.map("Vertical.TScrollbar", background=[("active", C["btn_hover"])])

    style.configure(
        "TNotebook",
        background=C["surface"],
        bordercolor=C["border"],
        tabmargins=(4, 6, 4, 0),
    )
    style.configure(
        "TNotebook.Tab",
        background=C["panel"],
        foreground=C["muted"],
        bordercolor=C["border"],
        padding=(16, 6),
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", C["accent"]), ("active", C["btn_hover"])],
        foreground=[("selected", "#ffffff")],
    )
