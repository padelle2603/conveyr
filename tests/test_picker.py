"""Tests for the native file picker wrapper."""

from __future__ import annotations

import unittest
from unittest import mock

from conveyr import picker


class PickerCommandTest(unittest.TestCase):
    def test_kdialog_files_single(self):
        self.assertEqual(
            picker._build_files_cmd("kdialog", "T", False),
            ["kdialog", "--title", "T", "--getopenfilename"],
        )

    def test_kdialog_files_multiple(self):
        self.assertEqual(
            picker._build_files_cmd("kdialog", "T", True),
            ["kdialog", "--title", "T", "--getopenfilename", "--multiple"],
        )

    def test_zenity_files(self):
        self.assertEqual(
            picker._build_files_cmd("zenity", "T", False),
            ["zenity", "--file-selection", "--title", "T"],
        )

    def test_zenity_files_multiple_uses_newline_separator(self):
        cmd = picker._build_files_cmd("zenity", "T", True)
        self.assertIn("--multiple", cmd)
        self.assertIn("--separator=\n", cmd)

    def test_kdialog_directory(self):
        self.assertEqual(
            picker._build_dir_cmd("kdialog", "T"),
            ["kdialog", "--title", "T", "--getexistingdirectory"],
        )

    def test_zenity_directory(self):
        self.assertEqual(
            picker._build_dir_cmd("zenity", "T"),
            ["zenity", "--file-selection", "--directory", "--title", "T"],
        )


class PickerBehaviorTest(unittest.TestCase):
    @mock.patch.object(picker, "native_picker", return_value=None)
    def test_pick_files_returns_none_when_no_native_picker(self, _np):
        self.assertIsNone(picker.pick_files("T", multiple=True))

    @mock.patch.object(picker, "native_picker", return_value="kdialog")
    @mock.patch.object(picker, "_run", return_value="")
    def test_pick_files_cancel_returns_empty(self, _run, _np):
        self.assertEqual(picker.pick_files("T"), [])

    @mock.patch.object(picker, "native_picker", return_value="kdialog")
    @mock.patch.object(picker, "_run", return_value="/a/one.png\n/a/two.png")
    def test_pick_files_parses_lines(self, _run, _np):
        self.assertEqual(picker.pick_files("T", multiple=True), ["/a/one.png", "/a/two.png"])

    @mock.patch.object(picker, "native_picker", return_value=None)
    def test_pick_directory_returns_none_without_picker(self, _np):
        self.assertIsNone(picker.pick_directory("T"))

    @mock.patch.object(picker, "native_picker", return_value="zenity")
    @mock.patch.object(picker, "_run", return_value="/a/dir")
    def test_pick_directory_returns_path(self, _run, _np):
        self.assertEqual(picker.pick_directory("T"), "/a/dir")


if __name__ == "__main__":
    unittest.main()