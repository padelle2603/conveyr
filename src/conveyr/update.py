"""Is there a newer Conveyr? — one anonymous HEAD request at startup.

Privacy: this is the only network call Conveyr's desktop app makes, ever. It
hits ``github.com/<repo>/releases/latest``, which answers ``302`` with the tag
in the ``Location`` header and an empty body. No GitHub API (no token, no JSON,
no rate-limit budget shared with other apps), no cookies, no redirect
following, nothing written to disk, nothing sent back. The User-Agent is the
bare project name: no version, no distro, no hostname.

``http.client`` is used directly rather than ``urllib.request`` on purpose:
``urlopen`` brings an opener with cookie handling, proxy discovery and an
automatic redirect chain, and every one of those is state we do not want.

Every failure — offline, DNS, TLS, HTTP error — returns ``None`` by design. A
user with no network must not see an error about an optional feature.
"""

from __future__ import annotations

import http.client
import re

LATEST_URL = "/padelle2603/conveyr/releases/latest"
HOST = "github.com"
RELEASES_URL = "https://github.com/padelle2603/conveyr/releases"

TIMEOUT = 5


def latest_tag(timeout: int = TIMEOUT) -> str | None:
    """Tag of the newest published release, or ``None`` if there is none.

    A repository with zero releases answers ``302 -> /releases`` with no tag in
    the path. That is not an error, it just means there is nothing to offer.
    """
    try:
        conn = http.client.HTTPSConnection(HOST, timeout=timeout)
        try:
            conn.request("HEAD", LATEST_URL, headers={"User-Agent": "conveyr"})
            response = conn.getresponse()
            location = response.getheader("location")
        finally:
            conn.close()
    except (OSError, http.client.HTTPException):
        return None

    if not location:
        return None
    tag = location.rsplit("/", 1)[-1].strip()
    if not tag or tag in ("releases", "latest"):
        return None
    return tag.lstrip("vV")


def _tokens(version: str) -> list[str]:
    return re.split(r"[._\-+]+", (version or "").strip().lstrip("vV").lower())


def remote_is_newer(local: str, remote: str) -> bool:
    """True when ``remote`` is strictly newer than ``local``.

    ponytail: length-first token compare, not a full semver implementation.
    ``1.0.0`` loses to ``1.0.1``; a dev build ahead of the newest release
    (``1.1.0`` vs ``1.0.0``) reports no update. Swap in ``packaging`` if
    pre-release ordering ever matters.
    """
    a, b = _tokens(local), _tokens(remote)
    for x, y in zip(a, b):
        nx, ny = x.isdigit(), y.isdigit()
        if nx and ny:
            if int(x) != int(y):
                return int(y) > int(x)
        elif nx != ny:
            return ny
        elif x != y:
            return y > x
    return len(b) > len(a)


def available_version(current: str, timeout: int = TIMEOUT) -> str | None:
    """The version to offer, or ``None``. One request."""
    remote = latest_tag(timeout)
    return remote if remote and remote_is_newer(current, remote) else None