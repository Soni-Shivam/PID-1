"""Shared atmospheric background painter (compositor-free).

Paints the multi-layer desktop background — diagonal gradient + two radial
glow accents + a sparse dot-grid — in SCREEN space translated by (ox, oy).

This lets any window reproduce the exact pixels of the desktop behind it
without a compositor: DesktopLayer paints it at offset (0, 0); the dock paints
it offset by its own negative screen position, so its overflow strip (the
narrow zone where magnified icons poke above the shelf) blends seamlessly into
the desktop underneath instead of showing a mismatched rectangle.

All colours come from theme tokens; no inline hex literals are authoritative
(the string defaults are fallbacks only).
"""
from __future__ import annotations

from core.qt_compat import QtCore, QtGui


def paint_background(p: QtGui.QPainter, w: int, h: int, tokens: dict,
                     ox: int = 0, oy: int = 0) -> None:
    """Paint the full-screen background into ``p`` translated by (ox, oy).

    A point at screen coordinate (sx, sy) is drawn at (sx + ox, sy + oy), so a
    window at screen position (X, Y) passes ox=-X, oy=-Y to align with the
    desktop.  Callers clip ``p`` to the region they actually want filled.
    """
    p.save()
    p.setRenderHint(QtGui.QPainter.Antialiasing)
    p.translate(ox, oy)
    rect = QtCore.QRect(0, 0, w, h)

    # Layer 1 — diagonal gradient (four distinct stops)
    c0 = QtGui.QColor(tokens.get("gradient_top",    "#080c1a"))
    c1 = QtGui.QColor(tokens.get("gradient_mid",    "#0b1020"))
    c2 = QtGui.QColor(tokens.get("gradient_bottom", "#0d1326"))
    c3 = QtGui.QColor(c2).lighter(115)
    base = QtGui.QLinearGradient(0, 0, w, h)
    base.setColorAt(0.00, c0)
    base.setColorAt(0.30, c1)
    base.setColorAt(0.68, c2)
    base.setColorAt(1.00, c3)
    p.fillRect(rect, base)

    # Layer 2 — top-left radial glow (large, soft)
    glow_tl      = QtGui.QColor(tokens.get("glow_tl", "rgba(91,155,255,0.18)"))
    glow_tl_fade = QtGui.QColor(glow_tl); glow_tl_fade.setAlpha(0)
    g1 = QtGui.QRadialGradient(int(w * 0.05), int(h * 0.03), int(max(w, h) * 0.55))
    g1.setColorAt(0.0, glow_tl)
    g1.setColorAt(0.6, QtGui.QColor(glow_tl.red(), glow_tl.green(),
                                    glow_tl.blue(), glow_tl.alpha() // 3))
    g1.setColorAt(1.0, glow_tl_fade)
    p.fillRect(rect, g1)

    # Layer 3 — bottom-right radial glow (medium)
    glow_br      = QtGui.QColor(tokens.get("glow_br", "rgba(23,58,94,0.25)"))
    glow_br_fade = QtGui.QColor(glow_br); glow_br_fade.setAlpha(0)
    g2 = QtGui.QRadialGradient(int(w * 0.94), int(h * 0.92), int(max(w, h) * 0.45))
    g2.setColorAt(0.0, glow_br)
    g2.setColorAt(0.5, QtGui.QColor(glow_br.red(), glow_br.green(),
                                    glow_br.blue(), glow_br.alpha() // 2))
    g2.setColorAt(1.0, glow_br_fade)
    p.fillRect(rect, g2)

    # Layer 4 — dot-grid texture (1.5 px dots every 38 px, very subtle)
    dot_col = QtGui.QColor(tokens.get("text", "#eef1f6")); dot_col.setAlpha(9)
    p.setPen(QtGui.QPen(dot_col, 1.5))
    step = 38
    pts = [QtCore.QPoint(gx, gy)
           for gx in range(0, w + step, step)
           for gy in range(0, h + step, step)]
    if pts:
        p.drawPoints(*pts)

    p.restore()
