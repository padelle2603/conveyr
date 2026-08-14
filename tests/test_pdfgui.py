"""Tests for the PDF tools GUI view (tool label/key handling, resize safety)."""

from __future__ import annotations

import os
import tempfile
import threading
import unittest
from unittest import mock

import tkinter as tk

from conveyr import pdfgui

try:
    _ROOT = tk.Tk()
    _ROOT.withdraw()
    _HAS_DISPLAY = True
except tk.TclError:
    _HAS_DISPLAY = False


class _SyncThread:
    """Runs a Thread's target synchronously in start()."""

    def __init__(self, *args, **kwargs):
        self._target = kwargs.get("target")
        self._args = kwargs.get("args", ())
        self._kwargs = kwargs.get("kwargs", {})
        self.daemon = kwargs.get("daemon", False)

    def start(self):
        self._target(*self._args, **self._kwargs)


def _make_view():
    parent = tk.Frame(_ROOT)
    return pdfgui.PdfToolsView(parent)


@unittest.skipUnless(_HAS_DISPLAY, "no display available")
class ToolKeyTest(unittest.TestCase):
    def setUp(self):
        self.view = _make_view()

    def tearDown(self):
        self.view.destroy()

    def test_label_to_key(self):
        self.view.tool.set("Images to PDF")
        self.assertEqual(self.view._current_tool(), "from-images")

    def test_key_passthrough(self):
        self.view.tool.set("from-images")
        self.assertEqual(self.view._current_tool(), "from-images")

    def test_default_label(self):
        self.assertEqual(self.view.tool.get(), "Merge PDFs")
        self.assertEqual(self.view._current_tool(), "merge")


@unittest.skipUnless(_HAS_DISPLAY, "no display available")
class OptionsTest(unittest.TestCase):
    def setUp(self):
        self.view = _make_view()

    def tearDown(self):
        self.view.destroy()

    def _visible(self, widget):
        return bool(widget.winfo_manager())

    def test_compress_shows_preset(self):
        self.view.tool.set("Compress PDF")
        self.view._refresh_options()
        self.assertTrue(self._visible(self.view.preset_combo))
        self.assertFalse(self._visible(self.view.angle_combo))

    def test_rotate_shows_angle(self):
        self.view.tool.set("Rotate PDF")
        self.view._refresh_options()
        self.assertTrue(self._visible(self.view.angle_combo))
        self.assertFalse(self._visible(self.view.format_combo))

    def test_to_images_shows_format(self):
        self.view.tool.set("PDF to Images")
        self.view._refresh_options()
        self.assertTrue(self._visible(self.view.format_combo))

    def test_protect_shows_password(self):
        self.view.tool.set("Protect PDF")
        self.view._refresh_options()
        self.assertTrue(self._visible(self.view.pass_ent))

    def test_merge_shows_no_options(self):
        self.view.tool.set("Merge PDFs")
        self.view._refresh_options()
        self.assertFalse(self._visible(self.view.preset_combo))
        self.assertFalse(self._visible(self.view.angle_combo))
        self.assertFalse(self._visible(self.view.format_combo))
        self.assertFalse(self._visible(self.view.pass_ent))


@unittest.skipUnless(_HAS_DISPLAY, "no display available")
class RunTest(unittest.TestCase):
    def setUp(self):
        self.view = _make_view()
        self.pdf = tempfile.mktemp(suffix=".pdf")
        with open(self.pdf, "w") as fh:
            fh.write("%PDF-1.4\n")
        self.view.files = [self.pdf]
        self.view.file_list.insert(tk.END, os.path.basename(self.pdf))

    def tearDown(self):
        self.view.destroy()
        os.unlink(self.pdf)

    def test_run_uses_tool_key_not_label(self):
        self.view.tool.set("Split PDF")
        with mock.patch.object(pdfgui, "run_tool", return_value=["/tmp/page-1.pdf"]) as m, \
             mock.patch("conveyr.pdfgui.threading.Thread", _SyncThread):
            self.view._run()
            self.view._poll_queue()
        self.assertEqual(m.call_args[0][0], "split")
        self.assertFalse(self.view.busy)

    def test_run_images_to_pdf(self):
        img1 = tempfile.mktemp(suffix=".png")
        img2 = tempfile.mktemp(suffix=".jpg")
        with open(img1, "w") as fh:
            fh.write("x")
        with open(img2, "w") as fh:
            fh.write("x")
        self.view.files = [img1, img2]
        self.view.tool.set("Images to PDF")
        with mock.patch.object(pdfgui, "run_tool", return_value="/tmp/out.pdf") as m, \
             mock.patch("conveyr.pdfgui.threading.Thread", _SyncThread):
            self.view._run()
            self.view._poll_queue()
        self.assertEqual(m.call_args[0][0], "from-images")
        self.assertFalse(self.view.busy)
        os.unlink(img1)
        os.unlink(img2)


