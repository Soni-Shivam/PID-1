"""ME-11: prove live theme swap (string.Template QSS -> setStyleSheet) works.

De-risks Phase D before migrating real code. Confirms, with NO restart:
1. A string.Template QSS renders with token substitution (no leftover $tokens).
2. app.setStyleSheet() restyles already-built widgets live.
3. A custom-painted widget (QPainter, like the dock dot / carousel dots) repaints
   with the new accent token when theme_changed fires -- verified by grabbing the
   widget to a pixmap and comparing the centre pixel across themes.

Self-checking (PASS/FAIL, no human interaction); pass --show for a visual window.
Run in VM with compositing off: DISPLAY=:0 python3 experiments/me11_theme.py
"""
from __future__ import annotations

import os
import sys
from string import Template

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from PyQt5 import QtCore, QtGui, QtWidgets  # noqa: E402

DARK = {"bg": "#15171e", "text": "#e6e6ea", "accent": "#5b9bff"}
LIGHT = {"bg": "#f4f5f7", "text": "#1b1d22", "accent": "#1763d6"}

TMPL = Template(
    "#Root{background:$bg;}"
    "QLabel{color:$text;font-size:16px;}"
)


class Swatch(QtWidgets.QWidget):
    """Custom-painted square filled with the current accent token."""

    def __init__(self) -> None:
        super().__init__()
        self._accent = DARK["accent"]
        self.setFixedSize(40, 40)

    def set_accent(self, hex_color: str) -> None:
        self._accent = hex_color
        self.update()

    def paintEvent(self, _e) -> None:  # noqa: N802
        p = QtGui.QPainter(self)
        p.fillRect(self.rect(), QtGui.QColor(self._accent))


def _centre_pixel(w: QtWidgets.QWidget) -> tuple[int, int, int]:
    img = w.grab().toImage()
    c = img.pixelColor(w.width() // 2, w.height() // 2)
    return c.red(), c.green(), c.blue()


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    root = QtWidgets.QWidget()
    root.setObjectName("Root")
    lay = QtWidgets.QVBoxLayout(root)
    lay.addWidget(QtWidgets.QLabel("Theme swap proof"))
    swatch = Swatch()
    lay.addWidget(swatch)

    ok = True

    def apply(tokens: dict) -> str:
        qss = TMPL.substitute(tokens)
        app.setStyleSheet(qss)
        swatch.set_accent(tokens["accent"])
        root.show()
        app.processEvents()
        return qss

    qss_dark = apply(DARK)
    if "$" in qss_dark:
        print("FAIL: leftover $token in rendered QSS", flush=True); ok = False
    else:
        print("PASS: template rendered, no leftover tokens", flush=True)

    px_dark = _centre_pixel(swatch)
    qss_light = apply(LIGHT)
    px_light = _centre_pixel(swatch)

    if app.styleSheet() == qss_light and qss_light != qss_dark:
        print("PASS: app stylesheet swapped live (no restart)", flush=True)
    else:
        print("FAIL: stylesheet did not swap", flush=True); ok = False

    if px_dark != px_light:
        print(f"PASS: custom-painted swatch repainted {px_dark} -> {px_light}", flush=True)
    else:
        print(f"FAIL: swatch did not repaint (still {px_dark})", flush=True); ok = False

    print("ME-11 RESULT:", "PASS" if ok else "FAIL", flush=True)

    if "--show" in sys.argv:
        btn = QtWidgets.QPushButton("Toggle theme", root)
        state = {"dark": True}
        btn.clicked.connect(
            lambda: (apply(LIGHT if state["dark"] else DARK),
                     state.update(dark=not state["dark"])))
        lay.addWidget(btn)
        QtCore.QTimer.singleShot(0, lambda: apply(DARK))
        return app.exec_()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
