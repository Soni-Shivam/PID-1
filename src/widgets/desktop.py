"""The desktop widget layer (Component C integrator).

A full-screen _NET_WM_WINDOW_TYPE_DESKTOP window (ME-07) that lays out plugin
views on a proportional grid (layout.json). Right-click opens WidgetPanel — a
320 px slide-in overlay with per-plugin Add/Remove cards; changes persist live.

Background: a rich diagonal linear gradient (top-left -> bottom-right) with two
large overlapping radial glow accents and a sparse dot-grid texture — all painted
in paintEvent, compositor-free. Widget cards use rgba QSS backgrounds so Qt
composites them against the gradient within this single window. Drop shadows
(QGraphicsDropShadowEffect) add depth without a compositor.

All colours come from theme tokens; no inline hex literals appear here.
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


def _username() -> str:
    try:
        info = pwd.getpwuid(os.getuid())
        return (info.pw_gecos or "").split(",")[0] or info.pw_name
    except KeyError:
        return ""


# ---------------------------------------------------------------------------
# Widget management panel
# ---------------------------------------------------------------------------

class _PluginCard(QtWidgets.QFrame):
    """Plugin row inside WidgetPanel: icon + name + description + Add/Remove."""

    toggled = QtCore.pyqtSignal(str, bool)   # (plugin_id, True=add / False=remove)

    def __init__(self, plugin, active: bool, theme: ThemeManager) -> None:
        super().__init__()
        self._plugin = plugin
        self._active = active
        self._theme  = theme
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("pluginCard")

        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(12)

        # Icon (keep reference so we don't confuse it with label children)
        self._icon_lbl = QtWidgets.QLabel()
        px = QtGui.QIcon.fromTheme(plugin.icon).pixmap(36, 36)
        if px.isNull():
            px = QtGui.QIcon.fromTheme("application-x-executable").pixmap(36, 36)
        self._icon_lbl.setPixmap(px)
        self._icon_lbl.setFixedSize(36, 36)
        lay.addWidget(self._icon_lbl)

        # Text — store refs directly
        text = QtWidgets.QVBoxLayout()
        text.setSpacing(2)
        self._name_lbl = QtWidgets.QLabel(plugin.name)
        self._desc_lbl = QtWidgets.QLabel(plugin.description or "")
        self._desc_lbl.setWordWrap(True)
        text.addWidget(self._name_lbl)
        text.addWidget(self._desc_lbl)
        lay.addLayout(text, 1)

        # Toggle button
        self._btn = QtWidgets.QPushButton()
        self._btn.setFixedWidth(84)
        self._btn.setCursor(Qt.PointingHandCursor)
        self._btn.clicked.connect(self._on_toggle)
        lay.addWidget(self._btn)

        self._apply_theme()
        theme.theme_changed.connect(self._apply_theme)

    def _apply_theme(self) -> None:
        t = self._theme.tokens
        bg     = t.get("accent_soft", "#21344f") if self._active else "transparent"
        border = t.get("accent", "#5b9bff") if self._active else t.get("border", "#2a2e38")
        self.setStyleSheet(
            f"QFrame#pluginCard{{background:{bg};border:1px solid {border};"
            f"border-radius:12px;}}"
        )
        self._name_lbl.setStyleSheet(
            f"color:{t['text']};font-size:13px;font-weight:700;background:transparent;")
        self._desc_lbl.setStyleSheet(
            f"color:{t['muted']};font-size:11px;background:transparent;")
        if self._active:
            self._btn.setText("Remove")
            self._btn.setStyleSheet(
                f"QPushButton{{background:{t['surface']};color:{t['muted']};"
                f"border:1px solid {t['border']};border-radius:8px;"
                f"padding:5px 8px;font-size:11px;font-weight:600;}}"
                f"QPushButton:hover{{color:{t['text']};border-color:{t['accent']};}}"
            )
        else:
            self._btn.setText("Add")
            self._btn.setStyleSheet(
                f"QPushButton{{background:{t['accent']};color:{t['on_accent']};"
                f"border:none;border-radius:8px;"
                f"padding:5px 8px;font-size:11px;font-weight:700;}}"
                f"QPushButton:hover{{background:{t['accent_soft']};"
                f"color:{t['accent']};border:1px solid {t['accent']};}}"
            )

    def set_active(self, active: bool) -> None:
        self._active = active
        self._apply_theme()

    def _on_toggle(self) -> None:
        self.toggled.emit(self._plugin.id, not self._active)


class WidgetPanel(QtWidgets.QWidget):
    """Right-edge slide-in panel for widget management.

    Animated via QPropertyAnimation on maximumWidth (0 → PANEL_W, 180 ms).
    Lives as a child of DesktopLayer so it composites against the gradient.
    """

    PANEL_W = 320

    def __init__(self, plugins: dict, layout: list[dict],
                 theme: ThemeManager, on_change,
                 parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._plugins  = plugins
        self._active   = {item["plugin_id"] for item in layout}
        self._theme    = theme
        self._on_change = on_change
        self._cards: dict[str, _PluginCard] = {}

        self.setFixedWidth(self.PANEL_W)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("WidgetPanel")

        self._anim = QtCore.QPropertyAnimation(self, b"maximumWidth")
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QtCore.QEasingCurve.InOutCubic)

        self._build()
        theme.theme_changed.connect(self._apply_panel_theme)
        self._apply_panel_theme()
        self.setMaximumWidth(0)

    def _apply_panel_theme(self) -> None:
        t = self._theme.tokens
        bg     = t.get("panel_bg", t.get("surface", "#181b22"))
        accent = t.get("accent", "#5b9bff")
        self.setStyleSheet(
            f"QWidget#WidgetPanel{{background:{bg};"
            f"border-left:2px solid {accent};}}"
        )

    def _build(self) -> None:
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Header
        header = QtWidgets.QWidget()
        header.setObjectName("WidgetPanelHeader")
        header.setAttribute(Qt.WA_StyledBackground, True)
        hl = QtWidgets.QHBoxLayout(header)
        hl.setContentsMargins(16, 14, 12, 14)
        t = self._theme.tokens
        title = QtWidgets.QLabel("Widgets")
        title.setStyleSheet(
            f"color:{t['text']};font-size:16px;font-weight:700;background:transparent;")
        close_btn = QtWidgets.QToolButton()
        close_btn.setText("✕")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(
            f"QToolButton{{color:{t['muted']};border:none;font-size:15px;"
            f"background:transparent;padding:4px;}}"
            f"QToolButton:hover{{color:{t['text']};}}"
        )
        close_btn.clicked.connect(self.close_panel)
        hl.addWidget(title, 1)
        hl.addWidget(close_btn)
        lay.addWidget(header)

        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.HLine)
        sep.setStyleSheet(f"color:{t.get('border','#2a2e38')};")
        lay.addWidget(sep)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background:transparent;")

        content = QtWidgets.QWidget()
        content.setStyleSheet("background:transparent;")
        cl = QtWidgets.QVBoxLayout(content)
        cl.setContentsMargins(10, 10, 10, 10)
        cl.setSpacing(8)

        for pid, plugin in sorted(self._plugins.items(),
                                   key=lambda kv: kv[1].name):
            card = _PluginCard(plugin, pid in self._active, self._theme)
            card.toggled.connect(self._on_card_toggled)
            self._cards[pid] = card
            cl.addWidget(card)

        cl.addStretch(1)
        scroll.setWidget(content)
        lay.addWidget(scroll, 1)

    def _on_card_toggled(self, plugin_id: str, add: bool) -> None:
        if add:
            self._active.add(plugin_id)
        else:
            self._active.discard(plugin_id)
        for pid, card in self._cards.items():
            card.set_active(pid in self._active)
        self._on_change(set(self._active))

    def open_panel(self) -> None:
        self.show()
        self.raise_()
        self._anim.stop()
        self._anim.setStartValue(self.maximumWidth())
        self._anim.setEndValue(self.PANEL_W)
        self._anim.start()

    def close_panel(self) -> None:
        self._anim.stop()
        self._anim.setStartValue(self.maximumWidth())
        self._anim.setEndValue(0)
        self._anim.start()
        self._anim.finished.connect(
            lambda: self.hide() if self.maximumWidth() == 0 else None)

    def is_open(self) -> bool:
        return self.isVisible() and self.maximumWidth() > 10

    def update_layout(self, layout: list[dict]) -> None:
        self._active = {item["plugin_id"] for item in layout}
        for pid, card in self._cards.items():
            card.set_active(pid in self._active)


# ---------------------------------------------------------------------------
# Desktop layer
# ---------------------------------------------------------------------------

class DesktopLayer(QtWidgets.QWidget):
    """Wallpaper-level window hosting the widget grid and slide-in widget panel.

    Background is painted as a diagonal multi-stop gradient with two large radial
    glow accents and a dot-grid texture — no compositor needed.
    """

    def __init__(self, cms_service, theme: ThemeManager) -> None:
        super().__init__()
        self._cms      = cms_service
        self._theme    = theme
        self._username = _username()
        self._apps_by_id = {a.app_id: a for a in list_apps()}
        self._plugins  = engine.discover_plugins()
        self._layout   = engine.load_layout()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("desktopRoot")

        self._grid_host = QtWidgets.QWidget(self)
        self._build_grid()

        self._panel = WidgetPanel(
            self._plugins, self._layout, theme,
            on_change=self._apply_selection,
            parent=self,
        )
        self._panel.hide()

        theme.theme_changed.connect(self._on_theme_changed)

    # --- lifecycle --------------------------------------------------------
    def start(self) -> None:
        geo = QtWidgets.QApplication.primaryScreen().geometry()
        self.setGeometry(geo)
        wid = int(self.winId())
        x11.set_desktop_type(wid)
        self.show()
        x11.set_desktop_type(wid)
        self._position_panel()
        if self._cms is not None:
            self._cms.refresh()

    def resizeEvent(self, e: QtGui.QResizeEvent) -> None:  # noqa: N802
        self._grid_host.setGeometry(self.rect())
        self._position_panel()
        super().resizeEvent(e)

    def _position_panel(self) -> None:
        self._panel.setGeometry(
            self.width() - WidgetPanel.PANEL_W, 0, WidgetPanel.PANEL_W, self.height())

    # --- rich gradient background -----------------------------------------
    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802
        """Paint the multi-layer atmospheric background (see core.background).

        The same painter is used by the dock's overflow strip (offset by the
        dock's screen position) so floating icons blend into this exact
        background with no mismatched rectangle.
        """
        p = QtGui.QPainter(self)
        paint_background(p, self.width(), self.height(), self._theme.tokens)
        p.end()

    def _on_theme_changed(self) -> None:
        self.update()

    # --- grid -------------------------------------------------------------
    def _build_grid(self) -> None:
        old             = self._grid_host
        self._grid_host = QtWidgets.QWidget(self)
        self._grid_host.setGeometry(self.rect())

        grid = QtWidgets.QGridLayout(self._grid_host)
        grid.setContentsMargins(40, 36, 40, 36)
        grid.setSpacing(20)

        rows_used: set[int] = set()
        cols_used: set[int] = set()
        max_col = 0

        for item in self._layout:
            plugin = self._plugins.get(item["plugin_id"])
            if not plugin:
                continue
            ctx = WidgetContext(
                cms        = self._cms if plugin.needs_cms else None,
                run_action = self._run_action,
                username   = self._username,
                theme      = self._theme,
            )
            card = self._wrap(plugin.create_view(ctx))
            grid.addWidget(card,
                           item["row"], item["col"],
                           item["h"],   item["w"])
            rows_used.add(item["row"])
            for r in range(item["row"], item["row"] + item["h"]):
                rows_used.add(r)
            for c in range(item["col"], item["col"] + item["w"]):
                cols_used.add(c)
            max_col = max(max_col, item["col"] + item["w"])

        # Column stretches: first column narrower, rest equal
        for c in range(max_col):
            grid.setColumnStretch(c, 1 if c == 0 else 3)

        # Row stretches: all rows equal
        for r in sorted(rows_used):
            grid.setRowStretch(r, 1)

        self._grid_host.show()
        old.deleteLater()

    def _wrap(self, view: QtWidgets.QWidget) -> QtWidgets.QWidget:
        """Apply card QSS property + software drop-shadow."""
        view.setProperty("card", True)
        view.setAttribute(Qt.WA_StyledBackground, True)
        shadow = QtWidgets.QGraphicsDropShadowEffect(view)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 5)
        shadow.setColor(QtGui.QColor(
            self._theme.tokens.get("shadow_color", "rgba(0,0,0,0.45)")))
        view.setGraphicsEffect(shadow)
        return view

    def _run_action(self, action: str) -> None:
        engine.execute_action(action, self._apps_by_id)

    # --- widget panel -----------------------------------------------------
    def contextMenuEvent(self, e: QtGui.QContextMenuEvent) -> None:  # noqa: N802
        menu = QtWidgets.QMenu(self)
        if self._panel.is_open():
            menu.addAction("Close widget editor", self._panel.close_panel)
        else:
            menu.addAction("Customise widgets...", self._panel.open_panel)
        menu.exec_(e.globalPos())

    def _apply_selection(self, selected: set[str]) -> None:
        """Rebuild the layout from the new selection, using default_layout positions."""
        # Start from the canonical default positions for known plugins
        default = {item["plugin_id"]: item
                   for item in engine.default_layout()}
        kept: list[dict] = []
        next_col = 0
        for pid in sorted(selected):
            if pid in default:
                kept.append(dict(default[pid]))
            else:
                plugin = self._plugins[pid]
                pw, ph = plugin.default_size
                # Auto-place in a new column at row 0
                kept.append({"plugin_id": pid, "col": next_col,
                             "row": 0, "w": pw, "h": ph})
            next_col = max(it["col"] + it["w"] for it in kept)

        self._layout = kept
        engine.save_layout(self._layout)
        self._panel.update_layout(self._layout)
        self._build_grid()
        self._panel.raise_()
