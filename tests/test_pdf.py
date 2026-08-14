"""Tests for the Conveyr PDF tools.

Run with:  PYTHONPATH=src python3 -m unittest tests.test_pdf -v
Requires ImageMagick to build the fixtures plus poppler-utils, ghostscript
and qpdf for the individual operations.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from conveyr.pdf import (
    compress,
    from_images,
    is_pdf,
    merge,
    protect,
    rotate,
    run_tool,
    split,
    to_images,
    to_text,
    unlock,
)

MAGICK = shutil.which("magick") or shutil.which("convert")
PDFINFO = shutil.which("pdfinfo")
QPDF = shutil.which("qpdf")
GS = shutil.which("gs")


def _run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _pages(path) -> int:
    for line in subprocess.run(
        ["pdfinfo", str(path)], capture_output=True, text=True
    ).stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":", 1)[1].strip())
    return -1


def _make_pdf(path: Path, color: str) -> None:
    _run([MAGICK, "-size", "120x90", f"xc:{color}", str(path)])


@unittest.skipUnless(MAGICK and PDFINFO, "magick/pdfinfo required")
class PdfToolsTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = Path(tempfile.mkdtemp(prefix="fpdf-test-"))
        cls.a = cls.dir / "a.pdf"
        cls.b = cls.dir / "b.pdf"
        _make_pdf(cls.a, "red")
        _make_pdf(cls.b, "blue")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)

    def _tmp(self, name: str) -> str:
        return str(self.dir / name)

    # ------------------------------------------------------------ basics -----
    def test_is_pdf(self):
        self.assertTrue(is_pdf(self.a))
        txt = self.dir / "note.txt"
        txt.write_text("hello")
        self.assertFalse(is_pdf(txt))

    def test_merge(self):
        out = merge([str(self.a), str(self.b)], out=self._tmp("m.pdf"))
        self.assertEqual(_pages(out), 2)

    @unittest.skipUnless(QPDF, "qpdf required")
    def test_merge_unordered_src_validation(self):
        with self.assertRaises(ValueError):
            merge([self._tmp("note.txt")])

    def test_no_overwrite_without_force(self):
        out = self._tmp("no_force.pdf")
        merge([str(self.a), str(self.b)], out=out)
        with self.assertRaises(FileExistsError):
            merge([str(self.a), str(self.b)], out=out)

    # ------------------------------------------------------------ split ------
    @unittest.skipUnless(GS, "ghostscript required to build a 2-page fixture")
    def test_split(self):
        merged = merge([str(self.a), str(self.b)], out=self._tmp("sp.pdf"))
        pages = split(merged, out_dir=str(self.dir / "sp_out"))
        self.assertEqual(len(pages), 2)
        for p in pages:
            self.assertTrue(is_pdf(p))

    # ---------------------------------------------------------- compress -----
    @unittest.skipUnless(GS, "ghostscript required")
    def test_compress(self):
        out = compress(str(self.a), out=self._tmp("c.pdf"), opts={"preset": "screen"})
        self.assertTrue(is_pdf(out))

    @unittest.skipUnless(GS, "ghostscript required")
    def test_compress_bad_preset(self):
        with self.assertRaises(ValueError):
            compress(str(self.a), out=self._tmp("c2.pdf"), opts={"preset": "huge"})

    # ----------------------------------------------------------- rotate ------
    @unittest.skipUnless(QPDF, "qpdf required")
    def test_rotate(self):
        out = rotate(str(self.a), out=self._tmp("r.pdf"), opts={"angle": "90"})
        self.assertTrue(is_pdf(out))

    @unittest.skipUnless(QPDF, "qpdf required")
    def test_rotate_bad_angle(self):
        with self.assertRaises(ValueError):
            rotate(str(self.a), out=self._tmp("r2.pdf"), opts={"angle": "45"})

    # ----------------------------------------------------- protect/unlock -----
    @unittest.skipUnless(QPDF, "qpdf required")
    def test_protect_unlock_roundtrip(self):
        protected = protect(
            str(self.a), out=self._tmp("p.pdf"), opts={"password": "secret"}
        )
        self.assertTrue(is_pdf(protected))
        unlocked = unlock(
            protected, out=self._tmp("u.pdf"), opts={"password": "secret"}
        )
        self.assertTrue(is_pdf(unlocked))

    @unittest.skipUnless(QPDF, "qpdf required")
    def test_protect_requires_password(self):
        with self.assertRaises(ValueError):
            protect(str(self.a), out=self._tmp("p2.pdf"), opts={"password": ""})

    # ------------------------------------------------------------ images -----
    def test_to_images(self):
        images = to_images(
            merge([str(self.a), str(self.b)], out=self._tmp("ti.pdf")),
            out_dir=str(self.dir / "ti_out"),
            opts={"format": "png", "dpi": 72},
        )
        self.assertEqual(len(images), 2)
        self.assertTrue(all(Path(p).suffix == ".png" for p in images))

    def test_to_images_bad_format(self):
        with self.assertRaises(ValueError):
            to_images(str(self.a), out_dir=str(self.dir), opts={"format": "gif"})

    def test_from_images(self):
        images = to_images(
            str(self.a), out_dir=str(self.dir / "fi_src"), opts={"format": "jpg", "dpi": 72}
        )
        out = from_images(images, out=self._tmp("fi.pdf"))
        self.assertTrue(is_pdf(out))

    # ------------------------------------------------------------ text -------
    def test_to_text(self):
        out = to_text(str(self.a), out=self._tmp("t.txt"))
        self.assertTrue(Path(out).is_file())

    # ----------------------------------------------------------- dispatch ----
    def test_run_tool_unknown(self):
        with self.assertRaises(ValueError):
            run_tool("nope", [str(self.a)], None, None, {})


if __name__ == "__main__":
    unittest.main()
