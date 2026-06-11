"""News / headlines widget (CMS-fed).

Lists headlines from the CMS feed; clicking one opens its URL. Re-renders when
the CmsService emits content_updated, so a background refresh updates it live.
Colours come from the live theme tokens and restyle on theme_changed (Phase D).
"""
from __future__ import annotations

from core.qt_compat import Qt, QtWidgets
from widgets.engine import WidgetContext, WidgetPlugin


class _News(QtWidgets.QFrame):
    def __init__(self, ctx: WidgetContext) -> None:
        super().__init__()
        self._ctx = ctx
        self._content: dict = {}
        self._lay = QtWidgets.QVBoxLayout(self)
        self._lay.setContentsMargins(18, 16, 18, 16)
        self._lay.setSpacing(8)
        self._title = QtWidgets.QLabel("Top Headlines")
        self._lay.addWidget(self._title)
        self._items = QtWidgets.QVBoxLayout()
        self._items.setSpacing(6)
        self._lay.addLayout(self._items)
        self._lay.addStretch(1)

        self._apply_theme()
        ctx.theme.theme_changed.connect(self._apply_theme)
        if ctx.cms is not None:
            ctx.cms.content_updated.connect(self._render)
            self._render(ctx.cms.content())

    def _apply_theme(self) -> None:
        t = self._ctx.theme.tokens
        self._title.setStyleSheet(f"color:{t['text']};font-size:16px;font-weight:700;")
        self._render(self._content)

    def _render(self, content: dict) -> None:
        self._content = content or {}
        while self._items.count():
            item = self._items.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for entry in self._content.get("news", [])[:6]:
            self._items.addWidget(self._row(entry))

    def _row(self, entry: dict) -> QtWidgets.QWidget:
        t = self._ctx.theme.tokens
        btn = QtWidgets.QToolButton()
        btn.setText(f"{entry.get('headline', '')}\n{entry.get('source', '')}")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
        btn.setStyleSheet(
            f"QToolButton{{text-align:left;border:none;border-radius:8px;"
            f"padding:6px 8px;color:{t['text']};font-size:12px;}}"
            f"QToolButton:hover{{background:{t['hover']};}}")
        url = entry.get("url", "")
        if url:
            btn.clicked.connect(lambda: self._ctx.run_action(f"url:{url}"))
        return btn


class NewsPlugin(WidgetPlugin):
    id = "news"
    name = "News & Headlines"
    default_size = (1, 2)
    needs_cms = True

    def create_view(self, ctx: WidgetContext) -> QtWidgets.QWidget:
        return _News(ctx)
