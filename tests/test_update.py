import pytest

from conveyr.update import (
    UpdateError,
    _tokens,
    available_version,
    latest_tag,
    remote_is_newer,
)


def _conn(location, status=302):
    """Stand-in for an HTTPSConnection answering one redirect."""
    class Response:
        def getheader(self, name):
            return location

    class Conn:
        def __init__(self, *a, **k):
            pass

        def request(self, *a, **k):
            pass

        def getresponse(self):
            return Response()

        def close(self):
            pass

    return Conn


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
    def test_network_failure_raises_with_the_cause(self, monkeypatch):
        """A broken TLS bundle must not look like 'no release published'.

        ssl.SSLError is an OSError subclass, so swallowing it here is how a
        certifi-less AppImage used to report a healthy app as offline.
        """
        def boom(*a, **k):
            raise OSError("certificate verify failed")

        monkeypatch.setattr("conveyr.update.http.client.HTTPSConnection", boom)
        with pytest.raises(UpdateError) as exc:
            latest_tag()
        assert "OSError" in str(exc.value)

    def test_available_version_stays_silent(self, monkeypatch):
        def boom(*a, **k):
            raise OSError("offline")

        monkeypatch.setattr("conveyr.update.http.client.HTTPSConnection", boom)
        assert available_version("1.0.0") is None

    @pytest.mark.parametrize(
        "location,expected",
        [
            (None, ""),
            ("https://github.com/padelle2603/conveyr/releases", ""),
            ("https://github.com/padelle2603/conveyr/releases/latest", ""),
            ("https://github.com/padelle2603/conveyr/releases/tag/v1.4.2", "1.4.2"),
        ],
    )
    def test_tag_extraction(self, monkeypatch, location, expected):
        monkeypatch.setattr(
            "conveyr.update.http.client.HTTPSConnection", _conn(location)
        )
        assert latest_tag() == expected

    def test_offered_only_when_newer(self, monkeypatch):
        monkeypatch.setattr(
            "conveyr.update.http.client.HTTPSConnection",
            _conn("https://github.com/padelle2603/conveyr/releases/tag/v1.4.2"),
        )
        assert available_version("1.0.0") == "1.4.2"
        assert available_version("99.0.0") is None