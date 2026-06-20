"""
JioPC Global Widget Design System
==================================
Single source of truth for all visual tokens, QSS helpers,
and shared widget utilities used by every dashboard card.

Spec compliance:
  - border-radius: 16px outer frame
  - Background: #1C1C1E standard, #2C2C2E highlighted, #2A2438 purple-tinted
  - Faux-depth borders: 1px rgba(255,255,255,0.08) top/left
                         1px rgba(0,0,0,0.4) bottom/right
  - No box-shadow, no GPU, no QML
"""
from __future__ import annotations
from core.qt_compat import QtCore, QtGui, QtWidgets

# ── Color palette ─────────────────────────────────────────────────────────────
BG_DEEP           = "#0F0F11"       # desktop background
BG_CARD           = "#1C1C1E"       # standard widget bg
BG_CARD_ALT       = "#2C2C2E"       # highlighted / secondary card
BG_CARD_PURPLE    = "#2A2438"       # subtle purple tint accent
BG_CARD_BLUE      = "#1A2235"       # subtle blue tint

# Accent backgrounds (explore tiles)
TILE_INDIGO   = "#1E1B4B"
TILE_GREEN    = "#052E16"
TILE_CRIMSON  = "#450A0A"
TILE_MUSTARD  = "#431407"

# Text
TEXT_PRIMARY   = "#F2F2F7"
TEXT_SECONDARY = "#8E8E93"
TEXT_TERTIARY  = "#48484A"

# Focus timer purple
BG_FOCUS      = "#4A3B69"
BG_FOCUS_BTN  = "#FFFFFF"

# Radius
RADIUS        = 16       # px — outer frame
RADIUS_INNER  = 10       # px — inner tiles

# Spacing
SPACING       = 16

# ── Faux-depth border (replaces box-shadow) ───────────────────────────────────
# Gives cards a subtle 3-D lift without GPU compositing.
FAUX_BORDER_QSS = """
    border-top:    1px solid rgba(255,255,255,0.08);
    border-left:   1px solid rgba(255,255,255,0.08);
    border-bottom: 1px solid rgba(0,0,0,0.40);
    border-right:  1px solid rgba(0,0,0,0.40);
"""

def card_qss(bg: str = BG_CARD, extra: str = "") -> str:
    """Return a complete QFrame style string for a standard card."""
    return f"""
        background-color: {bg};
        border-radius: {RADIUS}px;
        {FAUX_BORDER_QSS}
        {extra}
    """

def label_qss(color: str = TEXT_PRIMARY, size: int = 14,
              weight: str = "500", extra: str = "") -> str:
    return (f"color:{color}; font-size:{size}px; font-weight:{weight};"
            f" background:transparent; {extra}")


# ── Shared font constants ─────────────────────────────────────────────────────
FONT_STACK = ("'Century Gothic', 'Gill Sans', 'Trebuchet MS', "
              "system-ui, -apple-system, sans-serif")

# ── Elide utility ─────────────────────────────────────────────────────────────
def elide_text(text: str, font: QtGui.QFont, max_px: int,
               mode: QtCore.Qt.TextElideMode = QtCore.Qt.ElideRight) -> str:
    """
    Hard-truncate text using QFontMetrics before setting it on a QLabel.
    Prevents Qt from doing expensive multi-line layout math on every resize.
    """
    return QtGui.QFontMetrics(font).elidedText(text, mode, max_px)


def load_pixmap_scaled(path: str, w: int, h: int) -> QtGui.QPixmap:
    """
    Load an image file and downscale it immediately during decode.
    Uses QImageReader.setScaledSize() so the full-resolution buffer
    is never allocated in memory — critical for hero images.
    """
    reader = QtGui.QImageReader(path)
    sz = reader.size()
    if sz.isValid():
        w_ratio = w / sz.width()
        h_ratio = h / sz.height()
        scale = max(w_ratio, h_ratio)
        reader.setScaledSize(QtCore.QSize(int(sz.width() * scale), int(sz.height() * scale)))
    
    img = reader.read()
    if img.isNull():
        # Return a solid-colour fallback pixmap
        px = QtGui.QPixmap(w, h)
        px.fill(QtGui.QColor(BG_CARD))
        return px
    return QtGui.QPixmap.fromImage(img)


# ── Pill button QSS ───────────────────────────────────────────────────────────
def pill_btn_qss(bg: str = "#FFFFFF", fg: str = "#000000",
                 radius: int = 12) -> str:
    return f"""
        QPushButton {{
            background: {bg};
            color: {fg};
            border: none;
            border-radius: {radius}px;
            font-size: 15px;
            font-weight: 700;
            padding: 0 24px;
        }}
        QPushButton:hover   {{ background: rgba(255,255,255,0.85); }}
        QPushButton:pressed {{ background: rgba(255,255,255,0.65); }}
    """


# ── Ghost / outline button QSS ────────────────────────────────────────────────
def ghost_btn_qss(fg: str = TEXT_PRIMARY, radius: int = 12) -> str:
    return f"""
        QPushButton {{
            background: transparent;
            color: {fg};
            border: 1.5px solid rgba(255,255,255,0.25);
            border-radius: {radius}px;
            font-size: 15px;
            font-weight: 600;
            padding: 0 24px;
        }}
        QPushButton:hover   {{ background: rgba(255,255,255,0.07); }}
        QPushButton:pressed {{ background: rgba(255,255,255,0.03); }}
    """
