"""Round-trip tests for the Conveyr core.

Run with:  PYTHONPATH=src python3 -m unittest tests.test_core -v
Requires ffmpeg, ImageMagick and potrace on PATH.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from conveyr.core import convert, detect, valid_targets

MAGICK = shutil.which("magick") or shutil.which("convert")
FFMPEG = shutil.which("ffmpeg")
POTRACE = shutil.which("potrace")


def _magic(path) -> bytes:
    with open(path, "rb") as fh:
        return fh.read(4096)


def _assert_magic(test, path, prefix):
    data = _magic(path)
    test.assertTrue(prefix in data, f"{path} does not contain {prefix!r}: {data[:24]!r}")


def _run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


@unittest.skipUnless(FFMPEG and MAGICK and POTRACE, "ffmpeg/magick/potrace required")
class ConverterTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = Path(tempfile.mkdtemp(prefix="fconv-test-"))
        cls.jpg = cls.dir / "photo.jpg"
        _run([MAGICK, "-size", "96x64", "gradient:red-blue", str(cls.jpg)])
        cls.png = cls.dir / "logo.png"
        _run([MAGICK, "-size", "80x48", "plasma:fractal", str(cls.png)])
        cls.gif = cls.dir / "anim.gif"
        _run(
            [
                MAGICK, "-delay", "10",
                "-size", "64x48", "xc:red",
                "-size", "64x48", "xc:blue",
                str(cls.gif),
            ]
        )
        cls.wav = cls.dir / "tone.wav"
        _run(
            [FFMPEG, "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=0.3",
             "-c:a", "pcm_s16le", str(cls.wav)]
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)

    # ------------------------------------------------------------ detection --
    def test_detect(self):
        cases = {
            self.jpg: "jpg",
            self.png: "png",
            self.gif: "gif",
            self.wav: "wav",
        }
        for path, expected in cases.items():
            self.assertEqual(detect(path), expected, path.name)

    def test_detect_svg_file(self):
        svg = self.dir / "shape.svg"
        svg.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="50" height="50">'
            '<rect width="50" height="50" fill="black"/></svg>'
        )
        self.assertEqual(detect(svg), "svg")

    def test_detect_wrong_extension(self):
        fake = self.dir / "sneaky.txt"
        shutil.copy(self.png, fake)
        self.assertEqual(detect(fake), "png")

    # ---------------------------------------------------------- valid_targets --
    def test_valid_targets_sanity(self):
        self.assertNotIn("png", valid_targets("png"))
        self.assertIn("svg", valid_targets("png"))
        self.assertIn("png", valid_targets("svg"))
        self.assertIn("mp4", valid_targets("gif"))
        self.assertIn("gif", valid_targets("mp4"))
        self.assertIn("mp3", valid_targets("wav"))
        self.assertIn("wav", valid_targets("mp3"))
        self.assertNotIn("mp4", valid_targets("wav"))

    # ------------------------------------------------------------- images ----
    def test_jpg_to_png(self):
        out = convert(str(self.jpg), "jpg", "png", {"output": str(self.dir / "jpg_to_png.png")})
        _assert_magic(self, out, b"\x89PNG")

    def test_png_to_jpg(self):
        out = convert(str(self.png), "png", "jpg", {"output": str(self.dir / "png_to_jpg.jpg")})
        _assert_magic(self, out, b"\xff\xd8\xff")

    def test_png_to_svg_to_png(self):
        svg_out = convert(str(self.png), "png", "svg", {"output": str(self.dir / "logo_traced.svg")})
        _assert_magic(self, svg_out, b"<svg")
        png_out = convert(svg_out, "svg", "png", {"output": str(self.dir / "logo_rendered.png")})
        _assert_magic(self, png_out, b"\x89PNG")

    def test_gif_first_frame_to_png(self):
        out = convert(str(self.gif), "gif", "png", {"output": str(self.dir / "gif_frame.png")})
        _assert_magic(self, out, b"\x89PNG")

    # ------------------------------------------------------------- video -----
    @unittest.skipUnless(FFMPEG, "ffmpeg required")
    def test_gif_to_mp4(self):
        out = convert(str(self.gif), "gif", "mp4", {"output": str(self.dir / "gif_to_mp4.mp4")})
        _assert_magic(self, out, b"ftyp")

    @unittest.skipUnless(FFMPEG, "ffmpeg required")
    def test_mp4_to_gif(self):
        mp4 = self.dir / "sample.mp4"
        _run(
            [FFMPEG, "-y", "-f", "lavfi", "-i", "testsrc=duration=1:size=64x48:rate=10",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", str(mp4)]
        )
        out = convert(str(mp4), "mp4", "gif", {"output": str(self.dir / "mp4_to_gif.gif"), "fps": 10, "width": 64})
        _assert_magic(self, out, b"GIF8")

    @unittest.skipUnless(FFMPEG, "ffmpeg required")
    def test_mp4_to_webm(self):
        mp4 = self.dir / "sample2.mp4"
        _run(
            [FFMPEG, "-y", "-f", "lavfi", "-i", "testsrc=duration=1:size=64x48:rate=10",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", str(mp4)]
        )
        out = convert(str(mp4), "mp4", "webm", {"output": str(self.dir / "mp4_to_webm.webm")})
        _assert_magic(self, out, b"\x1aE\xdf\xa3")

    # ------------------------------------------------------------- audio -----
    @unittest.skipUnless(FFMPEG, "ffmpeg required")
    def test_wav_to_mp3(self):
        out = convert(str(self.wav), "wav", "mp3", {"output": str(self.dir / "wav_to_mp3.mp3")})
        _assert_magic(self, out, b"ID3")

    @unittest.skipUnless(FFMPEG, "ffmpeg required")
    def test_mp3_to_wav(self):
        mp3 = self.dir / "sample.mp3"
        _run(
            [FFMPEG, "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=0.3",
             "-c:a", "libmp3lame", str(mp3)]
        )
        out = convert(str(mp3), "mp3", "wav", {"output": str(self.dir / "mp3_to_wav.wav")})
        _assert_magic(self, out, b"RIFF")

    @unittest.skipUnless(FFMPEG, "ffmpeg required")
    def test_wav_to_flac(self):
        out = convert(str(self.wav), "wav", "flac", {"output": str(self.dir / "wav_to_flac.flac")})
        _assert_magic(self, out, b"fLaC")

    # ------------------------------------------------------------- safety ----
    def test_no_overwrite_without_force(self):
        target = str(self.dir / "no_force.png")
        convert(str(self.jpg), "jpg", "png", {"output": target})
        with self.assertRaises(FileExistsError):
            convert(str(self.jpg), "jpg", "png", {"output": target})

    def test_force_overwrites(self):
        target = str(self.dir / "force.png")
        convert(str(self.jpg), "jpg", "png", {"output": target, "force": True})
        convert(str(self.jpg), "jpg", "png", {"output": target, "force": True})


if __name__ == "__main__":
    unittest.main()