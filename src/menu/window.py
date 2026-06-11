"""The application menu window (Component B).

A frameless launcher sized to the work area (so the dock stays visible beneath
it). Top to bottom: search box, category chips, order-by, a Recently Used strip,
a Recommended strip, and the full app grid. Search filters the grid live and
hides the strips. Click or Enter launches and hides; Esc hides. Built lazily on
first open and kept alive. Live-updates the catalogue via QFileSystemWatcher.

Colours live in _C for now and migrate to theme tokens in Phase D.
"""
from __future__ import annotations

from core.qt_compat import Qt, QtCore, QtGui, QtWidgets
from apps import launcher
from apps.desktop_entries import AppEntry, app_dirs
from menu import recommend
from menu.app_model import ENTRY, AppFilterProxy, AppListModel

_C = {
    "bg": "#15171e",
    "surface": "#1d1f27",
    "hover": "#2c2f3a",
    "accent": "#5b9bff",
    "text": "#e6e6ea",
    "muted": "#9aa0ab",
}

# Main XDG categories -> friendly chip labels, in display order.
_CATEGORIES = [
    ("AudioVideo", "Media"), ("Graphics", "Graphics"), ("Development", "Developer"),
    ("Education", "Education"), ("Game", "Games"), ("Network", "Internet"),
    ("Office", "Office"), ("Science", "Science"), ("Settings", "Settings"),
    ("System", "System"), ("Utility", "Utilities"),
]
ICON = 48
TILE_W = 108
TILE_H = 92
STRIP_N = 8


def _icon(app: AppEntry) -> QtGui.QIcon:
    icon = QtGui.QIcon.fromTheme(app.icon) if app.icon else QtGui.QIcon()
    if icon.isNull():
        icon = QtGui.QIcon.fromTheme("application-x-executable")
    return icon


