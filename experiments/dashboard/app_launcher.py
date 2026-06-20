"""
App Library / Launcher — JioPC Discover Desktop
=================================================
Pixel-perfect replication of Screenshot 2.

Layout:
  ┌──────┬───────────────────────────────────────────────────────┐
  │ Nav  │  [🔍 Search apps                               🎤]   │
  │ col  │  [All] [Creativity] [Education] [Finance] ...         │
  │ icons│  ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐           │
  │  🏠  │  │Ch│ │Ff│ │Dl│ │Sl│ │Nn│ │Sp│ │Fg│ │Gm│           │
  │  🔍  │  └──┘ └──┘ └──┘ └──┘ └──┘ └──┘ └──┘ └──┘           │
  │  📚  │  ─────────────────────────────────────────            │
  │  👤  │  [ ＋ Request an app ]                                │
  └──────┴───────────────────────────────────────────────────────┘
"""
from __future__ import annotations
from typing import List, Optional

from core.qt_compat import QtCore, QtGui, QtWidgets
from vertical_dock import VerticalDockWidget

# ══════════════════════════════════════════════════════════════════════════════
# Design tokens
# ══════════════════════════════════════════════════════════════════════════════
_BG_OVERLAY = QtGui.QColor(12, 10, 20, 238)
_NAV_W      = 64     # left icon-only nav column
_TXT_W      = "#F2F2F7"
_TXT_G      = "#8E8E93"
_TXT_D      = "#48484A"
_PILL_SEL_BG = "#6366F1"
_ICON_R      = 28    # app icon border radius
_ICON_SZ     = 110   # app icon size (px)

# ══════════════════════════════════════════════════════════════════════════════
# App Catalog
# ══════════════════════════════════════════════════════════════════════════════
# (display_name, category_tag, bg_color, text_color, emoji)
APP_CATALOG: List[tuple] = [
    ("Chrome",    "Productivity", "#EA4335", "#FFF", ""),
    ("Firefox",   "Productivity", "#FF6611", "#FFF", "🦊"),
    ("Duolingo",  "Education",    "#58CC02", "#FFF", "🦉"),
    ("Slack",     "Productivity", "#4A154B", "#FFF", "💬"),
    ("Notion",    "Productivity", "#1C1C1C", "#FFF", "N"),
    ("Spotify",   "Entertainment","#1DB954", "#FFF", "🎵"),
    ("Figma",     "Creativity",   "#A259FF", "#FFF", "🎨"),
    ("Gmail",     "Productivity", "#EA4335", "#FFF", "M"),
    ("Maps",      "Utilities",    "#34A853", "#FFF", "🗺"),
    ("Photos",    "Utilities",    "#FF6B9D", "#FFF", "📷"),
    ("Calendar",  "Productivity", "#1E88E5", "#FFF", "📅"),
    ("Notes",     "Productivity", "#FDD835", "#000", "📝"),
    ("Reminders", "Productivity", "#FF3B30", "#FFF", "✓"),
    ("App Store", "Utilities",    "#1E88E5", "#FFF", "⊞"),
    ("Settings",  "Utilities",    "#8E8E93", "#FFF", "⚙"),
    ("Camera",    "Utilities",    "#1C1C1E", "#FFF", "📸"),
    ("YouTube",   "Entertainment","#FF0000", "#FFF", "▶"),
    ("Netflix",   "Entertainment","#E50914", "#FFF", "N"),
    ("Discord",   "Entertainment","#5865F2", "#FFF", "💙"),
    ("Zoom",      "Productivity", "#2D8CFF", "#FFF", "🎥"),
    ("VS Code",   "Creativity",   "#007ACC", "#FFF", "◈"),
    ("Sheets",    "Productivity", "#0F9D58", "#FFF", "📊"),
    ("Telegram",  "Productivity", "#2CA5E0", "#FFF", "✈"),
    ("WhatsApp",  "Productivity", "#25D366", "#FFF", "💬"),
    ("News",      "Information",  "#FF3B30", "#FFF", "📰"),
    ("Podcasts",  "Entertainment","#C84FC3", "#FFF", "🎙"),
    ("Finance",   "Finance",      "#22C55E", "#FFF", "📈"),
    ("Health",    "Utilities",    "#FF375F", "#FFF", "❤"),
    ("Music",     "Entertainment","#FC3C44", "#FFF", "♪"),
    ("Books",     "Education",    "#FF9F0A", "#FFF", "📚"),
    ("LinkedIn",  "Productivity", "#0A66C2", "#FFF", "in"),
    ("Twitter",   "Entertainment","#1DA1F2", "#FFF", "𝕏"),
]

