"""Parse theme colour tokens into QColor, including CSS rgb()/rgba() syntax.

QtGui.QColor only understands '#hex' and named colours: a token like
'rgba(12,15,24,0.88)' parses as *invalid* and silently renders opaque BLACK.
Theme tokens use rgba() for translucency, so any hand-painted (QPainter) widget
that reads a token through QColor must go through here. QSS stylesheets parse
rgba() natively, so this helper is only needed for custom-painted code.
"""
from __future__ import annotations

import re

from core.qt_compat import QtGui

_RGBA = re.compile(
    r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)\s*)?\)",
    re.IGNORECASE)


def to_qcolor(value, default: str = "#000000") -> QtGui.QColor:
    """QColor from a token: handles '#hex', 'rgb(r,g,b)', 'rgba(r,g,b,a)'.

    ``a`` is a 0..1 float (CSS convention). Falls back to ``default`` for an
    unparseable value so a bad token degrades to an obvious colour, not black.
    """
    if isinstance(value, QtGui.QColor):
        return QtGui.QColor(value)
    s = str(value or "").strip()
    m = _RGBA.fullmatch(s)
    if m:
        r, g, b = (int(m.group(i)) for i in (1, 2, 3))
        a = m.group(4)
        alpha = round(float(a) * 255) if a is not None else 255
        clamp = lambda v: max(0, min(255, v))
        return QtGui.QColor(clamp(r), clamp(g), clamp(b), clamp(alpha))
    c = QtGui.QColor(s)
    return c if c.isValid() else QtGui.QColor(default)
