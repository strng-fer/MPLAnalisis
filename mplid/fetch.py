"""Download helper with a local HTML cache.

The site is server rendered: every page ships the full markup, so plain HTTP
is enough. The headless browser (obscura) is only used as a fallback when the
HTTP response looks like a challenge page or is missing the expected payload.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

import requests

BASE_URL = "https://id-mpl.com"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36 mplid-dataset/2.0"
)


class FetchError(RuntimeError):
    pass


class Fetcher:
    def __init__(
        self,
        cache_dir: Path,
        *,
        delay: float = 0.4,
        max_age: int = 6 * 3600,
        refresh: bool = False,
        obscura: str | None = None,
        timeout: int = 45,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.delay = delay
        self.max_age = max_age
        self.refresh = refresh
        self.obscura = obscura
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "id,en"})
        self.stats = {"http": 0, "cache": 0, "obscura": 0, "bytes": 0}

    # -- cache plumbing -------------------------------------------------
    def _path(self, url: str) -> Path:
        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
        slug = re.sub(r"[^a-z0-9]+", "-", url.replace(BASE_URL, "").lower()).strip("-")
        return self.cache_dir / f"{slug[:60]}-{digest}.html"

    def _read_cache(self, path: Path, max_age: int) -> str | None:
        if self.refresh or not path.exists():
            return None
        age = time.time() - path.stat().st_mtime
        if age > max_age:
            return None
        self.stats["cache"] += 1
        return path.read_text(encoding="utf-8", errors="replace")

    # -- public ---------------------------------------------------------
    def get(self, url: str, *, max_age: int | None = None, expect: str | None = None) -> str:
        """Return page HTML, using the cache when fresh.

        ``expect`` is a substring that must be present; when it is missing the
        response is treated as a JS shell and the browser fallback is tried.
        """
        path = self._path(url)
        cached = self._read_cache(path, self.max_age if max_age is None else max_age)
        if cached is not None and (expect is None or expect in cached):
            return cached

        last_error: Exception | None = None
        for attempt in range(3):
            try:
                resp = self.session.get(url, timeout=self.timeout)
                if resp.status_code in (403, 429, 503):
                    raise FetchError(f"HTTP {resp.status_code}")
                resp.raise_for_status()
                html = resp.text
                if expect is not None and expect not in html:
                    raise FetchError(f"payload marker {expect!r} missing")
                path.write_text(html, encoding="utf-8")
                self.stats["http"] += 1
                self.stats["bytes"] += len(html)
                time.sleep(self.delay)
                return html
            except Exception as exc:  # noqa: BLE001 - retried below
                last_error = exc
                time.sleep(1.5 * (attempt + 1))

        if self.obscura and Path(self.obscura).exists():
            html = self._fetch_obscura(url)
            if html:
                path.write_text(html, encoding="utf-8")
                self.stats["obscura"] += 1
                return html
        raise FetchError(f"{url}: {last_error}")

    def _fetch_obscura(self, url: str) -> str | None:
        js = "document.documentElement.outerHTML"
        cmd = [
            self.obscura,
            "fetch",
            url,
            "--wait-until",
            "networkidle0",
            "--wait",
            "3",
            "--eval",
            js,
            "--quiet",
        ]
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            return None
        if out.returncode != 0:
            return None
        text = out.stdout.strip()
        if text.startswith('"'):
            try:
                text = json.loads(text)
            except json.JSONDecodeError:
                pass
        return text or None

    def cached(self, url: str) -> str | None:
        path = self._path(url)
        if path.exists():
            return path.read_text(encoding="utf-8", errors="replace")
        return None


def default_obscura() -> str | None:
    env = os.environ.get("OBSCURA_BIN")
    if env and Path(env).exists():
        return env
    guess = Path(
        os.environ.get("TEMP", ""),
        "opencode",
        "obscura",
        "target",
        "release",
        "obscura.exe",
    )
    return str(guess) if guess.exists() else None