def _make_pdf(tmpdir, name="f.pdf"):
    path = os.path.join(tmpdir, name)
    with open(path, "w") as fh:
        fh.write("%PDF-1.4\n")
    return path


@unittest.skipUnless(_HAS_DISPLAY, "no display available")
class CompatibilityTest(unittest.TestCase):
    def setUp(self):
        self.view = _make_view()
        self.tmp = tempfile.mkdtemp()
        self.pdf = _make_pdf(self.tmp)
        self.img = os.path.join(self.tmp, "img.png")
        with open(self.img, "w") as fh:
            fh.write("x")

    def tearDown(self):
        self.view.destroy()

    def test_merge_needs_two(self):
        self.assertFalse(self.view._compatible("merge", [self.pdf]))
        self.assertTrue(self.view._compatible("merge", [self.pdf, _make_pdf(self.tmp, "g.pdf")]))

    def test_single_file_pdf_tool(self):
        self.assertTrue(self.view._compatible("split", [self.pdf]))
        self.assertFalse(self.view._compatible("split", [self.pdf, _make_pdf(self.tmp, "g.pdf")]))

    def test_pdf_tool_rejects_non_pdf(self):
        self.assertFalse(self.view._compatible("compress", [self.img]))

    def test_from_images_accepts_images(self):
        self.assertTrue(self.view._compatible("from-images", [self.img]))

    def test_from_images_rejects_pdf(self):
        self.assertFalse(self.view._compatible("from-images", [self.pdf]))

    def test_empty_is_compatible(self):
        self.assertTrue(self.view._compatible("split", []))


@unittest.skipUnless(_HAS_DISPLAY, "no display available")
class ToolChangeTest(unittest.TestCase):
    def setUp(self):
        self.view = _make_view()
        self.tmp = tempfile.mkdtemp()
        self.pdf = _make_pdf(self.tmp)

    def tearDown(self):
        self.view.destroy()

    def _add(self, paths):
        self.view.files = list(paths)
        for p in paths:
            self.view.file_list.insert(tk.END, os.path.basename(p))

    def test_default_clears_always(self):
        self._add([self.pdf])
        self.view.tool.set("Split PDF")
        self.view._on_tool_changed()
        self.assertEqual(self.view.files, [])

    def test_smart_keeps_compatible(self):
        self.view.clear_on_switch.set(False)
        self._add([self.pdf])
        self.view.tool.set("Split PDF")
        self.view._on_tool_changed()
        self.assertEqual(self.view.files, [self.pdf])

    def test_smart_clears_incompatible(self):
        self.view.clear_on_switch.set(False)
        self._add([self.pdf, _make_pdf(self.tmp, "g.pdf")])
        self.view.tool.set("Split PDF")
        self.view._on_tool_changed()
        self.assertEqual(self.view.files, [])

    def test_smart_clears_for_images_to_pdf(self):
        self.view.clear_on_switch.set(False)
        self._add([self.pdf])
        self.view.tool.set("Images to PDF")
        self.view._on_tool_changed()
        self.assertEqual(self.view.files, [])

    def test_incompat_messages(self):
        self.assertIn("not a PDF", self.view._incompat_message("split", [os.path.join(self.tmp, "i.png")]))
        two = [self.pdf, _make_pdf(self.tmp, "g.pdf")]
        self.assertEqual(self.view._incompat_message("split", two), "Split PDF works on a single file.")
        self.assertEqual(self.view._incompat_message("merge", [self.pdf]), "Merge needs at least two PDFs.")
        self.assertIn("takes images", self.view._incompat_message("from-images", [self.pdf]))


if __name__ == "__main__":
    unittest.main()