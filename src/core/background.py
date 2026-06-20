"""Shared atmospheric background painter (compositor-free).

Paints the desktop background — an optional wallpaper image, or a multi-layer
diagonal gradient + two radial glow accents + a sparse dot-grid — in SCREEN
space translated by (ox, oy).

This lets any window reproduce the exact pixels of the desktop behind it
without a compositor: DesktopLayer paints it at offset (0, 0); the dock paints
it offset by its own negative screen position, so its overflow strip (the
narrow zone where magnified icons poke above the shelf) blends seamlessly into
the desktop underneath instead of showing a mismatched rectangle.

When the active theme sets a ``wallpaper_image`` token, that photo is drawn
cover-scaled (decoded once at screen size and cached) under a subtle darkening
scrim so widget cards stay legible; otherwise the painted gradient is used.
All colours come from theme tokens; no inline hex literals are authoritative
(the string defaults are fallbacks only).
"""
from __future__ import annotations

from pathlib import Path

from core.qt_compat import QtCore, QtGui
from core.colors import to_qcolor

_ASSETS = Path(__file__).resolve().parent.parent / "assets"
# Cache the cover-scaled wallpaper keyed by (name, w, h) so repaints are cheap
# and only one screen-sized pixmap is ever held (RAM budget).
_WALL_CACHE: dict[tuple, QtGui.QPixmap | None] = {}


def _wallpaper(name: str, w: int, h: int) -> QtGui.QPixmap | None:
    """Decode *name* from src/assets cover-scaled to w x h (cached). None if absent."""
    if not name or w <= 0 or h <= 0:
        return None
    key = (name, w, h)
    if key in _WALL_CACHE:
        return _WALL_CACHE[key]
    path = _ASSETS / name
    pm: QtGui.QPixmap | None = None
    if path.exists():
        reader = QtGui.QImageReader(str(path))
        sz = reader.size()
        if sz.isValid() and sz.width() > 0 and sz.height() > 0:
            # Decode at the smallest size that still covers w x h (centre-crop).
            scale = max(w / sz.width(), h / sz.height())
            reader.setScaledSize(QtCore.QSize(max(w, round(sz.width() * scale)),
                                              max(h, round(sz.height() * scale))))
        img = reader.read()
        if not img.isNull():
            pm = QtGui.QPixmap.fromImage(img)
    _WALL_CACHE.clear()          # keep at most one cached wallpaper
    _WALL_CACHE[key] = pm
    return pm


def paint_background(p: QtGui.QPainter, w: int, h: int, tokens: dict,
                     ox: int = 0, oy: int = 0) -> None:
    """Paint the full-screen background into ``p`` translated by (ox, oy).

    A point at screen coordinate (sx, sy) is drawn at (sx + ox, sy + oy), so a
    window at screen position (X, Y) passes ox=-X, oy=-Y to align with the
    desktop.  Callers clip ``p`` to the region they actually want filled.
    """
    p.save()
    p.setRenderHint(QtGui.QPainter.Antialiasing)
    p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
    p.translate(ox, oy)
    rect = QtCore.QRect(0, 0, w, h)

    wall = _wallpaper(tokens.get("wallpaper_image", ""), w, h)
    if wall is not None and not wall.isNull():
        sx = max(0, (wall.width() - w) // 2)
        sy = max(0, (wall.height() - h) // 2)
        p.drawPixmap(rect, wall, QtCore.QRect(sx, sy, w, h))
        # Gentle darkening scrim so glass cards and text stay readable.
        scrim = to_qcolor(tokens.get("wallpaper_scrim", "rgba(8,6,16,0.34)"))
        p.fillRect(rect, scrim)
        p.restore()
        return

    # Layer 1 — diagonal gradient (four distinct stops)
    c0 = to_qcolor(tokens.get("gradient_top",    "#080c1a"))
    c1 = to_qcolor(tokens.get("gradient_mid",    "#0b1020"))
    c2 = to_qcolor(tokens.get("gradient_bottom", "#0d1326"))
    c3 = QtGui.QColor(c2).lighter(115)
    base = QtGui.QLinearGradient(0, 0, w, h)
    base.setColorAt(0.00, c0)
    base.setColorAt(0.30, c1)
    base.setColorAt(0.68, c2)
    base.setColorAt(1.00, c3)
    p.fillRect(rect, base)

    # Layer 2 — top-left radial glow (large, soft)
    glow_tl      = to_qcolor(tokens.get("glow_tl", "rgba(91,155,255,0.18)"))
    glow_tl_fade = QtGui.QColor(glow_tl); glow_tl_fade.setAlpha(0)
    g1 = QtGui.QRadialGradient(int(w * 0.05), int(h * 0.03), int(max(w, h) * 0.55))
    g1.setColorAt(0.0, glow_tl)
    g1.setColorAt(0.6, QtGui.QColor(glow_tl.red(), glow_tl.green(),
                                    glow_tl.blue(), glow_tl.alpha() // 3))
    g1.setColorAt(1.0, glow_tl_fade)
    p.fillRect(rect, g1)

    # Layer 3 — bottom-right radial glow (medium)
    glow_br      = to_qcolor(tokens.get("glow_br", "rgba(23,58,94,0.25)"))
    glow_br_fade = QtGui.QColor(glow_br); glow_br_fade.setAlpha(0)
    g2 = QtGui.QRadialGradient(int(w * 0.94), int(h * 0.92), int(max(w, h) * 0.45))
    g2.setColorAt(0.0, glow_br)
    g2.setColorAt(0.5, QtGui.QColor(glow_br.red(), glow_br.green(),
                                    glow_br.blue(), glow_br.alpha() // 2))
    g2.setColorAt(1.0, glow_br_fade)
    p.fillRect(rect, g2)

    # Layer 4 — dot-grid texture (1.5 px dots every 38 px, very subtle)
    dot_col = to_qcolor(tokens.get("text", "#eef1f6")); dot_col.setAlpha(9)
    p.setPen(QtGui.QPen(dot_col, 1.5))
    step = 38
    pts = [QtCore.QPoint(gx, gy)
           for gx in range(0, w + step, step)
           for gy in range(0, h + step, step)]
    if pts:
        p.drawPoints(*pts)

    p.restore()
