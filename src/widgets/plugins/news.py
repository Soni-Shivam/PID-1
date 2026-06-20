"""News / headlines widget — live top headlines from NewsAPI (India).

Source priority, offline-first like the CMS pipeline:
1. show the cached NewsAPI headlines immediately (or the CMS feed's news as a
   fallback on a fresh profile / when no key is set);
2. refresh in a background thread (country=in) when shown and the cache is
   stale, with a short timeout;
3. on success, atomically cache the mapped headlines and re-render;
4. on any failure, log and keep serving what we have.

Clicking a headline opens its URL. Colours come from the live theme tokens and
restyle on theme_changed. The NewsAPI key is read via core.secrets (never
committed); without it the widget transparently uses the CMS feed.
"""
from __future__ import annotations

import calendar
import logging
import time

import requests

from core import secrets, store
from core.paths import cache_file
from core.qt_compat import Qt, QtCore, QtWidgets
from widgets.engine import WidgetContext, WidgetPlugin

log = logging.getLogger("jiopc.news")

# NewsAPI's top-headlines country=in returns nothing on this plan, so we pull
# the latest English articles from the major Indian outlets via /everything.
_NEWS_API = "https://newsapi.org/v2/everything"
_DOMAINS = ("thehindu.com,indianexpress.com,ndtv.com,"
            "timesofindia.indiatimes.com,hindustantimes.com,livemint.com")
_PAGE_SIZE = 12
_CACHE = "news.json"
_REFRESH_AFTER = 900      # seconds; only refetch when the cache is older
_TIMEOUT = 6


