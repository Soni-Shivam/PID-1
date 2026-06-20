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
from core import store, x11
from core.paths import cache_file, config_file, ensure_dirs
from core.theme import ThemeManager
from dock.widget import DockWindow
from widgets import cms
from widgets.desktop import DesktopLayer

DEFAULT_HOTKEY = "Super+Space"

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


def _settings() -> dict:
    return store.read_json(config_file("settings.json"), default={}) or {}


def main() -> int:
    ensure_dirs()
    settings = _settings()
    app = QtWidgets.QApplication([])
    app.setApplicationName("jiopc-home")

    # Theme first: render the app-wide stylesheet + font before any window shows,
    # so first paint is already themed (no flash of unstyled chrome).
    theme = ThemeManager(app)
    theme.apply()

    # Desktop widget layer first (it sits at wallpaper level, behind everything).
    cms_service = cms.CmsService(
        settings.get("cms_endpoint", cms.default_endpoint()),
        cache_file(cms.CACHE_NAME))
    desktop = DesktopLayer(cms_service, theme)
    desktop.start()

    dock = DockWindow(theme)
    dock.start()

    # The menu is heavy, so build it lazily on first request to protect the
    # < 3 s startup budget; reuse the instance after that.
    state: dict = {"menu": None}

    def toggle_menu() -> None:
        if state["menu"] is None:
            from menu.window import MenuWindow
            state["menu"] = MenuWindow(theme)
        state["menu"].toggle()

    dock.menu_requested.connect(toggle_menu)

    hotkey = x11.HotkeyListener(settings.get("menu_hotkey", DEFAULT_HOTKEY))
    if hotkey.valid():
        hotkey.pressed.connect(toggle_menu)
        hotkey.start()

    # Stop background threads cleanly on quit (closeEvent won't fire; D4).
    def _cleanup() -> None:
        dock.stop()
        if hotkey.valid():
            hotkey.stop()

    app.aboutToQuit.connect(_cleanup)

    # Record first paint once the event loop has drawn the dock.
    QtCore.QTimer.singleShot(0, _log_first_paint)
    if os.environ.get("JIOPC_OPEN_MENU"):   # screenshot/verify hook
        QtCore.QTimer.singleShot(600, toggle_menu)

    # First-run wizard (Component E): shown only when the flag is absent, and
    # after the shell has painted so the tour can reference live components.
    def _maybe_wizard() -> None:
        from wizard.window import WizardWindow, is_done
        if is_done() and not os.environ.get("JIOPC_FORCE_WIZARD"):
            return
        state["wizard"] = WizardWindow(theme, dock)
        state["wizard"].show_wizard()

    QtCore.QTimer.singleShot(400, _maybe_wizard)
    return exec_app(app)


if __name__ == "__main__":
    raise SystemExit(main())
