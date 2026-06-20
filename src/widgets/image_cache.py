"""RAM-safe image cache for hero carousel images.

Download pipeline (CLAUDE.md constraints strictly observed):

1. Download  — QNetworkAccessManager fetches the URL asynchronously on the
               Qt network thread.  The raw bytes are written straight to a
               local file (``~/.cache/jiopc/home/<sha256_hex[:16]>.img``);
               the QByteArray is released immediately so it never inflates
               the Python heap.

2. Scale     — QImageReader reads the on-disk file and calls setScaledSize()
               BEFORE allocating the decoded image.  This means only the
               *target* rectangle (the QLabel size) is ever in RAM, not the
               full source resolution.

3. Deliver   — The scaled QPixmap is emitted via a Qt signal so the UI thread
               can apply it.  The per-item cache means repeated show()s cost
               nothing (disk already hit, QPixmap already built).

Thread safety: network reply is received on the Qt main thread (single-
threaded Qt network stack).  QImageReader.read() is called there too; it is
fast because the image has already been pre-scaled.
"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from PyQt5 import QtNetwork

from core.paths import CACHE_DIR
from core.qt_compat import Qt, QtCore, QtGui

log = logging.getLogger("jiopc.image_cache")

_IMAGE_CACHE_DIR = CACHE_DIR / "images"


def _cache_path(url: str) -> Path:
    """Deterministic file path for a given URL (no collision by construction)."""
    digest = hashlib.sha256(url.encode()).hexdigest()[:24]
    return _IMAGE_CACHE_DIR / f"{digest}.img"


class ImageRequest(QtCore.QObject):
    """Fetches one image URL and delivers a scaled QPixmap.

    Signals
    -------
    ready(url, pixmap)  -- emitted on the main thread when the pixmap is ready
    failed(url, reason) -- emitted when download or decode fails
    """

    ready = QtCore.pyqtSignal(str, QtGui.QPixmap)
    failed = QtCore.pyqtSignal(str, str)

    def __init__(
        self,
        url: str,
        target_size: QtCore.QSize,
        nam: "QtNetwork.QNetworkAccessManager",
        parent: QtCore.QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._url = url
        self._target_size = target_size
        self._nam = nam
        self._reply: "QtNetwork.QNetworkReply | None" = None

    def start(self) -> None:
        """Kick off the download or serve from disk cache immediately."""
        path = _cache_path(self._url)
        if path.exists():
            log.debug("image cache hit: %s", self._url)
            self._deliver_from_disk(path)
            return

        log.debug("image cache miss, downloading: %s", self._url)
        req = QtNetwork.QNetworkRequest(QtCore.QUrl(self._url))
        req.setAttribute(
            QtNetwork.QNetworkRequest.FollowRedirectsAttribute, True  # type: ignore[attr-defined]
        )
        self._reply = self._nam.get(req)
        self._reply.finished.connect(self._on_finished)

    def _on_finished(self) -> None:
        reply = self._reply
        if reply is None:
            return

        error = reply.error()
        if error != QtNetwork.QNetworkReply.NoError:  # type: ignore[attr-defined]
            reason = reply.errorString()
            reply.deleteLater()
            self._reply = None
            log.warning("image download failed (%s): %s", reason, self._url)
            self.failed.emit(self._url, reason)
            return

        # Write bytes to disk immediately; release the QByteArray.
        path = _cache_path(self._url)
        _IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        try:
            tmp.write_bytes(bytes(reply.readAll()))  # copy to disk
            tmp.replace(path)                        # atomic rename
        except OSError as exc:
            log.warning("image cache write failed: %s", exc)
            reply.deleteLater()
            self._reply = None
            self.failed.emit(self._url, str(exc))
            return
        finally:
            reply.deleteLater()
            self._reply = None

        self._deliver_from_disk(path)

    def _deliver_from_disk(self, path: Path) -> None:
        """Read + pre-scale via QImageReader (never loads full resolution)."""
        reader = QtGui.QImageReader(str(path))
        reader.setAutoTransform(True)

        # Only scale down if the source is larger than the target.
        src_size = reader.size()
        if src_size.isValid() and (
            src_size.width() > self._target_size.width()
            or src_size.height() > self._target_size.height()
        ):
            scaled = src_size.scaled(self._target_size, Qt.KeepAspectRatioByExpanding)
            reader.setScaledSize(scaled)

        image = reader.read()
        if image.isNull():
            reason = reader.errorString()
            log.warning("image decode failed (%s): %s", reason, self._url)
            self.failed.emit(self._url, reason)
            return

        pixmap = QtGui.QPixmap.fromImage(image)
        self.ready.emit(self._url, pixmap)


class ImageCache(QtCore.QObject):
    """Application-wide image cache manager.

    Keeps a QNetworkAccessManager (one per process) and an in-memory dict of
    already-decoded QPixmaps so the same URL is never decoded twice per
    session.

    Usage
    -----
        cache = ImageCache(parent=self)
        cache.fetch(url, size, callback)   # callback(url, QPixmap)
    """

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._nam = QtNetwork.QNetworkAccessManager(self)
        self._pixmap_cache: dict[str, QtGui.QPixmap] = {}
        self._in_flight: dict[str, list] = {}   # url -> list of (size, cb)

    def fetch(
        self,
        url: str,
        size: QtCore.QSize,
        callback,  # Callable[[str, QPixmap], None]
    ) -> None:
        """Request a pixmap for *url* scaled to *size*.  Calls *callback* when
        ready (may be synchronous if already cached in memory).
        """
        if not url:
            return

        # In-memory cache hit.
        cache_key = f"{url}@{size.width()}x{size.height()}"
        if cache_key in self._pixmap_cache:
            callback(url, self._pixmap_cache[cache_key])
            return

        # Deduplicate concurrent requests for the same URL+size.
        if cache_key in self._in_flight:
            self._in_flight[cache_key].append(callback)
            return

        self._in_flight[cache_key] = [callback]

        req = ImageRequest(url, size, self._nam, self)
        req.ready.connect(lambda u, px, ck=cache_key: self._on_ready(ck, u, px))
        req.failed.connect(lambda u, r, ck=cache_key: self._on_failed(ck, u, r))
        req.start()

    def _on_ready(self, cache_key: str, url: str, pixmap: QtGui.QPixmap) -> None:
        self._pixmap_cache[cache_key] = pixmap
        for cb in self._in_flight.pop(cache_key, []):
            cb(url, pixmap)

    def _on_failed(self, cache_key: str, url: str, reason: str) -> None:
        for cb in self._in_flight.pop(cache_key, []):
            log.debug("image fetch failed for callback, url=%s reason=%s", url, reason)
