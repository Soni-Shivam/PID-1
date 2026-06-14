"""The application menu window (Component B).

A frameless launcher sized to the work area (so the dock stays visible beneath
it). Layout: a fixed header (search + chips + controls) pinned above a single
QScrollArea that contains everything else in one continuous flow:

  Recently used  (tile row)
  Recommended    (tile row)
  All apps       (4-column tile grid)

Scrolling the main area scrolls all three sections together — no separate inner
scroll views. Search hides the strips and shows only the All Apps grid. Esc hides.
Built lazily on first open, reused after that. Live-updates via QFileSystemWatcher.

Chrome themed by the app-wide stylesheet (#MenuRoot / #Search / [chip] / [tile]
/ #Section). Tile colours come from tokens, not inline CSS, so light↔dark works.
"""
from __future__ import annotations

import math

from core.qt_compat import Qt, QtCore, QtGui, QtWidgets
from core.theme import ThemeManager
from apps import launcher
from apps.desktop_entries import AppEntry, app_dirs
from menu import recommend
from menu.app_model import ENTRY, AppFilterProxy, AppListModel
from settings.dialog import SettingsDialog

# Main XDG categories -> friendly chip labels, in display order.
_CATEGORIES = [
    ("AudioVideo", "Media"), ("Graphics", "Graphics"), ("Development", "Developer"),
    ("Education", "Education"), ("Game", "Games"), ("Network", "Internet"),
    ("Office", "Office"), ("Science", "Science"), ("Settings", "Settings"),
    ("System", "System"), ("Utility", "Utilities"),
]
ICON = 48
TILE_W = 100
TILE_H = 88
GRID_COLS = 5     # columns in the all-apps grid
STRIP_N = 8       # max items in recent/recommended rows


def _icon(app: AppEntry) -> QtGui.QIcon:
    icon = QtGui.QIcon.fromTheme(app.icon) if app.icon else QtGui.QIcon()
    if icon.isNull():
        icon = QtGui.QIcon.fromTheme("application-x-executable")
    return icon


def _tile(app: AppEntry, launch_cb) -> QtWidgets.QToolButton:
    """Shared factory: one icon+label tile for strips and the grid."""
    btn = QtWidgets.QToolButton()
    btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
    btn.setIcon(_icon(app))
    btn.setIconSize(QtCore.QSize(ICON, ICON))
    btn.setText(app.name)
    btn.setFixedSize(TILE_W, TILE_H)
    btn.setToolTip(app.comment or app.name)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setProperty("tile", True)
    btn.clicked.connect(launch_cb)
    return btn


