"""Quick-launch tiles widget (CMS-fed).

A small grid of labelled tiles; each runs a namespaced action (app: or url:)
from the CMS feed. Re-renders on content_updated. Colours come from the live
theme tokens and restyle on theme_changed (Phase D).
"""
from __future__ import annotations

from core.qt_compat import Qt, QtCore, QtGui, QtWidgets
from widgets.engine import WidgetContext, WidgetPlugin

_COLS = 2


class _QuickTiles(QtWidgets.QFrame):
    def __init__(self, ctx: WidgetContext) -> None:
        super().__init__()
        self._ctx = ctx
        self._content: dict = {}
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(18, 16, 18, 16)
        outer.setSpacing(8)
        self._title = QtWidgets.QLabel("Start exploring")
        outer.addWidget(self._title)
        self._grid = QtWidgets.QGridLayout()
        self._grid.setSpacing(8)
        outer.addLayout(self._grid)
        outer.addStretch(1)

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
            f"Start exploring</span>")
        self._render(self._content)

    def _render(self, content: dict) -> None:
        self._content = content or {}
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for i, tile in enumerate(self._content.get("tiles", [])[:6]):
            self._grid.addWidget(self._tile(tile), i // _COLS, i % _COLS)

    def _tile(self, tile: dict) -> QtWidgets.QToolButton:
        t = self._ctx.theme.tokens
        btn = QtWidgets.QToolButton()
        btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        icon = QtGui.QIcon.fromTheme(tile.get("icon", ""))
        if not icon.isNull():
            btn.setIcon(icon)
            btn.setIconSize(QtCore.QSize(22, 22))
        btn.setText(tile.get("label", ""))
        btn.setCursor(Qt.PointingHandCursor)
        btn.setMinimumHeight(52)
        btn.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                          QtWidgets.QSizePolicy.Fixed)
        btn.setStyleSheet(
            f"QToolButton{{text-align:left;border:1px solid {t['border']};"
            f"border-radius:12px;padding:8px 12px;color:{t['text']};"
            f"background:{t['surface_alt']};font-size:12px;font-weight:600;}}"
            f"QToolButton:hover{{background:{t['accent_soft']};"
            f"border:1px solid {t['accent']};color:{t['accent']};}}")
        action = tile.get("action", "")
        if action:
            btn.clicked.connect(lambda: self._ctx.run_action(action))
        return btn


class QuickTilesPlugin(WidgetPlugin):
    id = "quick_tiles"
    name = "Quick Launch Tiles"
    description = "One-tap shortcuts to your most used apps and actions."
    icon = "view-grid"
    default_size = (1, 1)
    needs_cms = True

    def create_view(self, ctx: WidgetContext) -> QtWidgets.QWidget:
        return _QuickTiles(ctx)
