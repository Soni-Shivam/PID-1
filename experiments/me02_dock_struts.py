"""ME-02: dock window type + struts (highest-risk experiment).

PASS: `xprop -id <winid>` shows _NET_WM_WINDOW_TYPE = _NET_WM_WINDOW_TYPE_DOCK
and _NET_WM_STRUT_PARTIAL set; a maximized xterm stops ABOVE the dock; the dock
stays undecorated, above normal windows, on all desktops.

Run in VM: DISPLAY=:0 python3 experiments/me02_dock_struts.py
Then: WID from log -> `xprop -id <WID> _NET_WM_WINDOW_TYPE _NET_WM_STRUT_PARTIAL`
and maximize a window to check it does not cover the bar.
"""
from __future__ import annotations

from Xlib import Xatom, display

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QLabel, QWidget

DOCK_W = 600
DOCK_H = 56
GAP = 8

_d = display.Display()


def _atom(name: str) -> int:
    return _d.intern_atom(name)


def set_dock_type(win_id: int) -> None:
    """Mark the window as an EWMH dock so the WM keeps it bare and on top."""
    w = _d.create_resource_object("window", win_id)
    w.change_property(_atom("_NET_WM_WINDOW_TYPE"), Xatom.ATOM, 32,
                      [_atom("_NET_WM_WINDOW_TYPE_DOCK")])
    _d.sync()


def set_bottom_strut(win_id: int, reserve: int, x0: int, x1: int) -> None:
    """Reserve `reserve` px at the bottom across [x0, x1] so maximized
    windows stop above the dock. Sets both STRUT and STRUT_PARTIAL."""
    w = _d.create_resource_object("window", win_id)
    w.change_property(_atom("_NET_WM_STRUT"), Xatom.CARDINAL, 32,
                      [0, 0, 0, reserve])
    w.change_property(_atom("_NET_WM_STRUT_PARTIAL"), Xatom.CARDINAL, 32,
                      [0, 0, 0, reserve, 0, 0, 0, 0, 0, 0, x0, x1])
    _d.sync()


class Dock(QWidget):
    def __init__(self) -> None:
        super().__init__()
        # Frameless + on-top, but stay WM-managed (no X11BypassWindowManager):
        # the WM must honour the dock type and struts.
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setFixedSize(DOCK_W, DOCK_H)
        self.setStyleSheet("background:#1d1f27;")
        lbl = QLabel("ME-02 dock", self)
        lbl.setStyleSheet("color:#e6e6ea;font:600 14px;")
        lbl.move(16, 18)


def main() -> None:
    app = QApplication([])
    dock = Dock()
    geo = app.primaryScreen().geometry()  # full screen: struts are screen-relative
    x = geo.x() + (geo.width() - DOCK_W) // 2
    y = geo.y() + geo.height() - DOCK_H - GAP
    dock.move(x, y)

    # Set the dock type BEFORE mapping: realize the native window via winId()
    # (creates the X window but does not map it), set the property, then show().
    wid = int(dock.winId())
    set_dock_type(wid)
    dock.show()

    def after_show() -> None:
        set_dock_type(wid)  # re-assert in case Qt rewrote it during map
        reserve = DOCK_H + GAP
        set_bottom_strut(wid, reserve, x, x + DOCK_W - 1)
        print(f"WID 0x{wid:x} geo {x},{y} {DOCK_W}x{DOCK_H} "
              f"strut_bottom={reserve} x0={x} x1={x + DOCK_W - 1}", flush=True)
        print("CHECK: xprop -id 0x%x _NET_WM_WINDOW_TYPE _NET_WM_STRUT_PARTIAL"
              % wid, flush=True)

    QTimer.singleShot(0, after_show)
    QTimer.singleShot(600_000, app.quit)
    app.exec_()


if __name__ == "__main__":
    main()
