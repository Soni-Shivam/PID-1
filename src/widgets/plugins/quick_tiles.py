"""Quick-launch tiles widget (CMS-fed).

A small grid of labelled tiles; each runs a namespaced action (app: or url:)
from the CMS feed. Re-renders on content_updated.
"""
from __future__ import annotations

from core.qt_compat import Qt, QtCore, QtGui, QtWidgets
from widgets.engine import WidgetContext, WidgetPlugin

_C = {"text": "#e6e6ea", "surface": "#242732", "hover": "#2c2f3a"}
_COLS = 2


class _QuickTiles(QtWidgets.QFrame):
    def __init__(self, ctx: WidgetContext) -> None:
        super().__init__()
        self._ctx = ctx
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(18, 16, 18, 16)
        outer.setSpacing(8)
        title = QtWidgets.QLabel("Start exploring")
        title.setStyleSheet(f"color:{_C['text']};font-size:16px;font-weight:700;")
        outer.addWidget(title)
        self._grid = QtWidgets.QGridLayout()
        self._grid.setSpacing(8)
        outer.addLayout(self._grid)
        outer.addStretch(1)

        if ctx.cms is not None:
            ctx.cms.content_updated.connect(self._render)
            self._render(ctx.cms.content())

    def _render(self, content: dict) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for i, tile in enumerate(content.get("tiles", [])[:6]):
            self._grid.addWidget(self._tile(tile), i // _COLS, i % _COLS)

    def _tile(self, tile: dict) -> QtWidgets.QToolButton:
        btn = QtWidgets.QToolButton()
        btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        icon = QtGui.QIcon.fromTheme(tile.get("icon", ""))
        if not icon.isNull():
            btn.setIcon(icon)
            btn.setIconSize(QtCore.QSize(22, 22))
        btn.setText(tile.get("label", ""))
        btn.setCursor(Qt.PointingHandCursor)
        btn.setMinimumHeight(44)
        btn.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                          QtWidgets.QSizePolicy.Fixed)
        btn.setStyleSheet(
            f"QToolButton{{text-align:left;border:none;border-radius:10px;"
            f"padding:6px 10px;color:{_C['text']};background:{_C['surface']};"
            f"font-size:12px;}}"
            f"QToolButton:hover{{background:{_C['hover']};}}")
        action = tile.get("action", "")
        if action:
            btn.clicked.connect(lambda: self._ctx.run_action(action))
        return btn


class QuickTilesPlugin(WidgetPlugin):
    id = "quick_tiles"
    name = "Quick Launch Tiles"
    default_size = (1, 1)
    needs_cms = True

    def create_view(self, ctx: WidgetContext) -> QtWidgets.QWidget:
        return _QuickTiles(ctx)
