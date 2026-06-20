import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src")))
from core.qt_compat import QtCore, QtGui, QtWidgets

from utils import MODERN_FONT_STACK, get_icon
from state import DashboardState
from grid_manager import SnapGridManager, SlotSize, BG_DEEP
from vertical_dock import VerticalDockWidget
from library import WidgetManagerPanel
from app_launcher import AppLibraryPanel

from widgets import (
    FocusTimerWidget,
    WeatherWidget,
    MusicPlayerWidget,
    CalendarWidget,
    ActivityGraphWidget,
    SystemHealthWidget,
    TopHeadlinesWidget,
    FinanceWidget,
    SocialUpdatesWidget,
    HeroLearningWidget,
    ExploreGridWidget,
    HeroCarouselWidget,
    JiopcAssistantWidget,
)


def _make_factory(state: DashboardState):
    """Returns a factory(w_id, size) -> BaseWidgetCard callable."""
    mapping = {
        "focus":    lambda s: FocusTimerWidget(state, s),
        "weather":  lambda s: WeatherWidget(state, s),
        "music":    lambda s: MusicPlayerWidget(state, s),
        "calendar": lambda s: CalendarWidget(state, s),
        "activity": lambda s: ActivityGraphWidget(state, s),
        "sys":      lambda s: SystemHealthWidget(state, s),
        "headlines":lambda s: TopHeadlinesWidget(state, s),
        "finance":  lambda s: FinanceWidget(state, s),
        "social":   lambda s: SocialUpdatesWidget(state, s),
        "hero_learn":lambda s: HeroLearningWidget(state, s),
        "explore":  lambda s: ExploreGridWidget(state, s),
        "hero":     lambda s: HeroCarouselWidget(state, s),
        "assistant":lambda s: JiopcAssistantWidget(state, s),
    }

    def factory(w_id: str, size: SlotSize):
        fn = mapping.get(w_id)
        return fn(size) if fn else None

    return factory