CATEGORIES_APPS = [
    "All", "Creativity", "Education", "Finance",
    "Productivity", "Entertainment", "Information", "Utilities",
]

NAV_ITEMS = [
    ("🏠", "Home"),
    ("🔍", "Search"),
    ("📚", "Library"),
    ("👤", "Profile"),
]


# ══════════════════════════════════════════════════════════════════════════════
# App Icon Widget
# ══════════════════════════════════════════════════════════════════════════════
class _AppIcon(QtWidgets.QWidget):
    clicked = QtCore.pyqtSignal(str)

    def __init__(self, name: str, bg: str, fg: str, emoji: str, parent=None):
        super().__init__(parent)
        self._name  = name
        self._bg    = bg
        self._fg    = fg
        self._emoji = emoji
        self._hov   = False

        self.setFixedSize(_ICON_SZ + 16, _ICON_SZ + 32)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setStyleSheet("background: transparent;")
        self.setToolTip(name)

    def enterEvent(self, e):
        self._hov = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hov = False
        self.update()
        super().leaveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == QtCore.Qt.LeftButton:
            self.clicked.emit(self._name)
        super().mouseReleaseEvent(e)

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        icon_rect = QtCore.QRect(8, 0, _ICON_SZ, _ICON_SZ)

        # Scale on hover
        if self._hov:
            p.save()
            cx, cy = self.width() / 2, _ICON_SZ / 2
            p.translate(cx, cy)
            p.scale(1.10, 1.10)
            p.translate(-cx, -cy)

        # Background rounded square
        p.setBrush(QtGui.QColor(self._bg))
        p.setPen(QtCore.Qt.NoPen)
        p.drawRoundedRect(icon_rect, _ICON_R, _ICON_R)

        # Gloss (subtle inner highlight — no GPU)
        gloss = QtGui.QLinearGradient(icon_rect.topLeft(), icon_rect.center())
        gloss.setColorAt(0, QtGui.QColor(255, 255, 255, 40))
        gloss.setColorAt(1, QtGui.QColor(255, 255, 255, 0))
        p.setBrush(gloss)
        p.drawRoundedRect(icon_rect, _ICON_R, _ICON_R)

        # Emoji / letter
        f = QtGui.QFont("Segoe UI Emoji", 28 if len(self._emoji) == 1 else 24)
        p.setFont(f)
        p.setPen(QtGui.QColor(self._fg))
        p.drawText(icon_rect, QtCore.Qt.AlignCenter, self._emoji)

        if self._hov:
            p.restore()

        # App name label below icon
        f2 = QtGui.QFont("Century Gothic", 9)
        p.setFont(f2)
        p.setPen(QtGui.QColor(_TXT_W))
        lbl_rect = QtCore.QRect(0, _ICON_SZ + 6, self.width(), 20)
        # Elide long names
        fm   = QtGui.QFontMetrics(f2)
        name = fm.elidedText(self._name, QtCore.Qt.ElideRight, lbl_rect.width() - 4)
        p.drawText(lbl_rect, QtCore.Qt.AlignCenter | QtCore.Qt.AlignTop, name)
        p.end()


# ══════════════════════════════════════════════════════════════════════════════
# Left Navigation Column
# ══════════════════════════════════════════════════════════════════════════════
class _NavColumn(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(_NAV_W)
        self.setStyleSheet("background: transparent;")

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 20, 0, 20)
        lay.setSpacing(4)
        lay.setAlignment(QtCore.Qt.AlignTop)

        for i, (icon, tip) in enumerate(NAV_ITEMS):
            btn = QtWidgets.QToolButton()
            btn.setText(icon)
            btn.setFixedSize(_NAV_W, _NAV_W)
            btn.setToolTip(tip)
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            if i == 0:
                btn.setStyleSheet(f"""
                    QToolButton {{
                        background: rgba(255,255,255,0.15);
                        color: #FFF;
                        border-radius: {_NAV_W//2}px;
                        font-size: 22px;
                        border: none;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QToolButton {{
                        background: transparent;
                        color: rgba(255,255,255,0.40);
                        border-radius: {_NAV_W//2}px;
                        font-size: 22px;
                        border: none;
                    }}
                    QToolButton:hover {{
                        background: rgba(255,255,255,0.10);
                        color: #FFF;
                    }}
                """)
            lay.addWidget(btn)

        lay.addStretch()


