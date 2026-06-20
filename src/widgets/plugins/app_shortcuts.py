"""App Shortcuts widget — quick-launch tiles for your real apps.

No CMS and no hardcoded content: the tiles are your most-used installed apps
(from the usage log), falling back to a sensible default set on a fresh profile.
Clicking a tile launches the app via the shared run_action ("app:" handler). The
grid reflows its column count to the widget width. Themed from tokens.
"""
from __future__ import annotations

from core.qt_compat import Qt, QtCore, QtGui, QtWidgets
from apps import usage
from apps.desktop_entries import list_apps
from widgets.engine import WidgetContext, WidgetPlugin

_MAX = 8
_TILE_W = 116
_FALLBACK = (
    "firefox", "firefox-esr", "chromium", "google-chrome",
    "pcmanfm-qt", "qterminal", "featherpad", "audacious",
    "org.gnome.Calculator", "qalculate-qt", "lximage-qt", "vlc",
)


def _ranked_apps() -> list:
    apps = {a.app_id: a for a in list_apps()}
    stats = usage.stats()
    ranked = sorted(
        (a for a in apps.values()),
        key=lambda a: -int((stats.get(a.app_id) or {}).get("count", 0)))
    used = [a for a in ranked if int((stats.get(a.app_id) or {}).get("count", 0)) > 0]
    chosen = used[:_MAX]
    if len(chosen) < _MAX:
        have = {a.app_id for a in chosen}
        for cand in _FALLBACK:
            if cand in apps and cand not in have:
                chosen.append(apps[cand])
                have.add(cand)
            if len(chosen) >= _MAX:
                break
    return chosen[:_MAX]


class _AppShortcuts(QtWidgets.QFrame):
    def __init__(self, ctx: WidgetContext) -> None:
        super().__init__()
        self._ctx = ctx
        self._tiles: list[QtWidgets.QToolButton] = []
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(18, 16, 18, 16)
        outer.setSpacing(10)
        self._title = QtWidgets.QLabel()
        outer.addWidget(self._title)
        self._grid = QtWidgets.QGridLayout()
        self._grid.setSpacing(8)
        outer.addLayout(self._grid)
        outer.addStretch(1)
        self._build_tiles()
        self._apply_theme()
        ctx.theme.theme_changed.connect(self._apply_theme)

    def _build_tiles(self) -> None:
        for app in _ranked_apps():
            btn = QtWidgets.QToolButton()
            btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            icon = QtGui.QIcon.fromTheme(app.icon)
            if icon.isNull():
                icon = QtGui.QIcon.fromTheme("application-x-executable")
            btn.setIcon(icon)
            btn.setIconSize(QtCore.QSize(34, 34))
            btn.setText(app.name)
            btn.setToolTip(app.comment or app.name)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("tile", True)
            btn.setFixedHeight(78)
            btn.clicked.connect(
                lambda *_, a=app.app_id: self._ctx.run_action(f"app:{a}"))
            self._tiles.append(btn)
        self._reflow()

    def _reflow(self) -> None:
        for t in self._tiles:
            self._grid.removeWidget(t)
        cols = max(2, min(len(self._tiles), (self.width() - 36) // _TILE_W or 2))
        for i, t in enumerate(self._tiles):
            self._grid.addWidget(t, i // cols, i % cols)

    def resizeEvent(self, e) -> None:  # noqa: N802
        self._reflow()
        super().resizeEvent(e)

    def _apply_theme(self) -> None:
        t = self._ctx.theme.tokens
        self._title.setText(
            f"<span style='color:{t['accent']};'>▍</span> "
            f"<span style='color:{t['text']};font-size:15px;font-weight:700;'>"
            f"App Shortcuts</span>")


class AppShortcutsPlugin(WidgetPlugin):
    id = "app_shortcuts"
    name = "App Shortcuts"
    description = "One-tap tiles for your most-used apps."
    icon = "applications-other"
    default_size = (1, 1)
    sizes = [(1, 1), (2, 1), (2, 2)]
    category = "Productivity"

    def create_view(self, ctx: WidgetContext) -> QtWidgets.QWidget:
        return _AppShortcuts(ctx)