class DesktopDashboard(QtWidgets.QWidget):
    def __init__(self, state: DashboardState):
        super().__init__()
        self.state   = state
        self.factory = _make_factory(state)

        self.setWindowTitle("JioPC – Discover Desktop")

        screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
        self.setGeometry(screen)
        self.setStyleSheet(f"DesktopDashboard {{ background: {BG_DEEP}; }}"
                           f"* {{ font-family: {MODERN_FONT_STACK}; }}")

        self._build_ui()
        self.state.time_updated.connect(self._on_time)
        self.state.on_tick()

    # ── background atmosphere ────────────────────────────────────────────────
    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.fillRect(self.rect(), QtGui.QColor(BG_DEEP))
        w, h = self.width(), self.height()
        for cx, cy, rad, r, g, b, a in [
            (0.10, 0.00, 0.80, 80,  30, 140, 32),
            (0.90, 0.20, 0.70, 20,  70, 180, 25),
            (0.50, 1.00, 0.60, 160, 30,  90, 18),
        ]:
            gr = QtGui.QRadialGradient(w*cx, h*cy, h*rad)
            gr.setColorAt(0, QtGui.QColor(r, g, b, a))
            gr.setColorAt(1, QtGui.QColor(0, 0, 0, 0))
            p.fillRect(self.rect(), gr)

    # ── header ───────────────────────────────────────────────────────────────
    def _on_time(self, greeting, time_str, date_str):
        self._lbl_greeting.setText(f"{greeting}, Rakesh")
        self._lbl_sub.setText(f"{time_str}  •  {date_str}")

    # ── build ────────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Vertical dock
        dock_icons = [
            {"name": "Home",      "bg": "#E4E4E7", "fg": "#000", "emoji": "🏠"},
            {"name": "App Store", "bg": "#1E88E5", "fg": "#FFF", "emoji": "⊞"},
            {"name": "Settings",  "bg": "#8E8E93", "fg": "#FFF", "emoji": "⚙"},
            {"name": "Chrome",    "bg": "#EA4335", "fg": "#FFF", "emoji": "C"},
            {"name": "YouTube",   "bg": "#FF0000", "fg": "#FFF", "emoji": "▶"},
            {"name": "Spotify",   "bg": "#1DB954", "fg": "#FFF", "emoji": "🎵"}
        ]
        dock = VerticalDockWidget(dock_icons)
        dock.icon_clicked.connect(self._on_dock_click)
        root.addWidget(dock)

        # Central Stacked Widget
        self._main_stack = QtWidgets.QStackedWidget()
        self._main_stack.setStyleSheet("background: transparent;")
        root.addWidget(self._main_stack, 1)

        # ── Page 0: Home Screen ──────────────────────────────────────────────
        home_page = QtWidgets.QWidget()
        home_page.setStyleSheet("background: transparent;")
        right = QtWidgets.QVBoxLayout(home_page)
        right.setContentsMargins(16, 24, 16, 24)
        right.setSpacing(18)

        # Header
        hdr = QtWidgets.QHBoxLayout()
        vcol = QtWidgets.QVBoxLayout()
        vcol.setSpacing(3)
        self._lbl_greeting = QtWidgets.QLabel("Good morning, Rakesh")
        self._lbl_greeting.setStyleSheet(
            "color:#FFFFFF; font-size:32px; font-weight:700; background:transparent;")
        self._lbl_sub = QtWidgets.QLabel()
        self._lbl_sub.setStyleSheet(
            "color:#52525B; font-size:15px; font-weight:400; background:transparent;")
        vcol.addWidget(self._lbl_greeting)
        vcol.addWidget(self._lbl_sub)
        hdr.addLayout(vcol)
        hdr.addStretch()

        # Slot counter badge (live)
        self._slot_badge = QtWidgets.QLabel("0 / 6 slots")
        self._slot_badge.setFixedHeight(36)
        self._slot_badge.setAlignment(QtCore.Qt.AlignCenter)
        self._slot_badge.setStyleSheet("""
            QLabel {
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 18px;
                color: #A1A1AA;
                font-size: 13px;
                font-weight: 500;
                padding: 0 18px;
            }
        """)

        # Widget Library button
        btn_lib = QtWidgets.QPushButton("⊞  Widget Store")
        btn_lib.setFixedHeight(36)
        btn_lib.setCursor(QtCore.Qt.PointingHandCursor)
        btn_lib.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.08);
                color: #FFFFFF;
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 18px;
                padding: 0 18px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover  { background: rgba(255,255,255,0.15); }
            QPushButton:pressed{ background: rgba(255,255,255,0.05); }
        """)
        btn_lib.clicked.connect(self._open_store)

        hdr.addWidget(self._slot_badge)
        hdr.addSpacing(10)
        hdr.addWidget(btn_lib)
        right.addLayout(hdr)

        # SnapGridManager (3 cols × 2 rows = 6 slots)
        self.grid = SnapGridManager()
        self.grid.capacity_changed.connect(self._on_capacity)
        right.addWidget(self.grid, 1)

        self._main_stack.addWidget(home_page)

        # ── Page 1: App Library ──────────────────────────────────────────────
        self.app_lib_panel = AppLibraryPanel(self)
        self._main_stack.addWidget(self.app_lib_panel)

        # ── Page 2: Widget Store ─────────────────────────────────────────────
        self.widget_store_panel = WidgetManagerPanel(self.grid, self.factory, self)
        self._main_stack.addWidget(self.widget_store_panel)

        # Defer widget population until the window is visible & sized
        QtCore.QTimer.singleShot(0, self._populate)

    def _populate(self):
        loaded = self.grid.load_layout(self.factory)
        if not loaded:
            self._default_layout()

    def _default_layout(self):
        g = self.grid
        g.add_widget(ExploreGridWidget(self.state,   SlotSize.LARGE))
        g.add_widget(TopHeadlinesWidget(self.state,  SlotSize.TALL))

    def _on_capacity(self, used: int, total: int):
        free = total - used
        colour = "#22c55e" if free > 1 else ("#f59e0b" if free == 1 else "#ef4444")
        self._slot_badge.setText(f"{used} / {total} slots")
        self._slot_badge.setStyleSheet(self._slot_badge.styleSheet().split("color:")[0]
                                       + f"color: {colour}; padding: 0 18px; }}")

    def closeEvent(self, event):
        self.grid.save_layout()
        super().closeEvent(event)

    def _open_store(self):
        self._main_stack.setCurrentIndex(2)

    def _on_dock_click(self, idx: int):
        if idx == 0:
            self._main_stack.setCurrentIndex(0)  # Home
        elif idx == 1:
            self._main_stack.setCurrentIndex(2)  # App Store (Widget Store for now)
        elif idx == 2:
            self._main_stack.setCurrentIndex(1)  # Settings -> using App Library for demo
        else:
            self._main_stack.setCurrentIndex(1)  # All other icons open App Library


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    font = QtGui.QFont("Century Gothic", 11)
    font.setStyleHint(QtGui.QFont.SansSerif)
    app.setFont(font)

    state  = DashboardState()
    window = DesktopDashboard(state)
    window.showMaximized()
    sys.exit(app.exec_())
