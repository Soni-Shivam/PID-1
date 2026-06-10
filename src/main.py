"""Entry point for the jiopc-home desktop shell (single QApplication process).

Boot order grows here: theme -> dock -> desktop layer -> lazy rest. Currently
boots the dock (Component A). The launcher (/usr/bin/jiopc-home) logs the
session-start time to /tmp/jiopc-startup.log; this records first paint, and the
delta is the login-to-visible figure tracked against the < 3 s budget.
"""
from __future__ import annotations

import os
import time

from core.qt_compat import QtCore, QtWidgets, exec_app
from core.paths import ensure_dirs
from dock.widget import DockWindow

T_IMPORT = time.monotonic()
STARTUP_LOG = os.environ.get("JIOPC_STARTUP_LOG", "/tmp/jiopc-startup.log")


def _vmrss_mb() -> float:
    try:
        with open("/proc/self/status") as fh:
            for line in fh:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024.0
    except OSError:
        pass
    return -1.0


def _log_first_paint() -> None:
    line = (f"FIRST_PAINT epoch={time.time():.3f} "
            f"proc_s={time.monotonic() - T_IMPORT:.3f} "
            f"rss_mb={_vmrss_mb():.1f}\n")
    try:
        with open(STARTUP_LOG, "a") as fh:
            fh.write(line)
    except OSError:
        pass
    print(line, end="", flush=True)


def main() -> int:
    ensure_dirs()
    app = QtWidgets.QApplication([])
    app.setApplicationName("jiopc-home")

    dock = DockWindow()
    dock.start()
    # Record first paint once the event loop has drawn the dock.
    QtCore.QTimer.singleShot(0, _log_first_paint)
    return exec_app(app)


if __name__ == "__main__":
    raise SystemExit(main())
