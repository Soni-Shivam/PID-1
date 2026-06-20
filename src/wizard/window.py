"""First-run greeting / onboarding wizard (Component E).

Runs once, on first login. Three steps over a token-themed, work-area-sized
frameless overlay (the dock and panel stay visible beneath it so the tour can
point at real components):

  1. Personalised greeting   - real name + current time/date salutation
  2. Quick tour              - dock, application menu, widgets, themes
  3. Make it yours           - pick light/dark (applied live) + pin a few apps

The completion flag is written when the wizard OPENS, not on finish, so a
mid-wizard crash cannot re-trigger it (per the roadmap's once-only rule). Every
page offers Skip. Theme and pins are applied to the live ThemeManager/DockModel.
"""
from __future__ import annotations

from core import store, user
from core.paths import config_file
from core.qt_compat import Qt, QtCore, QtGui, QtWidgets

_FLAG = "onboarding_done"

# Apps offered for pinning on the personalise step, best-effort by id.
_PIN_CANDIDATES = (
    "firefox", "firefox-esr", "chromium", "google-chrome",
    "pcmanfm-qt", "org.kde.dolphin", "nautilus",
    "qterminal", "lxterminal",
    "featherpad", "org.gnome.gedit",
    "audacious", "vlc", "lximage-qt",
    "lxqt-config", "org.gnome.Calculator", "qalculate-qt",
)


def flag_path():
    return config_file(_FLAG)


def is_done() -> bool:
    return flag_path().exists()


