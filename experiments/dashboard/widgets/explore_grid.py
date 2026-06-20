"""
Widget 1: "Start Exploring" — 2×2 Quick Action Grid
=====================================================
A dark container with four colorful clickable image tiles.
Images are cropped & zoomed to fill tiles without stretching.
Falls back to gradient + emoji when images are unavailable.
"""
import os
from core.qt_compat import QtCore, QtGui, QtWidgets
from grid_manager import BaseWidgetCard, SlotSize
from design_system import (
    card_qss, label_qss, FAUX_BORDER_QSS,
    RADIUS, RADIUS_INNER, SPACING,
    BG_CARD_PURPLE,
    TEXT_PRIMARY, TEXT_SECONDARY,
    TILE_INDIGO, TILE_GREEN, TILE_CRIMSON, TILE_MUSTARD,
    FONT_STACK,
)

_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")

# Each tile: (image_file, emoji_fallback, label, bg_fallback, accent)
_TILES = [
    ("explore_study.png",   "📚", "Study",       TILE_INDIGO,  "#818CF8"),
    ("explore_gaming.png",  "🎮", "Play games",  TILE_GREEN,   "#4ADE80"),
    ("explore_fitness.png", "🏃", "Fitness",     TILE_CRIMSON, "#F87171"),
    ("explore_invest.png",  "📈", "Investments", TILE_MUSTARD, "#FCD34D"),
]

# Cache pixmaps
_PX_CACHE: dict = {}

def _load_px(fname: str) -> QtGui.QPixmap:
    if fname not in _PX_CACHE:
        path = os.path.join(_ASSETS_DIR, fname)
        px = QtGui.QPixmap(path) if os.path.exists(path) else QtGui.QPixmap()
        _PX_CACHE[fname] = px
    return _PX_CACHE[fname]


class ExploreTile(QtWidgets.QFrame):
    clicked = QtCore.pyqtSignal(str)

    def __init__(self, img_file: str, emoji: str, label: str,
                 bg: str, accent: str, parent=None):
        super().__init__(parent)
        self._label_id = label
        self._img_file = img_file
        self._emoji    = emoji
        self._bg       = bg
        self._accent   = accent
        self._hovered  = False

        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setAttribute(QtCore.Qt.WA_Hover)
        self.setStyleSheet("ExploreTile { background: transparent; border: none; }")

        # Preload
        _load_px(img_file)

    # ── painting ─────────────────────────────────────────────────────────────
    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        w, h = self.width(), self.height()
        r    = RADIUS_INNER
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(0, 0, w, h), r, r)
        p.setClipPath(path)

        px = _load_px(self._img_file)
        if not px.isNull():
            # Zoom-crop: cover the tile without stretching
            pw, ph = px.width(), px.height()
            scale  = max(w / pw, h / ph)
            sw, sh = int(pw * scale), int(ph * scale)
            sx = (w - sw) // 2
            sy = (h - sh) // 2
            p.drawPixmap(sx, sy, sw, sh, px)

            # Dark scrim at bottom for text legibility
            scrim = QtGui.QLinearGradient(0, h * 0.40, 0, h)
            scrim.setColorAt(0, QtGui.QColor(0, 0, 0, 0))
            scrim.setColorAt(1, QtGui.QColor(0, 0, 0, 200))
            p.fillRect(QtCore.QRectF(0, 0, w, h), scrim)
        else:
            # Fallback gradient
            grad = QtGui.QLinearGradient(0, 0, w, h)
            grad.setColorAt(0, QtGui.QColor(self._bg))
            grad.setColorAt(1, QtGui.QColor(self._bg).darker(140))
            p.fillRect(QtCore.QRectF(0, 0, w, h), grad)

            # Emoji in center
            ef = QtGui.QFont("Segoe UI Emoji", 28)
            p.setFont(ef)
            p.setPen(QtGui.QColor(self._accent))
            p.drawText(QtCore.QRectF(0, 0, w, h * 0.65),
                       QtCore.Qt.AlignCenter, self._emoji)

        # Hover highlight overlay
        if self._hovered:
            p.fillRect(QtCore.QRectF(0, 0, w, h),
                       QtGui.QColor(255, 255, 255, 18))

        # Glass border
        border_col = QtGui.QColor(255, 255, 255, 40 if self._hovered else 18)
        pen = QtGui.QPen(border_col, 1)
        p.setPen(pen)
        p.setBrush(QtCore.Qt.NoBrush)
        p.setClipping(False)
        p.drawRoundedRect(QtCore.QRectF(0.5, 0.5, w - 1, h - 1), r, r)

        # Label at bottom
        tf = QtGui.QFont("Century Gothic", 12)
        tf.setBold(True)
        p.setFont(tf)
        p.setPen(QtGui.QColor("#FFFFFF"))
        p.drawText(QtCore.QRect(12, h - 34, w - 16, 28),
                   QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
                   self._label_id)

        p.end()

    # ── events ────────────────────────────────────────────────────────────────
    def enterEvent(self, e):
        self._hovered = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        self.update()
        super().leaveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == QtCore.Qt.LeftButton:
            self.clicked.emit(self._label_id)
        super().mouseReleaseEvent(e)


class ExploreGridWidget(BaseWidgetCard):
    """2×2 Quick Action Image Grid"""
    SUPPORTED_SIZES = [SlotSize.LARGE]

    def __init__(self, state=None, size: SlotSize = SlotSize.LARGE):
        super().__init__("explore", size)

        self.setStyleSheet(f"ExploreGridWidget {{ {card_qss(BG_CARD_PURPLE)} }}")

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(16, 40, 16, 16)
        root.setSpacing(12)

        # Header
        hdr = QtWidgets.QHBoxLayout()
        lbl_title = QtWidgets.QLabel("Start exploring")
        lbl_title.setStyleSheet(label_qss(TEXT_PRIMARY, 18, "700"))
        hdr.addWidget(lbl_title)
        hdr.addStretch()
        root.addLayout(hdr)

        # 2×2 tile grid
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(10)

        for idx, (img, emoji, name, bg, accent) in enumerate(_TILES):
            tile = ExploreTile(img, emoji, name, bg, accent)
            tile.clicked.connect(self._on_tile_clicked)
            grid.addWidget(tile, idx // 2, idx % 2)

        root.addLayout(grid, 1)

    def _on_tile_clicked(self, name: str):
        print(f"[Explore] '{name}' clicked")
