"""Quick-launch tiles widget (CMS-fed) — "Start exploring".

A grid of polished tiles; each runs a namespaced action (app: or url:) from the
CMS feed. Every tile shows a rounded gradient badge with the action's icon
rendered in white (or the label's initial when the theme has no icon), so the
widget looks consistent and vivid even when icon themes are sparse. Re-renders
on content_updated; colours come from the live theme tokens and restyle on
theme_changed.
"""
from __future__ import annotations

from core.qt_compat import Qt, QtCore, QtGui, QtWidgets
from widgets.engine import WidgetContext, WidgetPlugin

_COLS = 2
# A vivid, rotating badge palette (purple-led to match the shell).
_PALETTE = ["#b15cff", "#ec4899", "#22c55e", "#f59e0b", "#3b82f6", "#06b6d4"]


def _badge(icon_name: str, label: str, color_hex: str, px: int = 46) -> QtGui.QIcon:
    """A rounded gradient badge with the icon in white, or the label initial."""
    pm = QtGui.QPixmap(px, px)
    pm.fill(Qt.transparent)
    p = QtGui.QPainter(pm)
    p.setRenderHint(QtGui.QPainter.Antialiasing)
    p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
    c = QtGui.QColor(color_hex)
    grad = QtGui.QLinearGradient(0, 0, 0, px)
    grad.setColorAt(0.0, c.lighter(122))
    grad.setColorAt(1.0, c.darker(112))
    path = QtGui.QPainterPath()
    path.addRoundedRect(QtCore.QRectF(0, 0, px, px), px * 0.32, px * 0.32)
    p.fillPath(path, QtGui.QBrush(grad))

    icon = QtGui.QIcon.fromTheme(icon_name) if icon_name else QtGui.QIcon()
    if not icon.isNull():
        s = int(px * 0.56)
        src = icon.pixmap(s, s)
        white = QtGui.QPixmap(src.size())
        white.fill(Qt.transparent)
        wp = QtGui.QPainter(white)
        wp.drawPixmap(0, 0, src)
        wp.setCompositionMode(QtGui.QPainter.CompositionMode_SourceIn)
        wp.fillRect(white.rect(), QtGui.QColor("#ffffff"))
        wp.end()
        p.drawPixmap(int((px - white.width()) / 2),
                     int((px - white.height()) / 2), white)
    else:
        p.setPen(QtGui.QColor("#ffffff"))
        f = p.font()
        f.setPointSize(int(px * 0.34))
        f.setBold(True)
        p.setFont(f)
        p.drawText(pm.rect(), Qt.AlignCenter,
                   (label[:1] or "?").upper())
    p.end()
    return QtGui.QIcon(pm)


class _QuickTiles(QtWidgets.QFrame):
    def __init__(self, ctx: WidgetContext) -> None:
        super().__init__()
        self._ctx = ctx
        self._content: dict = {}
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(18, 16, 18, 16)
        outer.setSpacing(10)
        self._title = QtWidgets.QLabel("Start exploring")
        outer.addWidget(self._title)
        self._grid = QtWidgets.QGridLayout()
        self._grid.setSpacing(10)
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
            self._grid.addWidget(self._tile(tile, i), i // _COLS, i % _COLS)

    def _tile(self, tile: dict, index: int) -> QtWidgets.QToolButton:
        t = self._ctx.theme.tokens
        color = _PALETTE[index % len(_PALETTE)]
        btn = QtWidgets.QToolButton()
        btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        btn.setIcon(_badge(tile.get("icon", ""), tile.get("label", ""), color))
        btn.setIconSize(QtCore.QSize(46, 46))
        btn.setText(tile.get("label", ""))
        btn.setCursor(Qt.PointingHandCursor)
        btn.setMinimumHeight(96)
        btn.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                          QtWidgets.QSizePolicy.Expanding)
        btn.setStyleSheet(
            f"QToolButton{{border:1px solid {t['border']};"
            f"border-radius:16px;padding:12px 8px;color:{t['text']};"
            f"background:{t['surface_alt']};font-size:11px;font-weight:600;}}"
            f"QToolButton:hover{{background:{t['hover']};"
            f"border:1px solid {color};color:{t['text']};}}")
        action = tile.get("action", "")
        if action:
            btn.clicked.connect(lambda *_: self._ctx.run_action(action))
        return btn


class QuickTilesPlugin(WidgetPlugin):
    id = "quick_tiles"
    name = "Quick Launch Tiles"
    description = "One-tap shortcuts to your most used apps and actions."
    icon = "view-grid"
    default_size = (1, 1)
    sizes = [(1, 1), (2, 1)]
    needs_cms = True
    category = "Productivity"

    def create_view(self, ctx: WidgetContext) -> QtWidgets.QWidget:
        return _QuickTiles(ctx)