# ══════════════════════════════════════════════════════════════════════════════
# App Library Modal
# ══════════════════════════════════════════════════════════════════════════════
class AppLibraryPanel(QtWidgets.QWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self._active_cat = "All"
        self._icons:  List[_AppIcon] = []
        self._filter_btns: List[QtWidgets.QPushButton] = []
        self.main_window = parent

        self._build()
        self._apply_filter("All")

    # ── construction ──────────────────────────────────────────────────────────
    def _build(self):
        outer = QtWidgets.QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Main panel centering wrapper
        main_wrapper = QtWidgets.QWidget()
        main_wrapper.setStyleSheet("background: transparent;")
        mw_lay = QtWidgets.QHBoxLayout(main_wrapper)
        mw_lay.setContentsMargins(0, 0, 0, 0)
        
        # Add stretch to center the panel (so panel takes ~60%)
        mw_lay.addStretch(2)

        # Main panel
        panel = QtWidgets.QWidget()
        panel.setStyleSheet("background: transparent;")
        panel.setMinimumWidth(800)
        p_lay = QtWidgets.QVBoxLayout(panel)
        p_lay.setContentsMargins(24, 40, 24, 24)
        p_lay.setSpacing(24)

        # ── Search bar ────────────────────────────────────────────────────────
        search_row = QtWidgets.QHBoxLayout()
        self._search = QtWidgets.QLineEdit()
        self._search.setPlaceholderText("Search apps")
        self._search.setFixedHeight(46)
        self._search.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(255,255,255,0.09);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 23px;
                color: {_TXT_W};
                font-size: 15px;
                padding: 0 48px 0 44px;
            }}
            QLineEdit:focus {{
                background: rgba(255,255,255,0.13);
                border-color: rgba(255,255,255,0.22);
            }}
        """)
        self._search.textChanged.connect(self._on_search)

        mic_btn = QtWidgets.QPushButton("🎤")
        mic_btn.setFixedSize(46, 46)
        mic_btn.setCursor(QtCore.Qt.PointingHandCursor)
        mic_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.09);
                border: none;
                border-radius: 23px;
                font-size: 18px;
            }
            QPushButton:hover { background: rgba(255,255,255,0.15); }
        """)

        search_row.addWidget(self._search)
        search_row.addSpacing(8)
        search_row.addWidget(mic_btn)
        p_lay.addLayout(search_row)

        # ── Category filter pills ──────────────────────────────────────────────
        pills_scroll = QtWidgets.QScrollArea()
        pills_scroll.setFixedHeight(40)
        pills_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        pills_scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        pills_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        pills_scroll.setWidgetResizable(True)

        pills_w = QtWidgets.QWidget()
        pills_w.setStyleSheet("background: transparent;")
        pills_lay = QtWidgets.QHBoxLayout(pills_w)
        pills_lay.setContentsMargins(0, 0, 0, 0)
        pills_lay.setSpacing(8)

        for cat in CATEGORIES_APPS:
            btn = QtWidgets.QPushButton(cat)
            btn.setFixedHeight(34)
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, c=cat: self._apply_filter(c))
            self._filter_btns.append(btn)
            pills_lay.addWidget(btn)
        pills_lay.addStretch()

        pills_scroll.setWidget(pills_w)
        p_lay.addWidget(pills_scroll)

        # ── App grid (paged) ──────────────────────────────────────────────────
        self._page_stack = QtWidgets.QStackedWidget()
        self._page_stack.setStyleSheet("background: transparent;")
        
        # Enable mouse wheel scrolling for pages
        self._page_stack.wheelEvent = self._on_wheel_scroll
        
        p_lay.addWidget(self._page_stack, 1)

        # Page indicator dots
        self._page_dots_lay = QtWidgets.QHBoxLayout()
        self._page_dots_lay.setAlignment(QtCore.Qt.AlignCenter)
        p_lay.addLayout(self._page_dots_lay)

        # Pre-create all icons
        for name, cat, bg, fg, emoji in APP_CATALOG:
            icon = _AppIcon(name, bg, fg, emoji)
            icon.clicked.connect(self._on_app_clicked)
            icon.setProperty("category", cat)
            self._icons.append(icon)

        # ── Request button ────────────────────────────────────────────────────
        req_btn = QtWidgets.QPushButton("＋   Request an app")
        req_btn.setFixedHeight(52)
        req_btn.setCursor(QtCore.Qt.PointingHandCursor)
        req_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255,255,255,0.09);
                color: {_TXT_W};
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 14px;
                font-size: 16px;
                font-weight: 600;
            }}
            QPushButton:hover   {{ background: rgba(255,255,255,0.16); }}
            QPushButton:pressed {{ background: rgba(255,255,255,0.05); }}
        """)
        req_btn.clicked.connect(lambda: print("[AppLib] Request an app clicked"))
        p_lay.addWidget(req_btn)

        mw_lay.addWidget(panel, 6) # 60% of width conceptually
        mw_lay.addStretch(2)

        outer.addWidget(main_wrapper, 1)

    # ── dock ──────────────────────────────────────────────────────────────────
    def _on_dock_click(self, idx: int):
        pass

    # ── filter / search ───────────────────────────────────────────────────────
    def _apply_filter(self, cat: str):
        self._active_cat = cat
        self._update_pill_styles()
        self._rebuild_grid(cat, self._search.text().strip().lower())

    def _on_search(self, text: str):
        self._rebuild_grid(self._active_cat, text.strip().lower())

    def _update_pill_styles(self):
        for btn in self._filter_btns:
            sel = btn.text() == self._active_cat
            if sel:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {_PILL_SEL_BG};
                        color: #FFF;
                        border: none;
                        border-radius: 17px;
                        font-size: 13px;
                        font-weight: 600;
                        padding: 0 18px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: rgba(255,255,255,0.09);
                        color: {_TXT_G};
                        border: 1px solid rgba(255,255,255,0.10);
                        border-radius: 17px;
                        font-size: 13px;
                        font-weight: 400;
                        padding: 0 16px;
                    }}
                    QPushButton:hover {{
                        background: rgba(255,255,255,0.15);
                        color: #FFF;
                    }}
                """)

    def _rebuild_grid(self, cat: str, query: str):
        COLS = 7
        ROWS = 4
        APPS_PER_PAGE = COLS * ROWS

        # Clear existing pages
        while self._page_stack.count():
            w = self._page_stack.widget(0)
            self._page_stack.removeWidget(w)
            w.deleteLater()

        # Clear dots
        while self._page_dots_lay.count():
            item = self._page_dots_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Filter icons
        filtered = []
        for icon in self._icons:
            icon.hide()
            icon.setParent(None)
            c = icon.property("category")
            if cat == "All" or c == cat:
                if not query or query in icon._name.lower():
                    filtered.append(icon)

        # Build pages
        for p in range(0, len(filtered), APPS_PER_PAGE):
            page_w = QtWidgets.QWidget()
            page_lay = QtWidgets.QGridLayout(page_w)
            page_lay.setSpacing(16)
            page_lay.setAlignment(QtCore.Qt.AlignCenter)
            
            page_items = filtered[p : p + APPS_PER_PAGE]
            for i, icon in enumerate(page_items):
                r = i // COLS
                c = i % COLS
                icon.show()
                page_lay.addWidget(icon, r, c)
            
            self._page_stack.addWidget(page_w)

            # Add dot
            dot = QtWidgets.QLabel("●")
            dot.setStyleSheet("color: rgba(255,255,255,0.2); font-size: 14px;")
            self._page_dots_lay.addWidget(dot)

        if self._page_stack.count() > 0:
            self._update_dots(0)
            self._page_stack.currentChanged.connect(self._update_dots)

    def _update_dots(self, idx: int):
        for i in range(self._page_dots_lay.count()):
            dot = self._page_dots_lay.itemAt(i).widget()
            if i == idx:
                dot.setStyleSheet("color: #FFFFFF; font-size: 14px;")
            else:
                dot.setStyleSheet("color: rgba(255,255,255,0.2); font-size: 14px;")

    def _on_wheel_scroll(self, event):
        delta = event.angleDelta().y()
        # horizontal scrolling might come in as x() on some trackpads
        if delta == 0:
            delta = event.angleDelta().x()
        
        idx = self._page_stack.currentIndex()
        if delta < -20 and idx < self._page_stack.count() - 1:
            self._page_stack.setCurrentIndex(idx + 1)
        elif delta > 20 and idx > 0:
            self._page_stack.setCurrentIndex(idx - 1)

    def _on_app_clicked(self, name: str):
        print(f"[AppLib] Launched: {name}")

    # ── painting ──────────────────────────────────────────────────────────────
    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        # Dark overlay
        p.fillRect(self.rect(), _BG_OVERLAY)

        # Purple + blue atmosphere
        w, h = self.width(), self.height()
        orbs = [
            (0.65, 0.15, 0.40, 100, 40, 200, 55),
            (0.90, 0.50, 0.30,  40, 30, 180, 40),
            (0.30, 0.70, 0.25,  70, 20, 150, 28),
        ]
        for cx, cy, rad, r, g, b, a in orbs:
            gr = QtGui.QRadialGradient(w * cx, h * cy, w * rad)
            gr.setColorAt(0, QtGui.QColor(r, g, b, a))
            gr.setColorAt(1, QtGui.QColor(0, 0, 0, 0))
            p.fillRect(self.rect(), gr)

        p.end()

    def keyPressEvent(self, e):
        if e.key() == QtCore.Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(e)
