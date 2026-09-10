import pytest
from conveyr.backends import BackendError, install_hint
from conveyr.core import RASTER, VECTOR, VIDEO, AUDIO, ALL, ALIASES, CATEGORY, canonical
from conveyr.video import is_video, ROTATE_ANGLES
from conveyr.pdf import is_pdf, COMPRESS_PRESETS, IMAGE_FORMATS
from pathlib import Path
import tempfile


class TestBackendError:
    def test_message(self):
        err = BackendError("test error")
        assert str(err) == "test error"

    def test_stderr(self):
        err = BackendError("error", stderr="details")
        assert err.stderr == "details"

    def test_install_hint(self):
        hint = install_hint()
        assert isinstance(hint, str)
        assert len(hint) > 0


class TestCoreConstants:
    def test_raster_formats(self):
        assert "jpg" in RASTER
        assert "png" in RASTER
        assert "webp" in RASTER

    def test_video_formats(self):
        assert "mp4" in VIDEO
        assert "mkv" in VIDEO

    def test_audio_formats(self):
        assert "mp3" in AUDIO
        assert "wav" in AUDIO
        assert "flac" in AUDIO

    def test_vector_formats(self):
        assert "svg" in VECTOR

    def test_all_includes_everything(self):
        assert RASTER <= ALL
        assert VIDEO <= ALL
        assert AUDIO <= ALL
        assert VECTOR <= ALL

    def test_aliases(self):
        assert canonical("jpeg") == "jpg"
        assert canonical("mpeg") == "mpg"
        assert canonical("m4v") == "mp4"

    def test_canonical_passthrough(self):
        assert canonical("png") == "png"

    def test_category_mapping(self):
        assert CATEGORY["jpg"] == "image"
        assert CATEGORY["svg"] == "vector"
        assert CATEGORY["mp4"] == "video"
        assert CATEGORY["mp3"] == "audio"
        assert CATEGORY["gif"] == "gif"


class TestVideoModule:
    def test_is_video_mp4(self, tmp_path):
        f = tmp_path / "test.mp4"
        f.write_bytes(b"\x00" * 100)
        assert is_video(f) is True

    def test_is_video_txt(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        assert is_video(f) is False

    def test_rotate_angles(self):
        assert "90" in ROTATE_ANGLES
        assert "180" in ROTATE_ANGLES
        assert "270" in ROTATE_ANGLES


class TestPdfModule:
    def test_is_pdf_magic_bytes(self, tmp_path):
        f = tmp_path / "test.pdf"
        f.write_bytes(b"%PDF-1.4 fake content")
        assert is_pdf(f) is True

    def test_is_pdf_not_pdf(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("not a pdf")
        assert is_pdf(f) is False

    def test_compress_presets(self):
        assert "screen" in COMPRESS_PRESETS
        assert "ebook" in COMPRESS_PRESETS
        assert "printer" in COMPRESS_PRESETS

    def test_image_formats(self):
        assert "png" in IMAGE_FORMATS
        assert "jpg" in IMAGE_FORMATS
