"""The visible dock: a bottom-anchored bar of app icons.

Builds icon buttons from DockModel (pinned + running-unpinned), single-click to
launch-or-focus, right-click for pin/unpin/reorder, running indicator dots, and
a grid button that will open the application menu (Phase B). Uses core.x11 for
dock type + strut (verified ME-02), activate_window (ME-06), and a
ClientListWatcher (ME-05) for running state. No polling.

Window/button chrome is themed by the app-wide stylesheet (themes/base.qss.tmpl
keyed on #DockRoot / #DockGrid / [dockbtn]); the running-indicator dot is
custom-painted, so it reads its colour from the live theme tokens (Phase D).
"""
from __future__ import annotations

from core.qt_compat import Qt, QtCore, QtGui, QtWidgets
from core import x11
from core.theme import ThemeManager
from apps import launcher
from dock.model import DockModel

ICON_SIZE = 40
BTN = 56
PAD = 8
GAP = 8
RADIUS = 14
DOT = 5


class DockButton(QtWidgets.QToolButton):
    """One dock entry: an app icon with a running-indicator dot."""

    activated = QtCore.pyqtSignal(str)         # left click -> app_id
    context = QtCore.pyqtSignal(str, QtCore.QPoint)

    def __init__(self, app_id: str, name: str, icon: QtGui.QIcon,
                 theme: ThemeManager) -> None:
        super().__init__()
        self.app_id = app_id
        self._theme = theme
        self._running = False
        self.setIcon(icon)
        self.setIconSize(QtCore.QSize(ICON_SIZE, ICON_SIZE))
        self.setFixedSize(BTN, BTN)
        self.setToolTip(name)
        self.setAutoRaise(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("dockbtn", True)  # styled by app-wide stylesheet
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.clicked.connect(lambda: self.activated.emit(self.app_id))
        self.customContextMenuRequested.connect(
            lambda pos: self.context.emit(self.app_id, self.mapToGlobal(pos)))

    def set_running(self, running: bool) -> None:
        if running != self._running:
            self._running = running
            self.update()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802
        super().paintEvent(event)
        if not self._running:
            return
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setBrush(QtGui.QColor(self._theme.tokens["indicator"]))
        p.setPen(Qt.NoPen)
        x = (self.width() - DOT) // 2
        p.drawEllipse(x, self.height() - DOT - 3, DOT, DOT)


class DockWindow(QtWidgets.QWidget):
    """Frameless bottom dock window holding the icon buttons."""

    menu_requested = QtCore.pyqtSignal()

    def __init__(self, theme: ThemeManager,
                 model: DockModel | None = None) -> None:
        super().__init__()
        self._theme = theme
        self.model = model or DockModel()
        self._buttons: dict[str, DockButton] = {}
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
                            | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("DockRoot")  # background from app-wide stylesheet
        theme.theme_changed.connect(self._on_theme_changed)

        self._row = QtWidgets.QHBoxLayout(self)
        self._row.setContentsMargins(PAD, PAD, PAD, PAD)
        self._row.setSpacing(6)

        self._watcher = x11.ClientListWatcher()
        self._watcher.window_added.connect(self._on_window_added)
        self._watcher.window_removed.connect(self._on_window_removed)

        self._build()

    # --- lifecycle --------------------------------------------------------
    def start(self) -> None:
        """Realize as a dock, show, set strut, begin watching windows."""
        wid = int(self.winId())          # realize native window (not yet mapped)
        x11.set_dock_type(wid)           # set DOCK type before map (ME-02)
        self.show()
        QtCore.QTimer.singleShot(0, self._apply_dock_geometry)
        self._watcher.start()

    def stop(self) -> None:
        """Stop the window-tracking thread (called on app quit; D4)."""
        self._watcher.stop()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: N802
        self.stop()
        super().closeEvent(event)

    def _on_theme_changed(self) -> None:
        # The app stylesheet re-themes chrome; repaint the custom-painted dots.
        for btn in self._buttons.values():
            btn.update()

    # --- building ---------------------------------------------------------
    def _build(self) -> None:
        while self._row.count():
            item = self._row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._buttons.clear()

        style = self.style()
        for app_id in self.model.visible_items():
            app = self.model.app(app_id)
            if not app:
                continue
            icon = QtGui.QIcon.fromTheme(app.icon)
            if icon.isNull():
                icon = style.standardIcon(QtWidgets.QStyle.SP_FileIcon)
            btn = DockButton(app_id, app.name, icon, self._theme)
            btn.set_running(self.model.is_running(app_id))
            btn.activated.connect(self._on_activated)
            btn.context.connect(self._show_menu)
            self._row.addWidget(btn)
            self._buttons[app_id] = btn

        self._add_grid_button()
        self.adjustSize()
        if self.isVisible():
            QtCore.QTimer.singleShot(0, self._apply_dock_geometry)

    def _add_grid_button(self) -> None:
        grid = QtWidgets.QToolButton()
        grid.setText("☰")  # menu glyph
        grid.setObjectName("DockGrid")  # styled by app-wide stylesheet
        grid.setFixedSize(BTN, BTN)
        grid.setCursor(Qt.PointingHandCursor)
        grid.setToolTip("Applications")
        grid.clicked.connect(self.menu_requested.emit)
        self._row.addWidget(grid)

    def _apply_dock_geometry(self) -> None:
        screen = QtWidgets.QApplication.primaryScreen().geometry()
        w, h = self.width(), self.height()
        x = screen.x() + (screen.width() - w) // 2
        y = screen.y() + screen.height() - h - GAP
        self.move(x, y)
        # Rounded corners via mask (no compositor).
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(0, 0, w, h), RADIUS, RADIUS)
        self.setMask(QtGui.QRegion(path.toFillPolygon().toPolygon()))
        wid = int(self.winId())
        x11.set_dock_type(wid)                      # re-assert after map
        x11.set_bottom_strut(wid, h + GAP, x, x + w - 1)

    # --- interaction ------------------------------------------------------
    def _on_activated(self, app_id: str) -> None:
        wins = self.model.windows(app_id)
        if wins:
            x11.activate_window(wins[-1])
        else:
            app = self.model.app(app_id)
            if app:
                launcher.launch(app)

    def _show_menu(self, app_id: str, global_pos: QtCore.QPoint) -> None:
        menu = QtWidgets.QMenu()
        app = self.model.app(app_id)
        if app:
            menu.addAction("Open new window",
                           lambda: launcher.launch(app))
            menu.addSeparator()
        if self.model.is_pinned(app_id):
            menu.addAction("Move left", lambda: self._move(app_id, -1))
            menu.addAction("Move right", lambda: self._move(app_id, +1))
            menu.addAction("Unpin from dock", lambda: self._unpin(app_id))
        else:
            menu.addAction("Pin to dock", lambda: self._pin(app_id))
        menu.exec_(global_pos)

    def _pin(self, app_id: str) -> None:
        self.model.pin(app_id)
        self._build()

    def _unpin(self, app_id: str) -> None:
        self.model.unpin(app_id)
        self._build()

    def _move(self, app_id: str, delta: int) -> None:
        self.model.move(app_id, delta)
        self._build()

    # --- running state (event-driven) ------------------------------------
    def _on_window_added(self, wm_class: str, win_id: int) -> None:
        app_id = self.model.add_window(wm_class, win_id)
        if not app_id:
            return
        if app_id in self._buttons:
            self._buttons[app_id].set_running(True)
        else:
            self._build()  # a running-but-unpinned app appeared

    def _on_window_removed(self, win_id: int) -> None:
        app_id = self.model.remove_window(win_id)
        if not app_id:
            return
        still = self.model.is_running(app_id)
        if app_id in self._buttons:
            if not still and not self.model.is_pinned(app_id):
                self._build()  # drop a running-unpinned icon that closed
            else:
                self._buttons[app_id].set_running(still)
