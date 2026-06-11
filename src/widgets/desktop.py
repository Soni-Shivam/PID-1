"""The desktop widget layer (Component C integrator).

A full-screen _NET_WM_WINDOW_TYPE_DESKTOP window (verified ME-07) that lays out
plugin views on a grid read from layout.json. Right-click opens a Widget Library
to add/remove widgets; changes persist. CMS-fed widgets share one CmsService and
refresh live. No per-second work except the clock and (visible-only) carousel.

The wallpaper and card surfaces are themed by the app-wide stylesheet
(themes/base.qss.tmpl keyed on #desktopRoot and QFrame[card]); plugins theme
their own contents from ctx.theme.tokens (Phase D).
"""
from __future__ import annotations

import os
import pwd

from core.qt_compat import Qt, QtGui, QtWidgets
from core import x11
from core.theme import ThemeManager
from apps.desktop_entries import list_apps
from widgets import engine
from widgets.engine import WidgetContext


def _username() -> str:
    try:
        info = pwd.getpwuid(os.getuid())
        return (info.pw_gecos or "").split(",")[0] or info.pw_name
    except KeyError:
        return ""


class DesktopLayer(QtWidgets.QWidget):
    """Wallpaper-level window hosting the widget grid."""

    def __init__(self, cms_service, theme: ThemeManager) -> None:
        super().__init__()
        self._cms = cms_service
        self._theme = theme
        self._username = _username()
        self._apps_by_id = {a.app_id: a for a in list_apps()}
        self._plugins = engine.discover_plugins()
        self._layout = engine.load_layout()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("desktopRoot")  # wallpaper from app-wide stylesheet
        self._grid_host = QtWidgets.QWidget(self)
        self._build_grid()

    # --- lifecycle --------------------------------------------------------
    def start(self) -> None:
        geo = QtWidgets.QApplication.primaryScreen().geometry()
        self.setGeometry(geo)
        wid = int(self.winId())          # realize, not mapped
        x11.set_desktop_type(wid)        # DESKTOP type before map (ME-07)
        self.show()
        x11.set_desktop_type(wid)        # re-assert after map
        if self._cms is not None:
            self._cms.refresh()

    def resizeEvent(self, e: QtGui.QResizeEvent) -> None:  # noqa: N802
        self._grid_host.setGeometry(self.rect())
        super().resizeEvent(e)

    # --- grid -------------------------------------------------------------
    def _build_grid(self) -> None:
        old = self._grid_host
        self._grid_host = QtWidgets.QWidget(self)
        self._grid_host.setGeometry(self.rect())
        grid = QtWidgets.QGridLayout(self._grid_host)
        grid.setContentsMargins(48, 44, 48, 44)
        grid.setSpacing(22)

        max_col = 0
        for item in self._layout:
            plugin = self._plugins.get(item["plugin_id"])
            if not plugin:
                continue
            ctx = WidgetContext(
                cms=self._cms if plugin.needs_cms else None,
                run_action=self._run_action,
                username=self._username,
                theme=self._theme,
            )
            card = self._wrap(plugin.create_view(ctx))
            grid.addWidget(card, item["row"], item["col"], item["h"], item["w"])
            max_col = max(max_col, item["col"] + item["w"])

        for c in range(max_col):
            grid.setColumnStretch(c, 2 if c else 1)
        self._grid_host.show()
        old.deleteLater()

    def _wrap(self, view: QtWidgets.QWidget) -> QtWidgets.QWidget:
        view.setProperty("card", True)  # surface from app-wide stylesheet
        view.setAttribute(Qt.WA_StyledBackground, True)
        return view

    def _run_action(self, action: str) -> None:
        engine.execute_action(action, self._apps_by_id)

    # --- customise --------------------------------------------------------
    def contextMenuEvent(self, e: QtGui.QContextMenuEvent) -> None:  # noqa: N802
        menu = QtWidgets.QMenu(self)
        menu.addAction("Customise widgets...", self._open_library)
        menu.exec_(e.globalPos())

    def _open_library(self) -> None:
        active = {item["plugin_id"] for item in self._layout}
        dlg = WidgetLibrary(self._plugins, active, self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            self._apply_selection(dlg.selected())

    def _apply_selection(self, selected: set[str]) -> None:
        kept = [it for it in self._layout if it["plugin_id"] in selected]
        existing = {it["plugin_id"] for it in kept}
        next_col = max((it["col"] + it["w"] for it in kept), default=0)
        for pid in selected - existing:
            plugin = self._plugins[pid]
            w, h = plugin.default_size
            kept.append({"plugin_id": pid, "col": next_col, "row": 0,
                         "w": w, "h": h})
            next_col += w
        self._layout = kept
        engine.save_layout(self._layout)
        self._build_grid()


class WidgetLibrary(QtWidgets.QDialog):
    """Pick which widgets appear on the desktop."""

    def __init__(self, plugins: dict, active: set[str],
                 parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Widget Library")
        self.setMinimumWidth(360)
        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(QtWidgets.QLabel("Choose widgets for your desktop:"))
        self._boxes: dict[str, QtWidgets.QCheckBox] = {}
        for pid, plugin in sorted(plugins.items(), key=lambda kv: kv[1].name):
            box = QtWidgets.QCheckBox(plugin.name)
            box.setChecked(pid in active)
            self._boxes[pid] = box
            lay.addWidget(box)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def selected(self) -> set[str]:
        return {pid for pid, box in self._boxes.items() if box.isChecked()}