class MenuWindow(QtWidgets.QWidget):
    """Lazily-built, reusable application launcher."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet(self._qss())
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
        outer.setContentsMargins(48, 36, 48, 24)
        outer.setSpacing(14)

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
        outer.addLayout(controls)

        self.recent_label, self.recent_strip = self._section("Recently used")
        outer.addWidget(self.recent_label)
        outer.addWidget(self.recent_strip)
        self.reco_label, self.reco_strip = self._section("Recommended")
        outer.addWidget(self.reco_label)
        outer.addWidget(self.reco_strip)

        self.grid_label = QtWidgets.QLabel("All apps")
        self.grid_label.setObjectName("Section")
        outer.addWidget(self.grid_label)
        self.grid = QtWidgets.QListView()
        self.grid.setViewMode(QtWidgets.QListView.IconMode)
        self.grid.setResizeMode(QtWidgets.QListView.Adjust)
        self.grid.setMovement(QtWidgets.QListView.Static)
        self.grid.setUniformItemSizes(True)
        self.grid.setIconSize(QtCore.QSize(ICON, ICON))
        self.grid.setGridSize(QtCore.QSize(TILE_W, TILE_H))
        self.grid.setSpacing(6)
        self.grid.setWordWrap(True)
        self.grid.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.grid.setModel(self.proxy)
        self.grid.clicked.connect(self._on_grid_click)
        outer.addWidget(self.grid, 1)

    def _section(self, title: str) -> tuple[QtWidgets.QLabel, QtWidgets.QWidget]:
        label = QtWidgets.QLabel(title)
        label.setObjectName("Section")
        host = QtWidgets.QWidget()
        row = QtWidgets.QHBoxLayout(host)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        row.addStretch(1)
        host.setFixedHeight(TILE_H + 8)
        return label, host

    def _build_chips(self) -> None:
        while self.chips_row.count():
            item = self.chips_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._chip_group = QtWidgets.QButtonGroup(self)
        self._chip_group.setExclusive(True)
        present = set()
        for app in self.model._apps:  # noqa: SLF001 (same package, read-only)
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
        chip.clicked.connect(lambda: self.proxy.set_category(category))
        self._chip_group.addButton(chip)
        self.chips_row.addWidget(chip)

    # --- data / strips ----------------------------------------------------
    def _fill_strip(self, host: QtWidgets.QWidget, apps: list[AppEntry]) -> None:
        row = host.layout()
        while row.count():
            item = row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for app in apps:
            row.addWidget(self._tile(app))
        row.addStretch(1)

    def _tile(self, app: AppEntry) -> QtWidgets.QToolButton:
        btn = QtWidgets.QToolButton()
        btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        btn.setIcon(_icon(app))
        btn.setIconSize(QtCore.QSize(ICON, ICON))
        btn.setText(app.name)
        btn.setFixedSize(TILE_W, TILE_H)
        btn.setToolTip(app.comment or app.name)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setProperty("tile", True)
        btn.clicked.connect(lambda: self._launch(app))
        return btn

    def _refresh_strips(self) -> None:
        apps = self.model._apps  # noqa: SLF001
        self._fill_strip(self.recent_strip, recommend.recently_used(apps, STRIP_N))
        self._fill_strip(self.reco_strip, recommend.recommended(apps, STRIP_N))

    # --- interaction ------------------------------------------------------
    def _on_search(self, text: str) -> None:
        self.proxy.set_query(text)
        self._set_sections_visible(not text.strip())

    def _on_order(self, label: str) -> None:
        self.proxy.set_order(
            {"Most used": "most_used", "Recently used": "recent"}.get(label, "name"))

    def _set_sections_visible(self, visible: bool) -> None:
        for w in (self.recent_label, self.recent_strip,
                  self.reco_label, self.reco_strip):
            w.setVisible(visible)

    def _on_grid_click(self, index: QtCore.QModelIndex) -> None:
        app = self.proxy.data(index, ENTRY)
        if app:
            self._launch(app)

    def _launch_first(self) -> None:
        if self.proxy.rowCount():
            app = self.proxy.data(self.proxy.index(0, 0), ENTRY)
            if app:
                self._launch(app)

    def _launch(self, app: AppEntry) -> None:
        launcher.launch(app)
        self.hide()

    # --- live updates -----------------------------------------------------
    def _schedule_reload(self, _path: str) -> None:
        self._reload_timer.start(1000)

    def _do_reload(self) -> None:
        self.model.reload()
        self._build_chips()
        self._refresh_strips()

    # --- show/hide --------------------------------------------------------
    def toggle(self) -> None:
        if self.isVisible():
            self.hide()
            return
        self.setGeometry(QtWidgets.QApplication.primaryScreen().availableGeometry())
        self.search.clear()
        self._set_sections_visible(True)
        self._refresh_strips()
        self.show()
        self.raise_()
        self.activateWindow()
        self.search.setFocus()

    def _qss(self) -> str:
        return (
            f"#MenuRoot{{background:{_C['bg']};}}"
            f"#Search{{background:{_C['surface']};color:{_C['text']};"
            f"border:none;border-radius:18px;padding:12px 18px;font-size:18px;}}"
            f"QLabel{{color:{_C['muted']};}}"
            f"QLabel#Section{{color:{_C['text']};font-size:14px;font-weight:600;}}"
            f"QComboBox{{background:{_C['surface']};color:{_C['text']};"
            f"border:none;border-radius:8px;padding:4px 10px;}}"
            f"QPushButton[chip=\"true\"]{{background:{_C['surface']};"
            f"color:{_C['muted']};border:none;border-radius:14px;padding:6px 14px;}}"
            f"QPushButton[chip=\"true\"]:checked{{background:{_C['accent']};"
            f"color:#ffffff;}}"
            f"QToolButton[tile=\"true\"]{{background:transparent;color:{_C['text']};"
            f"border:none;border-radius:10px;font-size:11px;}}"
            f"QToolButton[tile=\"true\"]:hover{{background:{_C['hover']};}}"
            f"QListView{{background:transparent;color:{_C['text']};border:none;"
            f"font-size:11px;}}"
            f"QListView::item{{border-radius:10px;padding:6px;}}"
            f"QListView::item:hover{{background:{_C['hover']};}}"
        )
