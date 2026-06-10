"""ME-01: blank shell window + RAM baseline.

PASS: frameless 400x60 window visible bottom-center in LxQt; VmRSS logged
at 10/30/60 s after first paint (expect ~50-90 MB for PyQt5).
Run in VM: DISPLAY=:0 python3 experiments/me01_blank_window.py
"""
from __future__ import annotations

import sys
import time

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QWidget

T0 = time.monotonic()


def vmrss_mb() -> float:
    """Read this process's resident set size in MB from /proc."""
    with open("/proc/self/status") as f:
        for line in f:
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) / 1024.0
    return -1.0


class BlankShell(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("me01-shell")
        if "--normal" not in sys.argv:
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setFixedSize(400, 60)
        self.setStyleSheet("background-color: #222233; border-radius: 8px;")
        self._painted = False

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().paintEvent(event)
        if not self._painted:
            self._painted = True
            print(f"FIRST_PAINT {time.monotonic() - T0:.3f}s "
                  f"RSS {vmrss_mb():.1f} MB", flush=True)


def main() -> None:
    app = QApplication([])
    win = BlankShell()
    screen = app.primaryScreen().availableGeometry()
    win.move(screen.x() + (screen.width() - win.width()) // 2,
             screen.y() + screen.height() - win.height() - 8)
    win.show()
    QTimer.singleShot(1000, lambda: print(
        f"MAPPED winid 0x{int(win.winId()):x} geo {win.geometry().x()},"
        f"{win.geometry().y()} {win.width()}x{win.height()} "
        f"visible={win.isVisible()}", flush=True))
    for delay_s in (10, 30, 60):
        QTimer.singleShot(
            delay_s * 1000,
            lambda d=delay_s: print(f"RSS@{d}s {vmrss_mb():.1f} MB", flush=True),
        )
    QTimer.singleShot(600_000, app.quit)
    app.exec_()
    print("ME-01 done", flush=True)


if __name__ == "__main__":
    main()