def _epoch(published_at: str) -> float:
    """Parse NewsAPI's ISO 'Z' timestamp to epoch seconds (0 on failure)."""
    try:
        return calendar.timegm(
            time.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ"))
    except (ValueError, TypeError):
        return 0.0


def _map_article(a: dict) -> dict:
    src = (a.get("source") or {}).get("name") or ""
    return {"headline": a.get("title", ""), "source": src,
            "url": a.get("url", ""), "ts": _epoch(a.get("publishedAt", ""))}


def _ago(ts: float) -> str:
    """Compact relative time, '' if no/!future timestamp."""
    try:
        delta = time.time() - float(ts)
    except (TypeError, ValueError):
        return ""
    if delta < 0:
        return ""
    if delta < 3600:
        return f"{int(delta // 60)}m"
    if delta < 86400:
        return f"{int(delta // 3600)}h"
    return f"{int(delta // 86400)}d"


class _NewsWorker(QtCore.QThread):
    done = QtCore.pyqtSignal(list)
    failed = QtCore.pyqtSignal(str)

    def __init__(self, key: str, parent=None) -> None:
        super().__init__(parent)
        self._key = key

    def run(self) -> None:
        try:
            resp = requests.get(
                _NEWS_API,
                params={"domains": _DOMAINS, "language": "en",
                        "sortBy": "publishedAt", "pageSize": _PAGE_SIZE,
                        "apiKey": self._key},
                timeout=_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") != "ok":
                raise ValueError(data.get("message", "newsapi error"))
            items = [_map_article(a) for a in data.get("articles", [])
                     if a.get("title")]
            if not items:
                raise ValueError("no articles")
            self.done.emit(items)
        except Exception as exc:  # network/parse: degrade gracefully
            self.failed.emit(str(exc))


class _NewsRow(QtWidgets.QFrame):
    """A clickable headline entry: accent marker + headline + source + age."""

    clicked = QtCore.pyqtSignal()

    def __init__(self, entry: dict, tokens: dict) -> None:
        super().__init__()
        self.setObjectName("newsRow")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(
            f"#newsRow{{background:transparent;border:none;border-radius:10px;}}"
            f"#newsRow:hover{{background:{tokens['hover']};}}")
        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(10, 8, 10, 8)
        row.setSpacing(10)

        bar = QtWidgets.QLabel()
        bar.setFixedWidth(3)
        bar.setStyleSheet(f"background:{tokens['accent']};border-radius:2px;")
        row.addWidget(bar)

        text = QtWidgets.QVBoxLayout()
        text.setSpacing(1)
        head = QtWidgets.QLabel(entry.get("headline", ""))
        head.setWordWrap(True)
        head.setStyleSheet(
            f"color:{tokens['text']};font-size:12px;font-weight:600;")
        src = QtWidgets.QLabel(entry.get("source", ""))
        src.setStyleSheet(f"color:{tokens['muted']};font-size:10px;")
        text.addWidget(head)
        text.addWidget(src)
        row.addLayout(text, 1)

        ago = _ago(entry.get("ts", 0))
        if ago:
            when = QtWidgets.QLabel(ago)
            when.setAlignment(Qt.AlignRight | Qt.AlignTop)
            when.setStyleSheet(
                f"color:{tokens['muted']};font-size:10px;font-weight:600;")
            row.addWidget(when, 0, Qt.AlignTop)

    def mousePressEvent(self, e) -> None:  # noqa: N802
        if e.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(e)


class _News(QtWidgets.QFrame):
    def __init__(self, ctx: WidgetContext) -> None:
        super().__init__()
        self._ctx = ctx
        self._items: list[dict] = []
        self._last_fetch = 0.0
        self._worker: _NewsWorker | None = None
        self._key = secrets.get("NEWS_API_KEY")

        self._lay = QtWidgets.QVBoxLayout(self)
        self._lay.setContentsMargins(22, 20, 22, 20)
        self._lay.setSpacing(10)
        self._title = QtWidgets.QLabel()
        self._lay.addWidget(self._title)
        self._items_lay = QtWidgets.QVBoxLayout()
        self._items_lay.setSpacing(2)
        self._lay.addLayout(self._items_lay)
        self._lay.addStretch(1)

        # Seed: cached NewsAPI headlines, else the CMS feed's news section.
        cached = store.read_json(cache_file(_CACHE), default=None)
        if isinstance(cached, list) and cached:
            self._items = cached
        elif ctx.cms is not None:
            self._items = (ctx.cms.content() or {}).get("news", [])

        self._apply_theme()
        ctx.theme.theme_changed.connect(self._apply_theme)

    def _apply_theme(self) -> None:
        t = self._ctx.theme.tokens
        self._title.setText(
            f"<span style='color:{t['accent']};'>▍</span> "
            f"<span style='color:{t['text']};font-size:15px;font-weight:700;'>"
            f"Top Headlines</span>")
        self._render()

    def _render(self) -> None:
        t = self._ctx.theme.tokens
        while self._items_lay.count():
            item = self._items_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for entry in self._items[:6]:
            row = _NewsRow(entry, t)
            url = entry.get("url", "")
            if url:
                row.clicked.connect(lambda u=url: self._ctx.run_action(f"url:{u}"))
            self._items_lay.addWidget(row)

    def _refresh(self) -> None:
        if not self._key:
            return
        if self._worker is not None and self._worker.isRunning():
            return
        if time.time() - self._last_fetch < _REFRESH_AFTER and self._items:
            return
        self._last_fetch = time.time()
        self._worker = _NewsWorker(self._key, self)
        self._worker.done.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_done(self, items: list) -> None:
        self._items = items
        store.write_json(cache_file(_CACHE), items)
        self._render()

    def _on_failed(self, msg: str) -> None:
        log.warning("news refresh failed, serving cache: %s", msg)

    def showEvent(self, e) -> None:  # noqa: N802 - refresh when shown if stale
        self._refresh()
        super().showEvent(e)


class NewsPlugin(WidgetPlugin):
    id = "news"
    name = "News & Headlines"
    description = "Live India top headlines from NewsAPI (offline-cached)."
    icon = "news-subscribe"
    default_size = (1, 2)
    sizes = [(1, 2), (1, 1), (2, 2)]
    needs_cms = True
    category = "Information"

    def create_view(self, ctx: WidgetContext) -> QtWidgets.QWidget:
        return _News(ctx)
