"""News / headlines widget (CMS-fed).

Lists headlines from the CMS feed; clicking one opens its URL. Re-renders when
the CmsService emits content_updated, so a background refresh updates it live.
Each row carries an accent marker, headline and a muted source line; colours come
from the live theme tokens and restyle on theme_changed (Phase D).
"""
from __future__ import annotations

from core.qt_compat import Qt, QtCore, QtWidgets
from widgets.engine import WidgetContext, WidgetPlugin


class _NewsRow(QtWidgets.QFrame):
    """A clickable headline entry: accent marker + headline + source."""

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
        bar.setStyleSheet(
            f"background:{tokens['accent']};border-radius:2px;")
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

    def mousePressEvent(self, e) -> None:  # noqa: N802
        if e.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(e)


class _News(QtWidgets.QFrame):
    def __init__(self, ctx: WidgetContext) -> None:
        super().__init__()
        self._ctx = ctx
        self._content: dict = {}
        self._lay = QtWidgets.QVBoxLayout(self)
        self._lay.setContentsMargins(22, 20, 22, 20)
        self._lay.setSpacing(10)
        self._title = QtWidgets.QLabel()
        self._lay.addWidget(self._title)
        self._items = QtWidgets.QVBoxLayout()
        self._items.setSpacing(2)
        self._lay.addLayout(self._items)
        self._lay.addStretch(1)

        self._apply_theme()
        ctx.theme.theme_changed.connect(self._apply_theme)
        if ctx.cms is not None:
            ctx.cms.content_updated.connect(self._render)
            self._render(ctx.cms.content())

    def _apply_theme(self) -> None:
        t = self._ctx.theme.tokens
        self._title.setText(
            f"<span style='color:{t['accent']};'>▍</span> "
            f"<span style='color:{t['text']};font-size:15px;font-weight:700;'>"
            f"Top Headlines</span>")
        self._render(self._content)

    def _render(self, content: dict) -> None:
        self._content = content or {}
        t = self._ctx.theme.tokens
        while self._items.count():
            item = self._items.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for entry in self._content.get("news", [])[:6]:
            row = _NewsRow(entry, t)
            url = entry.get("url", "")
            if url:
                row.clicked.connect(lambda u=url: self._ctx.run_action(f"url:{u}"))
            self._items.addWidget(row)


class NewsPlugin(WidgetPlugin):
    id = "news"
    name = "News & Headlines"
    description = "Live top headlines from the JioPC content feed."
    icon = "news-subscribe"
    default_size = (1, 2)
    needs_cms = True

    def create_view(self, ctx: WidgetContext) -> QtWidgets.QWidget:
        return _News(ctx)
