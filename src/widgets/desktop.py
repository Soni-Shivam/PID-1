"""The desktop widget layer (Component C integrator).

A full-screen _NET_WM_WINDOW_TYPE_DESKTOP window (ME-07) that hosts the
arrangeable SnapGrid of plugin widgets. A slim top bar carries the Widget Store
button, a live slot badge, and a light/dark toggle. Right-click also opens the
store. Content is inset past the left dock strut and the bottom LxQt panel so
nothing is hidden.

Background: a rich diagonal gradient with radial glow accents and a dot-grid,
painted in paintEvent (compositor-free, core.background). Widget cards are glass
(rgba QSS over the gradient). All colours come from theme tokens.
"""
from __future__ import annotations

import os
import pwd

from core.qt_compat import Qt, QtCore, QtGui, QtWidgets
from core import x11
from core.background import paint_background
from core.theme import ThemeManager
from apps.desktop_entries import list_apps
from widgets import engine
from widgets.engine import WidgetContext
from widgets.grid import SnapGrid, WidgetCard, TOTAL_SLOTS
from widgets.store import WidgetStore

# Insets so grid content clears the left dock and the bottom LxQt panel.
_DOCK_INSET = 104
_PANEL_INSET = 52


def _username() -> str:
    try:
        info = pwd.getpwuid(os.getuid())
        return (info.pw_gecos or "").split(",")[0] or info.pw_name
    except KeyError:
        return ""


class DesktopLayer(QtWidgets.QWidget):
    """Wallpaper-level window hosting the widget grid + Widget Store."""

    def __init__(self, cms_service, theme: ThemeManager) -> None:
        super().__init__()
        self._cms = cms_service
        self._theme = theme
        self._username = _username()
        self._apps_by_id = {a.app_id: a for a in list_apps()}
        self._plugins = engine.discover_plugins()
        self._store: WidgetStore | None = None

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("desktopRoot")

        self._ctx = WidgetContext(
            cms=self._cms, run_action=self._run_action,
            username=self._username, theme=self._theme)

        self._build_ui()
        self._grid.capacity_changed.connect(self._on_capacity)
        theme.theme_changed.connect(self._on_theme_changed)

    # --- lifecycle --------------------------------------------------------
    def start(self) -> None:
        geo = QtWidgets.QApplication.primaryScreen().geometry()
        self.setGeometry(geo)
        wid = int(self.winId())
        x11.set_desktop_type(wid)
        self.show()
        x11.set_desktop_type(wid)
        self._grid.load(self._make_card, engine.load_layout())
        self._on_capacity(self._grid.used(), TOTAL_SLOTS)
        if self._cms is not None:
            self._cms.refresh()
        if os.environ.get("JIOPC_OPEN_STORE"):   # screenshot/verify hook
            QtCore.QTimer.singleShot(500, self._open_store)

    # --- background -------------------------------------------------------
    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802
        p = QtGui.QPainter(self)
        paint_background(p, self.width(), self.height(), self._theme.tokens)
        p.end()

    def _on_theme_changed(self) -> None:
        self.update()
        self._style_topbar()

    # --- UI ---------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(_DOCK_INSET, 22, 26, _PANEL_INSET)
        root.setSpacing(16)

        bar = QtWidgets.QHBoxLayout()
        bar.setSpacing(12)
        self._title = QtWidgets.QLabel("Your desktop")
        self._title.setObjectName("Greeting")
        self._badge = QtWidgets.QLabel()
        self._badge.setObjectName("GreetingSub")
        bar.addWidget(self._title)
        bar.addSpacing(8)
        bar.addWidget(self._badge)
        bar.addStretch(1)

        self._btn_theme = QtWidgets.QPushButton("◐  Theme")
        self._btn_theme.setCursor(Qt.PointingHandCursor)
        self._btn_theme.clicked.connect(self._toggle_theme)
        self._btn_store = QtWidgets.QPushButton("⊞  Widget Store")
        self._btn_store.setCursor(Qt.PointingHandCursor)
        self._btn_store.clicked.connect(self._open_store)
        bar.addWidget(self._btn_theme)
        bar.addWidget(self._btn_store)
        root.addLayout(bar)

        self._grid = SnapGrid(self._theme, self)
        root.addWidget(self._grid, 1)
        self._style_topbar()

    def _style_topbar(self) -> None:
        t = self._theme.tokens
        accent = (f"QPushButton{{background:{t['accent']};color:{t['on_accent']};"
                  f"border:none;border-radius:18px;padding:8px 18px;"
                  f"font-size:13px;font-weight:700;}}"
                  f"QPushButton:hover{{background:{t['accent_soft']};"
                  f"color:{t['accent']};border:1px solid {t['accent']};}}")
        ghost = (f"QPushButton{{background:{t['surface_alt']};color:{t['text']};"
                 f"border:1px solid {t['border']};border-radius:18px;"
                 f"padding:8px 18px;font-size:13px;font-weight:600;}}"
                 f"QPushButton:hover{{border-color:{t['accent']};color:{t['accent']};}}")
        self._btn_store.setStyleSheet(accent)
        self._btn_theme.setStyleSheet(ghost)

    # --- widget factory ---------------------------------------------------
    def _make_card(self, plugin_id: str,
                   size: tuple[int, int]) -> WidgetCard | None:
        plugin = self._plugins.get(plugin_id)
        if plugin is None:
            return None
        view = plugin.create_view(self._ctx)
        return WidgetCard(plugin, view, size, self._theme)

    def _run_action(self, action: str) -> None:
        engine.execute_action(action, self._apps_by_id)

    # --- store ------------------------------------------------------------
    def _open_store(self) -> None:
        if self._store is None:
            self._store = WidgetStore(
                self._plugins, self._grid, self._theme, self._ctx,
                self._add_widget)
        self._store.open_over(
            QtWidgets.QApplication.primaryScreen().geometry())

    def _add_widget(self, plugin_id: str, size: tuple) -> None:
        if self._grid.has(plugin_id):
            return
        card = self._make_card(plugin_id, tuple(size))
        if card and self._grid.add(card):
            self._grid._persist()

    def contextMenuEvent(self, e: QtGui.QContextMenuEvent) -> None:  # noqa: N802
        menu = QtWidgets.QMenu(self)
        menu.addAction("Open Widget Store...", self._open_store)
        menu.addAction("Switch light / dark", self._toggle_theme)
        menu.exec_(e.globalPos())

    def _toggle_theme(self) -> None:
        self._theme.set_theme("light" if self._theme.name == "dark" else "dark")

    def _on_capacity(self, used: int, total: int) -> None:
        self._badge.setText(f"{used} / {total} widgets")
