"""Entry point for the jiopc-home desktop shell (single QApplication process).

Phase P skeleton: paints a frameless placeholder dock bottom-centre and records
a first-paint timestamp to /tmp/jiopc-startup.log. The launcher (/usr/bin/jiopc-home)
logs the session-start time to the same file; the delta is the login-to-visible
figure tracked against the < 3 s budget. Boot order grows here later:
theme -> dock -> desktop layer -> lazy rest.
"""
from __future__ import annotations

import os
import time

from core.qt_compat import Qt, QtCore, QtGui, QtWidgets, exec_app

T_IMPORT = time.monotonic()

STARTUP_LOG = os.environ.get("JIOPC_STARTUP_LOG", "/tmp/jiopc-startup.log")
DOCK_W = 200
DOCK_H = 48
EDGE_GAP = 8
RADIUS = 10


def _vmrss_mb() -> float:
    """Resident set size of this process in MB, read from /proc."""
    try:
        with open("/proc/self/status") as fh:
            for line in fh:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024.0
    except OSError:
        pass
    return -1.0


def _log_first_paint() -> None:
    """Append a first-paint marker for the startup-timing benchmark."""
    line = (
        f"FIRST_PAINT epoch={time.time():.3f} "
        f"proc_s={time.monotonic() - T_IMPORT:.3f} "
        f"rss_mb={_vmrss_mb():.1f}\n"
    )
    try:
        with open(STARTUP_LOG, "a") as fh:
            fh.write(line)
    except OSError:
        pass
    print(line, end="", flush=True)


class PlaceholderDock(QtWidgets.QWidget):
    """Minimal bottom-centre bar standing in for the real dock (Phase A)."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("jiopc-home")
        # Frameless, always-on-top tool window; real dock-type comes in Phase A.
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setFixedSize(DOCK_W, DOCK_H)
        self._painted = False

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        label = QtWidgets.QLabel("JioPC Home")
        label.setAlignment(Qt.AlignCenter)
        # Solid colours only: no compositor means no real transparency.
        self.setStyleSheet(
            "PlaceholderDock { background-color: #1d1f27; }"
            "QLabel { color: #e6e6ea; font-size: 14px; font-weight: 600; }"
        )
        layout.addWidget(label)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:  # noqa: N802
        # Rounded corners without a compositor: clip the window with a mask so
        # the corners read as transparent to the WM rather than square black.
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(self.rect()), RADIUS, RADIUS)
        self.setMask(QtGui.QRegion(path.toFillPolygon().toPolygon()))
        super().resizeEvent(event)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802
        super().paintEvent(event)
        if not self._painted:
            self._painted = True
            _log_first_paint()


def main() -> int:
    app = QtWidgets.QApplication([])
    app.setApplicationName("jiopc-home")
    dock = PlaceholderDock()
    geo = app.primaryScreen().availableGeometry()
    dock.move(
        geo.x() + (geo.width() - DOCK_W) // 2,
        geo.y() + geo.height() - DOCK_H - EDGE_GAP,
    )
    dock.show()
    return exec_app(app)


if __name__ == "__main__":
    raise SystemExit(main())
