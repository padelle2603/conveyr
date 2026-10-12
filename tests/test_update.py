import pytest

from conveyr import __version__
from conveyr.update import (
    _tokens,
    available_version,
    latest_tag,
    remote_is_newer,
)


class TestTokens:
    def test_strips_v_prefix(self):
        assert _tokens("v1.0.0") == ["1", "0", "0"]
        assert _tokens("1.0.0") == ["1", "0", "0"]

    def test_splits_all_separators(self):
        assert _tokens("1.2.3-rc1") == ["1", "2", "3", "rc1"]


class TestRemoteIsNewer:
    @pytest.mark.parametrize(
        "local,remote",
        [("1.0.0", "1.0.1"), ("1.0.9", "1.1.0"), ("1.0.0", "2.0.0"), ("v1.0.0", "v1.0.1")],
    )
    def test_newer_remote_wins(self, local, remote):
        assert remote_is_newer(local, remote)

    @pytest.mark.parametrize(
        "local,remote", [("1.0.1", "1.0.1"), ("1.1.0", "1.0.0"), ("2.0.0", "1.9.9")]
    )
    def test_current_and_ahead_report_nothing(self, local, remote):
        assert not remote_is_newer(local, remote)

    def test_longer_version_is_newer(self):
        assert remote_is_newer("1.0", "1.0.1")
        assert not remote_is_newer("1.0.1", "1.0")


class TestLatestTag:
    def test_network_failure_is_silent(self, monkeypatch):
        def boom(*a, **k):
            raise OSError("offline")

        monkeypatch.setattr("conveyr.update.http.client.HTTPSConnection", boom)
        assert latest_tag() is None
        assert available_version("1.0.0") is None

    def test_no_release_returns_none(self, monkeypatch):
        class Response:
            status = 302

            def getheader(self, name):
                return "https://github.com/padelle2603/conveyr/releases"

        class Conn:
            def __init__(self, *a, **k):
                pass

            def request(self, *a, **k):
                pass

            def getresponse(self):
                return Response()

            def close(self):
                pass

        monkeypatch.setattr("conveyr.update.http.client.HTTPSConnection", Conn)
        assert latest_tag() is None

    def test_tag_is_extracted_and_stripped(self, monkeypatch):
        class Response:
            def getheader(self, name):
                return "https://github.com/padelle2603/conveyr/releases/tag/v1.4.2"

        class Conn:
            def __init__(self, *a, **k):
                pass

            def request(self, *a, **k):
                pass

            def getresponse(self):
                return Response()

            def close(self):
                pass

        monkeypatch.setattr("conveyr.update.http.client.HTTPSConnection", Conn)
        assert latest_tag() == "1.4.2"
        assert available_version(__version__) == "1.4.2"
        assert available_version("99.0.0") is None