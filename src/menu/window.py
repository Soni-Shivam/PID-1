"""The application menu window (Component B).

A frameless launcher sized to the work area (so the dock stays visible beneath
it). Layout follows the reference: a left category sidebar (vertical), a big
search field on top of the main column, and the app tiles inside a rounded glass
panel that scrolls — Recently used, Recommended and All apps in one flow.

Search hides the strips and shows only All Apps, and is fuzzy (subsequence). Esc
or the top-right close button hides it. Built lazily on first open, reused after;
live-updates via QFileSystemWatcher.

Chrome themed by the app-wide stylesheet (#MenuRoot / #MenuSidebar / #MenuPanel /
#MenuNavItem / #Search / [tile] / #Section). Tile colours come from tokens, not
inline CSS, so light and dark both work.
"""
from __future__ import annotations

from core import user
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
TILE_W = 104
TILE_H = 92
GRID_COLS = 6     # columns in the all-apps grid
STRIP_N = 6       # max items in recent/recommended rows
SIDEBAR_W = 224


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
    # clicked() emits a `checked` bool; swallow it so it can't be passed into
    # the callback's bound AppEntry argument (that turned `app` into a bool and
    # broke launching).
    btn.clicked.connect(lambda *_: launch_cb())
    return btn


class _TileGrid(QtWidgets.QWidget):
    """A fixed-column grid of app tiles (no QListView; lives in a QScrollArea)."""

    def __init__(self, cols: int = GRID_COLS) -> None:
        super().__init__()
        self.setStyleSheet("background:transparent;")
        self._cols = cols
        self._grid = QtWidgets.QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(6)
        for c in range(cols):
            self._grid.setColumnMinimumWidth(c, TILE_W)

    def set_tiles(self, tiles: list[QtWidgets.QWidget]) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for i, t in enumerate(tiles):
            self._grid.addWidget(t, i // self._cols, i % self._cols)
        remainder = len(tiles) % self._cols
        if remainder:
            for i in range(self._cols - remainder):
                spacer = QtWidgets.QWidget()
                spacer.setFixedSize(TILE_W, TILE_H)
                self._grid.addWidget(spacer, len(tiles) // self._cols,
                                     remainder + i)


class MenuWindow(QtWidgets.QWidget):
    """Lazily-built, reusable application launcher with a category sidebar."""

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
        shell = QtWidgets.QVBoxLayout(self)
        shell.setContentsMargins(0, 0, 0, 0)
        self._body = QtWidgets.QWidget()
        self._body.setObjectName("MenuBody")
        shell.addWidget(self._body)

        outer = QtWidgets.QVBoxLayout(self._body)
        outer.setContentsMargins(40, 28, 40, 28)
        outer.setSpacing(16)

        # --- Header: greeting + close ---
        self._greeting = QtWidgets.QLabel()
        self._greeting.setObjectName("Greeting")
        self._greeting_sub = QtWidgets.QLabel("What would you like to open?")
        self._greeting_sub.setObjectName("GreetingSub")
        head = QtWidgets.QHBoxLayout()
        gcol = QtWidgets.QVBoxLayout()
        gcol.setSpacing(2)
        gcol.addWidget(self._greeting)
        gcol.addWidget(self._greeting_sub)
        head.addLayout(gcol, 1)
        close_btn = QtWidgets.QToolButton()
        close_btn.setText("✕")
        close_btn.setObjectName("MenuClose")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setToolTip("Close (Esc)")
        close_btn.setFixedSize(40, 40)
        close_btn.clicked.connect(self.hide)
        head.addWidget(close_btn, 0, Qt.AlignTop)
        outer.addLayout(head)

        # --- Body: sidebar + main ---
        body = QtWidgets.QHBoxLayout()
        body.setSpacing(20)

        sidebar = QtWidgets.QWidget()
        sidebar.setObjectName("MenuSidebar")
        sidebar.setAttribute(Qt.WA_StyledBackground, True)
        sidebar.setFixedWidth(SIDEBAR_W)
        sb = QtWidgets.QVBoxLayout(sidebar)
        sb.setContentsMargins(12, 16, 12, 16)
        sb.setSpacing(4)
        cats_title = QtWidgets.QLabel("Categories")
        cats_title.setObjectName("Section")
        sb.addWidget(cats_title)
        sb.addSpacing(4)
        self._cat_col = QtWidgets.QVBoxLayout()
        self._cat_col.setSpacing(3)
        sb.addLayout(self._cat_col)
        sb.addStretch(1)
        sort_lbl = QtWidgets.QLabel("Sort by")
        sort_lbl.setObjectName("Section")
        sb.addWidget(sort_lbl)
        self.order = QtWidgets.QComboBox()
        self.order.addItems(["Name", "Most used", "Recently used"])
        self.order.currentTextChanged.connect(self._on_order)
        sb.addWidget(self.order)
        settings_btn = QtWidgets.QPushButton("  Settings")
        settings_btn.setIcon(QtGui.QIcon.fromTheme("configure"))
        settings_btn.setCursor(Qt.PointingHandCursor)
        settings_btn.clicked.connect(self._open_settings)
        sb.addWidget(settings_btn)
        body.addWidget(sidebar)

        # main column: search + scrollable glass panel of tiles
        main = QtWidgets.QVBoxLayout()
        main.setSpacing(14)
        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText("Search apps")
        self.search.setClearButtonEnabled(True)
        self.search.setObjectName("Search")
        self.search.textChanged.connect(self._on_search)
        self.search.returnPressed.connect(self._launch_first)
        main.addWidget(self.search)

        self._scroll = QtWidgets.QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("background:transparent;")
        self._content = QtWidgets.QWidget()
        self._content.setObjectName("MenuPanel")
        self._content.setAttribute(Qt.WA_StyledBackground, True)
        self._content_lay = QtWidgets.QVBoxLayout(self._content)
        self._content_lay.setContentsMargins(22, 20, 22, 26)
        self._content_lay.setSpacing(8)

        self._recent_label = self._section_label("Recently used")
        self._recent_grid = _TileGrid(cols=STRIP_N)
        self._content_lay.addWidget(self._recent_label)
        self._content_lay.addWidget(self._recent_grid)
        self._reco_label = self._section_label("Recommended")
        self._reco_grid = _TileGrid(cols=STRIP_N)
        self._content_lay.addWidget(self._reco_label)
        self._content_lay.addWidget(self._reco_grid)
        self._all_label = self._section_label("All apps")
        self._all_grid = _TileGrid(cols=GRID_COLS)
        self._content_lay.addWidget(self._all_label)
        self._content_lay.addWidget(self._all_grid)
        self._content_lay.addStretch(1)
        self._scroll.setWidget(self._content)
        main.addWidget(self._scroll, 1)
        body.addLayout(main, 1)
        outer.addLayout(body, 1)

    def _section_label(self, text: str) -> QtWidgets.QLabel:
        lbl = QtWidgets.QLabel(text)
        lbl.setObjectName("Section")
        return lbl

    def _build_chips(self) -> None:
        """(Re)build the vertical category list in the sidebar."""
        while self._cat_col.count():
            item = self._cat_col.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._chip_group = QtWidgets.QButtonGroup(self)
        self._chip_group.setExclusive(True)
        present = set()
        for app in self.model._apps:  # noqa: SLF001
            present.update(app.categories)
        self._add_chip("All apps", "", checked=True)
        for cat, label in _CATEGORIES:
            if cat in present:
                self._add_chip(label, cat)

    def _add_chip(self, label: str, category: str, checked: bool = False) -> None:
        chip = QtWidgets.QPushButton(label)
        chip.setCheckable(True)
        chip.setChecked(checked)
        chip.setCursor(Qt.PointingHandCursor)
        chip.setObjectName("MenuNavItem")
        chip.clicked.connect(lambda: self._on_chip(category))
        self._chip_group.addButton(chip)
        self._cat_col.addWidget(chip)

    def _on_chip(self, category: str) -> None:
        self.proxy.set_category(category)
        self._rebuild_all_grid()

    # --- data filling -----------------------------------------------------
    def _fill_strip(self, grid: _TileGrid, apps: list[AppEntry]) -> None:
        tiles = [_tile(a, lambda a=a: self._launch(a)) for a in apps]
        grid.set_tiles(tiles)

    def _app_at(self, proxy_row: int) -> AppEntry | None:
        src = self.proxy.mapToSource(self.proxy.index(proxy_row, 0))
        return self.model.data(src, ENTRY) if src.isValid() else None

    def _rebuild_all_grid(self) -> None:
        apps = [a for row in range(self.proxy.rowCount())
                if (a := self._app_at(row)) is not None]
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
        self._all_label.setText("Results" if searching else "All apps")
        self._rebuild_all_grid()

    def _on_order(self, label: str) -> None:
        self.proxy.set_order(
            {"Most used": "most_used", "Recently used": "recent"}.get(label, "name"))
        self._rebuild_all_grid()

    def _launch_first(self) -> None:
        if self.proxy.rowCount():
            app = self._app_at(0)
            if app:
                self._launch(app)

    def _launch(self, app: AppEntry) -> None:
        launcher.launch(app)
        self.hide()

    def _open_settings(self) -> None:
        SettingsDialog(self._theme, self).exec_()

    def _refresh_greeting(self) -> None:
        self._greeting.setText(f"{user.salutation()}, {user.first_name()}")

    def _play_entrance(self) -> None:
        """One-shot fade + rise on open (compositor-free, < 250 ms, removed on
        finish so it adds no idle cost)."""
        effect = QtWidgets.QGraphicsOpacityEffect(self._body)
        self._body.setGraphicsEffect(effect)
        home = self._body.pos()

        fade = QtCore.QPropertyAnimation(effect, b"opacity", self)
        fade.setDuration(180)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QtCore.QEasingCurve.OutCubic)

        rise = QtCore.QPropertyAnimation(self._body, b"pos", self)
        rise.setDuration(240)
        rise.setStartValue(home + QtCore.QPoint(0, 26))
        rise.setEndValue(home)
        rise.setEasingCurve(QtCore.QEasingCurve.OutCubic)

        group = QtCore.QParallelAnimationGroup(self)
        group.addAnimation(fade)
        group.addAnimation(rise)

        def _settle() -> None:
            self._body.setGraphicsEffect(None)
            self._body.move(home)

        group.finished.connect(_settle)
        self._entrance = group
        group.start(QtCore.QAbstractAnimation.DeleteWhenStopped)

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
        self._all_label.setText("All apps")
        self._refresh_greeting()
        self._refresh_strips()
        self._rebuild_all_grid()
        self._scroll.verticalScrollBar().setValue(0)
        self.show()
        self.raise_()
        self.activateWindow()
        self.search.setFocus()
        self._play_entrance()
