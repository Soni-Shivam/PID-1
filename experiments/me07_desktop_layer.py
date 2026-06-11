"""ME-07: desktop-layer stacking vs pcmanfm-qt (Phase C, highest-risk).

PASS: a full-screen _NET_WM_WINDOW_TYPE_DESKTOP Qt window renders at desktop
level - ABOVE pcmanfm-qt's desktop (so our content shows) but BELOW all normal
windows (a qterminal covers it); lxqt-panel stays visible/usable.

Run in VM: DISPLAY=:0 python3 experiments/me07_desktop_layer.py
Then: xprop -root _NET_CLIENT_LIST_STACKING  (bottom->top order)
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from PyQt5.QtCore import Qt, QTimer  # noqa: E402
from PyQt5.QtGui import QColor, QPainter  # noqa: E402
from PyQt5.QtWidgets import QApplication, QWidget  # noqa: E402

from core import x11  # noqa: E402


class DesktopLayer(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#10202a"))
        p.setPen(QColor("#79c0ff"))
        f = p.font()
        f.setPointSize(28)
        p.setFont(f)
        p.drawText(self.rect(), Qt.AlignCenter,
                   "JioPC desktop layer (ME-07)\nopen a window - it should cover this")


def main() -> None:
    app = QApplication([])
    layer = DesktopLayer()
    geo = app.primaryScreen().geometry()
    layer.setGeometry(geo)
    wid = int(layer.winId())          # realize, not mapped
    x11.set_desktop_type(wid)         # DESKTOP type before map
    layer.show()

    def after() -> None:
        x11.set_desktop_type(wid)     # re-assert after map
        print(f"WID 0x{wid:x} geo {geo.width()}x{geo.height()}", flush=True)
        print("CHECK: xprop -root _NET_CLIENT_LIST_STACKING (our wid above "
              "pcmanfm-desktop, below normal windows)", flush=True)

    QTimer.singleShot(0, after)
    QTimer.singleShot(600_000, app.quit)
    app.exec_()


if __name__ == "__main__":
    main()
