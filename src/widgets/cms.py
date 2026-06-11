"""Offline-first CMS pipeline (ME-08).

Render order guarantees no startup wait and no crash offline:
1. serve cached feed immediately (or the bundled default, or an empty feed);
2. refresh in a background thread with a short timeout;
3. on success, atomically replace the cache and emit ``content_updated``;
4. on any failure, log and keep serving the cache.

The endpoint is configurable (settings.json ``cms_endpoint``) and may be an
http(s) URL or a local file path / file:// URL.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from core import store
from core.qt_compat import QtCore

log = logging.getLogger("jiopc.cms")

CACHE_NAME = "feed.json"
_BUNDLED_DEFAULT = Path(__file__).with_name("default_feed.json")
_TIMEOUT = 5
_SECTIONS = ("carousel", "news", "tiles")


def empty_feed() -> dict[str, Any]:
    return {"version": 1, "fetched_hint_minutes": 0,
            "carousel": [], "news": [], "tiles": []}


def _valid(data: Any) -> bool:
    return isinstance(data, dict) and all(k in data for k in _SECTIONS)


def load_cache(cache_path: Path) -> dict[str, Any] | None:
    data = store.read_json(cache_path, default=None)
    return data if _valid(data) else None


def bundled_default() -> dict[str, Any]:
    data = store.read_json(_BUNDLED_DEFAULT, default=None)
    return data if _valid(data) else empty_feed()


def initial_content(cache_path: Path) -> dict[str, Any]:
    """Best content available without the network: cache > bundled > empty."""
    return load_cache(cache_path) or bundled_default()


def fetch(endpoint: str, timeout: int = _TIMEOUT) -> dict[str, Any]:
    """Fetch+parse a feed from http(s) or a local file. Raises on failure."""
    scheme = urlparse(endpoint).scheme
    if scheme in ("http", "https"):
        resp = requests.get(endpoint, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    else:
        path = endpoint[len("file://"):] if scheme == "file" else endpoint
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    if not _valid(data):
        raise ValueError("feed missing required sections")
    return data


class _FetchWorker(QtCore.QThread):
    done = QtCore.pyqtSignal(dict)
    failed = QtCore.pyqtSignal(str)

    def __init__(self, endpoint: str, parent=None) -> None:
        super().__init__(parent)
        self._endpoint = endpoint

    def run(self) -> None:
        try:
            self.done.emit(fetch(self._endpoint))
        except Exception as exc:  # network/parse: degrade gracefully
            self.failed.emit(str(exc))


class CmsService(QtCore.QObject):
    """Serves cached content immediately and refreshes in the background."""

    content_updated = QtCore.pyqtSignal(dict)

    def __init__(self, endpoint: str, cache_path: Path,
                 parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._endpoint = endpoint
        self._cache_path = Path(cache_path)
        self._content = initial_content(self._cache_path)
        self._worker: _FetchWorker | None = None

    def content(self) -> dict[str, Any]:
        return self._content

    def refresh(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        self._worker = _FetchWorker(self._endpoint, self)
        self._worker.done.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_done(self, data: dict) -> None:
        store.write_json(self._cache_path, data)  # atomic
        self._content = data
        self.content_updated.emit(data)

    def _on_failed(self, msg: str) -> None:
        log.warning("CMS refresh failed, serving cache: %s", msg)