class _TileGrid(QtWidgets.QWidget):
    """A fixed-column grid of app tiles (no QListView; lives in a QScrollArea)."""

    def __init__(self, cols: int = GRID_COLS) -> None:
        super().__init__()
        self._cols = cols
        self._grid = QtWidgets.QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(4)
        for c in range(cols):
            self._grid.setColumnMinimumWidth(c, TILE_W)

    def set_tiles(self, tiles: list[QtWidgets.QWidget]) -> None:
        # Clear
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        # Fill
        for i, t in enumerate(tiles):
            self._grid.addWidget(t, i // self._cols, i % self._cols)
        # Pad last row so columns are uniform
        remainder = len(tiles) % self._cols
        if remainder:
            for i in range(self._cols - remainder):
                spacer = QtWidgets.QWidget()
                spacer.setFixedSize(TILE_W, TILE_H)
                self._grid.addWidget(spacer,
                                     len(tiles) // self._cols,
                                     remainder + i)


class MenuWindow(QtWidgets.QWidget):
    """Lazily-built, reusable application launcher with a unified scroll."""

    def __init__(self, theme: ThemeManager) -> None:
        super().__init__()
        self._theme = theme
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("MenuRoot")

        self.model = AppListModel(self)
        self.proxy = AppFilterProxy(self)
        self.proxy.setSourceModel(self.model)

        self._build_ui()
        self._build_chips()

        self._watcher = QtCore.QFileSystemWatcher(self)
        self._watcher.addPaths([str(d) for d in app_dirs() if d.is_dir()])
        self._watcher.directoryChanged.connect(self._schedule_reload)
        self._reload_timer = QtCore.QTimer(self)
        self._reload_timer.setSingleShot(True)
        self._reload_timer.timeout.connect(self._do_reload)

        QtWidgets.QShortcut(QtGui.QKeySequence(Qt.Key_Escape), self, self.hide)

    # --- UI construction --------------------------------------------------
    def _build_ui(self) -> None:
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(48, 36, 48, 0)
        outer.setSpacing(12)

        # --- Fixed header (search + chips + controls) ---
        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText("Search apps")
        self.search.setClearButtonEnabled(True)
        self.search.setObjectName("Search")
        self.search.textChanged.connect(self._on_search)
        self.search.returnPressed.connect(self._launch_first)
        outer.addWidget(self.search)

        controls = QtWidgets.QHBoxLayout()
        self.chips_row = QtWidgets.QHBoxLayout()
        self.chips_row.setSpacing(8)
        chip_host = QtWidgets.QWidget()
        chip_host.setLayout(self.chips_row)
        controls.addWidget(chip_host, 1)
        self.order = QtWidgets.QComboBox()
        self.order.addItems(["Name", "Most used", "Recently used"])
        self.order.currentTextChanged.connect(self._on_order)
        controls.addWidget(QtWidgets.QLabel("Sort:"))
        controls.addWidget(self.order)
        settings_btn = QtWidgets.QPushButton("Settings")
        settings_btn.setIcon(QtGui.QIcon.fromTheme("configure"))
        settings_btn.setCursor(Qt.PointingHandCursor)
        settings_btn.clicked.connect(self._open_settings)
        controls.addWidget(settings_btn)
        outer.addLayout(controls)

        # --- Single scrollable content area ---
        self._scroll = QtWidgets.QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("background:transparent;")

        self._content = QtWidgets.QWidget()
        self._content.setStyleSheet("background:transparent;")
        self._content_lay = QtWidgets.QVBoxLayout(self._content)
        self._content_lay.setContentsMargins(0, 8, 0, 24)
        self._content_lay.setSpacing(6)

        # Recent section
        self._recent_label = self._section_label("Recently used")
        self._recent_grid = _TileGrid(cols=STRIP_N)
        self._content_lay.addWidget(self._recent_label)
        self._content_lay.addWidget(self._recent_grid)

        # Recommended section
        self._reco_label = self._section_label("Recommended")
        self._reco_grid = _TileGrid(cols=STRIP_N)
        self._content_lay.addWidget(self._reco_label)
        self._content_lay.addWidget(self._reco_grid)

        # All apps section
        self._all_label = self._section_label("All apps")
        self._all_grid = _TileGrid(cols=GRID_COLS)
        self._content_lay.addWidget(self._all_label)
        self._content_lay.addWidget(self._all_grid)
        self._content_lay.addStretch(1)

        self._scroll.setWidget(self._content)
        outer.addWidget(self._scroll, 1)

    def _section_label(self, text: str) -> QtWidgets.QLabel:
        lbl = QtWidgets.QLabel(text)
        lbl.setObjectName("Section")
        return lbl

    def _build_chips(self) -> None:
        while self.chips_row.count():
            item = self.chips_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._chip_group = QtWidgets.QButtonGroup(self)
        self._chip_group.setExclusive(True)
        present = set()
        for app in self.model._apps:  # noqa: SLF001
            present.update(app.categories)
        self._add_chip("All", "", checked=True)
        for cat, label in _CATEGORIES:
            if cat in present:
                self._add_chip(label, cat)
        self.chips_row.addStretch(1)

    def _add_chip(self, label: str, category: str, checked: bool = False) -> None:
        chip = QtWidgets.QPushButton(label)
        chip.setCheckable(True)
        chip.setChecked(checked)
        chip.setCursor(Qt.PointingHandCursor)
        chip.setProperty("chip", True)
        chip.clicked.connect(lambda: self._on_chip(category))
        self._chip_group.addButton(chip)
        self.chips_row.addWidget(chip)

    def _on_chip(self, category: str) -> None:
        self.proxy.set_category(category)
        self._rebuild_all_grid()

    # --- data filling -----------------------------------------------------
    def _fill_strip(self, grid: _TileGrid, apps: list[AppEntry]) -> None:
        tiles = [_tile(a, lambda a=a: self._launch(a)) for a in apps]
        grid.set_tiles(tiles)

    def _rebuild_all_grid(self) -> None:
        """Rebuild the All Apps grid from the current proxy model state."""
        apps = []
        for row in range(self.proxy.rowCount()):
            app = self.proxy.data(self.proxy.index(row, 0), ENTRY)
            if app:
                apps.append(app)
        tiles = [_tile(a, lambda a=a: self._launch(a)) for a in apps]
        self._all_grid.set_tiles(tiles)

    def _refresh_strips(self) -> None:
        apps = self.model._apps  # noqa: SLF001
        self._fill_strip(self._recent_grid, recommend.recently_used(apps, STRIP_N))
        self._fill_strip(self._reco_grid, recommend.recommended(apps, STRIP_N))

    def _set_sections_visible(self, visible: bool) -> None:
        for w in (self._recent_label, self._recent_grid,
                  self._reco_label, self._reco_grid):
            w.setVisible(visible)

    # --- interaction ------------------------------------------------------
    def _on_search(self, text: str) -> None:
        self.proxy.set_query(text)
        searching = bool(text.strip())
        self._set_sections_visible(not searching)
        self._rebuild_all_grid()

    def _on_order(self, label: str) -> None:
        self.proxy.set_order(
            {"Most used": "most_used", "Recently used": "recent"}.get(label, "name"))
        self._rebuild_all_grid()

    def _launch_first(self) -> None:
        if self.proxy.rowCount():
            app = self.proxy.data(self.proxy.index(0, 0), ENTRY)
            if app:
                self._launch(app)

    def _launch(self, app: AppEntry) -> None:
        launcher.launch(app)
        self.hide()

    def _open_settings(self) -> None:
        SettingsDialog(self._theme, self).exec_()

    # --- live updates -----------------------------------------------------
    def _schedule_reload(self, _path: str) -> None:
        self._reload_timer.start(1000)

    def _do_reload(self) -> None:
        self.model.reload()
        self._build_chips()
        self._refresh_strips()
        self._rebuild_all_grid()

    # --- show/hide --------------------------------------------------------
    def toggle(self) -> None:
        if self.isVisible():
            self.hide()
            return
        self.setGeometry(QtWidgets.QApplication.primaryScreen().availableGeometry())
        self.search.clear()
        self.proxy.set_query("")
        self.proxy.set_category("")
        self._set_sections_visible(True)
        self._refresh_strips()
        self._rebuild_all_grid()
        # Reset scroll to top
        self._scroll.verticalScrollBar().setValue(0)
        self.show()
        self.raise_()
        self.activateWindow()
        self.search.setFocus()