class WizardWindow(QtWidgets.QWidget):
    """Once-only first-run overlay; writes its flag the moment it opens."""

    def __init__(self, theme, dock) -> None:
        super().__init__()
        self._theme = theme
        self._dock = dock
        self._pin_btns: dict[str, QtWidgets.QToolButton] = {}

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("WizardRoot")

        self._stack = QtWidgets.QStackedWidget(self)
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self._card = QtWidgets.QFrame()
        self._card.setObjectName("WizardCard")
        self._card.setFixedWidth(720)
        cardlay = QtWidgets.QVBoxLayout(self._card)
        cardlay.setContentsMargins(44, 40, 44, 32)
        cardlay.setSpacing(20)
        cardlay.addWidget(self._stack, 1)
        self._nav = QtWidgets.QHBoxLayout()
        cardlay.addLayout(self._nav)

        centre = QtWidgets.QHBoxLayout()
        centre.addStretch(1)
        centre.addWidget(self._card)
        centre.addStretch(1)
        wrap = QtWidgets.QVBoxLayout()
        wrap.addStretch(1)
        wrap.addLayout(centre)
        wrap.addStretch(1)
        root.addLayout(wrap)

        self._stack.addWidget(self._page_welcome())
        self._stack.addWidget(self._page_tour())
        self._stack.addWidget(self._page_personalise())
        self._build_nav()

        self._restyle()
        theme.theme_changed.connect(self._restyle)

    # --- lifecycle --------------------------------------------------------
    def show_wizard(self) -> None:
        store.write_json(flag_path(), {"done": True})   # flag on OPEN
        self.setGeometry(
            QtWidgets.QApplication.primaryScreen().availableGeometry())
        self.show()
        self.raise_()
        self.activateWindow()

    # --- pages ------------------------------------------------------------
    def _label(self, text: str, role: str) -> QtWidgets.QLabel:
        lbl = QtWidgets.QLabel(text)
        lbl.setProperty("wrole", role)
        lbl.setWordWrap(True)
        return lbl

    def _page_welcome(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)
        lay.setSpacing(8)
        lay.addStretch(1)
        self._greet = self._label(
            f"{user.salutation()}, {user.first_name()}", "h1")
        sub = self._label("Welcome to JioPC Home", "h2")
        body = self._label(
            "Your desktop, reimagined: a fast dock, a full app menu, and live "
            "widgets that bring content to your screen. Let's set it up — it "
            "takes about thirty seconds.", "body")
        lay.addWidget(self._greet)
        lay.addWidget(sub)
        lay.addSpacing(6)
        lay.addWidget(body)
        lay.addStretch(1)
        return w

    def _page_tour(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)
        lay.setSpacing(14)
        lay.addWidget(self._label("A quick tour", "h2"))
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(14)
        tour = [
            ("preferences-desktop", "The Dock",
             "Pinned apps on the left edge. Hover to magnify, click to launch, "
             "right-click to pin or reorder."),
            ("view-grid", "App Menu",
             "Open ☰ on the dock for every app — search, categories, recent and "
             "recommended."),
            ("applications-graphics", "Widgets",
             "Live cards on your desktop. Right-click the desktop or open the "
             "Widget Store to add, move and resize them."),
            ("preferences-desktop-theme", "Themes",
             "Switch light and dark any time from the desktop's Theme button or "
             "Settings."),
        ]
        for i, (icon, title, desc) in enumerate(tour):
            grid.addWidget(self._tour_card(icon, title, desc), i // 2, i % 2)
        lay.addLayout(grid)
        return w

    def _tour_card(self, icon: str, title: str, desc: str) -> QtWidgets.QFrame:
        f = QtWidgets.QFrame()
        f.setProperty("card", True)
        f.setAttribute(Qt.WA_StyledBackground, True)
        fl = QtWidgets.QHBoxLayout(f)
        fl.setContentsMargins(16, 14, 16, 14)
        fl.setSpacing(12)
        ic = QtWidgets.QLabel()
        px = QtGui.QIcon.fromTheme(icon).pixmap(34, 34)
        if px.isNull():
            px = QtGui.QIcon.fromTheme("application-x-executable").pixmap(34, 34)
        ic.setPixmap(px)
        ic.setFixedSize(34, 34)
        fl.addWidget(ic, 0, Qt.AlignTop)
        col = QtWidgets.QVBoxLayout()
        col.setSpacing(3)
        col.addWidget(self._label(title, "cardtitle"))
        col.addWidget(self._label(desc, "carddesc"))
        fl.addLayout(col, 1)
        return f

    def _page_personalise(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)
        lay.setSpacing(12)
        lay.addWidget(self._label("Make it yours", "h2"))
        lay.addWidget(self._label("Choose a look", "section"))
        themes = QtWidgets.QHBoxLayout()
        themes.setSpacing(12)
        self._theme_btns = {}
        for name, title in (("dark", "Dark"), ("light", "Light")):
            b = QtWidgets.QPushButton(f"  {title}")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedHeight(44)
            b.setChecked(self._theme.name == name)
            b.clicked.connect(lambda _=False, n=name: self._choose_theme(n))
            self._theme_btns[name] = b
            themes.addWidget(b)
        themes.addStretch(1)
        lay.addLayout(themes)

        lay.addWidget(self._label("Pin a few favourites to the dock", "section"))
        flow = QtWidgets.QGridLayout()
        flow.setSpacing(8)
        apps = self._dock.model._apps  # noqa: SLF001
        offered = [a for a in _PIN_CANDIDATES if a in apps][:8]
        for i, app_id in enumerate(offered):
            app = apps[app_id]
            btn = QtWidgets.QToolButton()
            btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            btn.setText("  " + app.name)
            btn.setIcon(QtGui.QIcon.fromTheme(app.icon))
            btn.setIconSize(QtCore.QSize(22, 22))
            btn.setCheckable(True)
            btn.setChecked(self._dock.model.is_pinned(app_id))
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("pinchip", True)
            self._pin_btns[app_id] = btn
            flow.addWidget(btn, i // 2, i % 2)
        lay.addLayout(flow)
        lay.addStretch(1)
        return w

    # --- navigation -------------------------------------------------------
    def _build_nav(self) -> None:
        self._skip = QtWidgets.QPushButton("Skip")
        self._skip.setCursor(Qt.PointingHandCursor)
        self._skip.clicked.connect(self._finish)
        self._back = QtWidgets.QPushButton("Back")
        self._back.setCursor(Qt.PointingHandCursor)
        self._back.clicked.connect(self._go_back)
        self._next = QtWidgets.QPushButton("Get started")
        self._next.setDefault(True)
        self._next.setCursor(Qt.PointingHandCursor)
        self._next.clicked.connect(self._go_next)
        self._dots = self._label("", "dots")
        self._nav.addWidget(self._skip)
        self._nav.addStretch(1)
        self._nav.addWidget(self._dots)
        self._nav.addStretch(1)
        self._nav.addWidget(self._back)
        self._nav.addWidget(self._next)
        self._sync_nav()

    def _sync_nav(self) -> None:
        i = self._stack.currentIndex()
        last = self._stack.count() - 1
        self._back.setVisible(i > 0)
        self._next.setText("Finish" if i == last else "Next"
                           if i > 0 else "Get started")
        self._dots.setText("   ".join(
            "●" if k == i else "○" for k in range(self._stack.count())))

    def _go_next(self) -> None:
        i = self._stack.currentIndex()
        if i >= self._stack.count() - 1:
            self._finish()
        else:
            self._stack.setCurrentIndex(i + 1)
            self._sync_nav()

    def _go_back(self) -> None:
        self._stack.setCurrentIndex(max(0, self._stack.currentIndex() - 1))
        self._sync_nav()

    def _choose_theme(self, name: str) -> None:
        for n, b in self._theme_btns.items():
            b.setChecked(n == name)
        if self._theme.name != name:
            self._theme.set_theme(name)

    def _finish(self) -> None:
        chosen = [a for a, b in self._pin_btns.items() if b.isChecked()]
        if chosen:
            existing = [a for a in self._dock.model.pins if a not in chosen]
            self._dock.model.reorder(chosen + existing)
            self._dock._build()           # refresh the live dock
            self._dock._apply_dock_geometry()
        self.close()

    # --- theming ----------------------------------------------------------
    def _restyle(self) -> None:
        t = self._theme.tokens
        scrim = t.get("bg", "#0f1117")
        self.setStyleSheet(
            f"#WizardRoot{{background:{scrim};}}"
            f"#WizardCard{{background:{t.get('panel_bg', t['surface'])};"
            f"border:1px solid {t.get('glass_border', t['border'])};"
            f"border-radius:22px;}}")
        roles = {
            "h1": f"color:{t['text']};font-size:34px;font-weight:800;background:transparent;",
            "h2": f"color:{t['accent']};font-size:20px;font-weight:800;background:transparent;",
            "section": f"color:{t['muted']};font-size:13px;font-weight:700;background:transparent;",
            "body": f"color:{t['muted']};font-size:15px;background:transparent;",
            "cardtitle": f"color:{t['text']};font-size:14px;font-weight:700;background:transparent;",
            "carddesc": f"color:{t['muted']};font-size:12px;background:transparent;",
            "dots": f"color:{t['accent']};font-size:13px;background:transparent;",
        }
        for lbl in self.findChildren(QtWidgets.QLabel):
            role = lbl.property("wrole")
            if role in roles:
                lbl.setStyleSheet(roles[role])
        for n, b in getattr(self, "_theme_btns", {}).items():
            b.setStyleSheet(
                f"QPushButton{{text-align:left;padding:0 18px;border-radius:12px;"
                f"font-size:14px;font-weight:700;background:{t['surface_alt']};"
                f"color:{t['text']};border:1px solid {t['border']};}}"
                f"QPushButton:checked{{background:{t['accent']};color:{t['on_accent']};"
                f"border:1px solid {t['accent']};}}")
        for b in self._pin_btns.values():
            b.setStyleSheet(
                f"QToolButton{{text-align:left;padding:8px 12px;border-radius:12px;"
                f"font-size:12px;font-weight:600;background:{t['surface_alt']};"
                f"color:{t['text']};border:1px solid {t['border']};}}"
                f"QToolButton:checked{{background:{t['accent_soft']};"
                f"color:{t['accent']};border:1px solid {t['accent']};}}")
        self._sync_nav()

    def keyPressEvent(self, e) -> None:  # noqa: N802
        if e.key() == Qt.Key_Escape:
            self._finish()
        else:
            super().keyPressEvent(e)
