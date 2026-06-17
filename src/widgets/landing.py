"""Landing dashboard (Component A) - the reference 'Discover JioPC' home.

A 70/30 split: the left main column (greeting, 2x2 action cards, the Discover
hero banner, an education bar) and a right sidebar (mode switch, large clock,
headlines, assistant prompt, Customise). Content is CMS-fed so it renders
offline from cache - action cards come from feed `tiles`, the hero and the
education bar from `carousel` cards, headlines from `news`.

All colours come from theme tokens and restyle on theme_changed; the only timer
is the 1 s clock (allowed by CLAUDE.md), paused while hidden. Layout is plain
nested QHBox/QVBox/QGrid with static QLabels (no scrolling models) to keep idle
CPU and RAM minimal.
"""
from __future__ import annotations

import time

from core import user
from core.qt_compat import Qt, QtCore, QtGui, QtWidgets
from core.theme import ThemeManager
from widgets.engine import WidgetContext


def _pick(cards: list[dict], needle: str, default_idx: int) -> dict:
    """First carousel card whose title/subtitle contains needle, else by index."""
    n = needle.lower()
    for c in cards:
        if n in (c.get("title", "") + c.get("subtitle", "")).lower():
            return c
    return cards[default_idx] if 0 <= default_idx < len(cards) else {}


class LandingView(QtWidgets.QWidget):
    """The full landing dashboard. Emits customise_requested for the editor."""

    customise_requested = QtCore.pyqtSignal()

    def __init__(self, ctx: WidgetContext) -> None:
        super().__init__()
        self._ctx = ctx
        self._content: dict = {}
        self.setAttribute(Qt.WA_StyledBackground, False)

        root = QtWidgets.QHBoxLayout(self)
        # Bottom margin clears the floating dock (~WIN_H 103 + GAP 10); the
        # DESKTOP-type layer is full-screen and ignores the dock's strut.
        root.setContentsMargins(56, 44, 40, 122)
        root.setSpacing(28)
        root.addWidget(self._build_main(), 7)
        root.addWidget(self._build_sidebar(), 3)

        self._clock_timer = QtCore.QTimer(self)
        self._clock_timer.setInterval(1000)
        self._clock_timer.timeout.connect(self._tick_clock)

        self._apply_theme()
        ctx.theme.theme_changed.connect(self._apply_theme)
        if ctx.cms is not None:
            ctx.cms.content_updated.connect(self._render)
            self._render(ctx.cms.content())

    # ---- left main column ------------------------------------------------
    def _build_main(self) -> QtWidgets.QWidget:
        col = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(col)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(20)

        self._greeting = QtWidgets.QLabel()
        self._greeting.setObjectName("LandGreeting")
        self._greet_sub = QtWidgets.QLabel("Pick up where you left off")
        self._greet_sub.setObjectName("LandGreetSub")
        lay.addWidget(self._greeting)
        lay.addWidget(self._greet_sub)

        # 2x2 action cards
        self._cards_grid = QtWidgets.QGridLayout()
        self._cards_grid.setSpacing(16)
        self._action_cards: list[QtWidgets.QToolButton] = []
        for i in range(4):
            b = QtWidgets.QToolButton()
            b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            b.setCursor(Qt.PointingHandCursor)
            b.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                            QtWidgets.QSizePolicy.Expanding)
            b.setIconSize(QtCore.QSize(30, 30))
            b.setProperty("actioncard", True)
            self._cards_grid.addWidget(b, i // 2, i % 2)
            self._action_cards.append(b)
        lay.addLayout(self._cards_grid, 1)

        # Discover hero banner
        self._hero = QtWidgets.QFrame()
        self._hero.setObjectName("LandHero")
        self._hero.setAttribute(Qt.WA_StyledBackground, True)
        hl = QtWidgets.QHBoxLayout(self._hero)
        hl.setContentsMargins(28, 22, 24, 22)
        htext = QtWidgets.QVBoxLayout(); htext.setSpacing(4)
        self._hero_title = QtWidgets.QLabel(); self._hero_title.setWordWrap(True)
        self._hero_sub = QtWidgets.QLabel(); self._hero_sub.setWordWrap(True)
        htext.addWidget(self._hero_title); htext.addWidget(self._hero_sub)
        hl.addLayout(htext, 1)
        self._hero_cta = QtWidgets.QPushButton()
        self._hero_cta.setCursor(Qt.PointingHandCursor)
        self._hero_cta.clicked.connect(lambda: self._run(self._hero.property("act")))
        hl.addWidget(self._hero_cta, 0, Qt.AlignVCenter)
        lay.addWidget(self._hero)

        # Education bar
        self._edu = QtWidgets.QFrame()
        self._edu.setObjectName("LandEdu")
        self._edu.setAttribute(Qt.WA_StyledBackground, True)
        el = QtWidgets.QHBoxLayout(self._edu)
        el.setContentsMargins(24, 16, 20, 16)
        etext = QtWidgets.QVBoxLayout(); etext.setSpacing(4)
        self._edu_tags = QtWidgets.QLabel("CBSE  |  JEE  |  NEET  |  UPSC")
        self._edu_tags.setObjectName("LandEduTags")
        self._edu_body = QtWidgets.QLabel(); self._edu_body.setWordWrap(True)
        etext.addWidget(self._edu_tags); etext.addWidget(self._edu_body)
        el.addLayout(etext, 1)
        self._edu_cta = QtWidgets.QPushButton("Start learning")
        self._edu_cta.setCursor(Qt.PointingHandCursor)
        self._edu_cta.clicked.connect(lambda: self._run(self._edu.property("act")))
        el.addWidget(self._edu_cta, 0, Qt.AlignVCenter)
        lay.addWidget(self._edu)

        self._left_content = col
        return col

    # ---- right sidebar ---------------------------------------------------
    def _build_sidebar(self) -> QtWidgets.QWidget:
        col = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(col)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(16)

        self._mode_btn = QtWidgets.QPushButton("Switch to Classic Desktop")
        self._mode_btn.setObjectName("LandMode")
        self._mode_btn.setCursor(Qt.PointingHandCursor)
        self._mode_btn.clicked.connect(self._toggle_mode)
        lay.addWidget(self._mode_btn)

        # everything below the mode switch toggles with "classic" mode
        self._side_content = QtWidgets.QWidget()
        sc = QtWidgets.QVBoxLayout(self._side_content)
        sc.setContentsMargins(0, 0, 0, 0); sc.setSpacing(16)

        clock_card = QtWidgets.QFrame(); clock_card.setObjectName("LandCard")
        clock_card.setAttribute(Qt.WA_StyledBackground, True)
        cl = QtWidgets.QVBoxLayout(clock_card); cl.setContentsMargins(22, 18, 22, 18)
        cl.setSpacing(2)
        self._clock = QtWidgets.QLabel(); self._clock.setObjectName("LandClock")
        self._date = QtWidgets.QLabel(); self._date.setObjectName("LandDate")
        cl.addWidget(self._clock); cl.addWidget(self._date)
        sc.addWidget(clock_card)

        news_card = QtWidgets.QFrame(); news_card.setObjectName("LandCard")
        news_card.setAttribute(Qt.WA_StyledBackground, True)
        nl = QtWidgets.QVBoxLayout(news_card); nl.setContentsMargins(20, 16, 20, 16)
        nl.setSpacing(8)
        head = QtWidgets.QHBoxLayout()
        nh = QtWidgets.QLabel("Top headlines"); nh.setObjectName("LandCardHead")
        self._news_all = QtWidgets.QLabel("View all"); self._news_all.setObjectName("LandLink")
        head.addWidget(nh, 1); head.addWidget(self._news_all)
        nl.addLayout(head)
        self._news_box = QtWidgets.QVBoxLayout(); self._news_box.setSpacing(7)
        nl.addLayout(self._news_box)
        sc.addWidget(news_card, 1)

        asst = QtWidgets.QFrame(); asst.setObjectName("LandAssistant")
        asst.setAttribute(Qt.WA_StyledBackground, True)
        al = QtWidgets.QVBoxLayout(asst); al.setContentsMargins(20, 16, 20, 16)
        al.setSpacing(2)
        at = QtWidgets.QLabel("JioPC Assistant"); at.setObjectName("LandCardHead")
        ap = QtWidgets.QLabel("Ask me to get started"); ap.setObjectName("LandAsstSub")
        al.addWidget(at); al.addWidget(ap)
        sc.addWidget(asst)
        lay.addWidget(self._side_content, 1)

        foot = QtWidgets.QHBoxLayout(); foot.addStretch(1)
        self._customise = QtWidgets.QPushButton("Customise")
        self._customise.setObjectName("LandCustomise")
        self._customise.setCursor(Qt.PointingHandCursor)
        self._customise.setIcon(QtGui.QIcon.fromTheme("preferences-desktop"))
        self._customise.clicked.connect(lambda: self.customise_requested.emit())
        foot.addWidget(self._customise)
        lay.addLayout(foot)
        return col

    # ---- interaction -----------------------------------------------------
    def _run(self, action) -> None:
        if action:
            self._ctx.run_action(str(action))

    def _toggle_mode(self) -> None:
        showing = not self._left_content.isVisible()
        self._left_content.setVisible(showing)
        self._side_content.setVisible(showing)
        self._mode_btn.setText(
            "Switch to Classic Desktop" if showing else "Switch to JioPC Home")

    # ---- content ---------------------------------------------------------
    def _render(self, content: dict) -> None:
        self._content = content or {}
        tiles = self._content.get("tiles", [])
        for i, btn in enumerate(self._action_cards):
            if i < len(tiles):
                tile = tiles[i]
                btn.setText(tile.get("label", ""))
                btn.setIcon(QtGui.QIcon.fromTheme(tile.get("icon", "")))
                btn.setProperty("act", tile.get("action", ""))
                try:
                    btn.clicked.disconnect()
                except TypeError:
                    pass
                btn.clicked.connect(lambda _=False, b=btn: self._run(b.property("act")))
                btn.show()
            else:
                btn.hide()

        cards = self._content.get("carousel", [])
        hero = _pick(cards, "discover", 1)
        self._hero_title.setText(hero.get("title", "Discover JioPC"))
        self._hero_sub.setText(hero.get(
            "subtitle", "A full computer on your TV. No laptop needed."))
        self._hero_cta.setText(hero.get("cta_label", "Take a quick tour"))
        self._hero.setProperty("act", hero.get("cta_action", ""))

        edu = _pick(cards, "doubt", 0)
        self._edu_body.setText(edu.get(
            "subtitle", "Khan Academy, Testbook, JEE prep - all on your TV."))
        self._edu_cta.setText(edu.get("cta_label", "Start learning"))
        self._edu.setProperty("act", edu.get("cta_action", ""))

        self._render_news()

    def _render_news(self) -> None:
        t = self._ctx.theme.tokens
        while self._news_box.count():
            it = self._news_box.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        for entry in self._content.get("news", [])[:5]:
            row = QtWidgets.QLabel("•  " + entry.get("headline", ""))
            row.setWordWrap(True)
            row.setStyleSheet(
                f"color:{t['text']};font-size:12px;background:transparent;")
            self._news_box.addWidget(row)

    def _tick_clock(self) -> None:
        now = time.localtime()
        self._clock.setText(time.strftime("%I:%M %p", now).lstrip("0"))
        self._date.setText(time.strftime("%d %B %Y", now))

    # ---- theming ---------------------------------------------------------
    def _apply_theme(self) -> None:
        t = self._ctx.theme.tokens
        self._greeting.setText(f"{user.salutation()}, {user.first_name()}")
        self._tick_clock()
        self._render_news()
        # action cards
        for b in self._action_cards:
            b.setStyleSheet(
                f"QToolButton[actioncard=\"true\"]{{background:qlineargradient("
                f"x1:0,y1:0,x2:0,y2:1,stop:0 {t['surface_alt']},stop:1 {t['surface']});"
                f"color:{t['text']};border:1px solid {t['glass_border']};"
                f"border-radius:16px;font-size:15px;font-weight:700;padding:14px;}}"
                f"QToolButton[actioncard=\"true\"]:hover{{border:1px solid {t['accent']};"
                f"color:{t['accent']};background:{t['accent_soft']};}}")
        self._hero.setStyleSheet(
            f"#LandHero{{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {t['hero']},stop:1 {t['surface']});border:1px solid "
            f"{t['glass_border']};border-radius:18px;}}")
        self._hero_title.setStyleSheet(
            f"color:{t['hero_text']};font-size:24px;font-weight:800;background:transparent;")
        self._hero_sub.setStyleSheet(
            f"color:{t['hero_muted']};font-size:13px;background:transparent;")
        cta = (f"QPushButton{{background:{t['accent']};color:{t['on_accent']};"
               f"border:none;border-radius:18px;padding:10px 22px;font-weight:700;}}"
               f"QPushButton:hover{{background:{t['on_accent']};color:{t['accent']};}}")
        self._hero_cta.setStyleSheet(cta)
        self._edu.setStyleSheet(
            f"#LandEdu{{background:{t['surface']};border:1px solid {t['glass_border']};"
            f"border-radius:16px;}}")
        self._edu_tags.setStyleSheet(
            f"color:{t['accent']};font-size:12px;font-weight:800;"
            f"letter-spacing:1px;background:transparent;")
        self._edu_body.setStyleSheet(
            f"color:{t['muted']};font-size:12px;background:transparent;")
        self._edu_cta.setStyleSheet(cta)
        # greeting + sidebar text
        self._greeting.setStyleSheet(
            f"color:{t['text']};font-size:30px;font-weight:800;background:transparent;")
        self._greet_sub.setStyleSheet(
            f"color:{t['muted']};font-size:14px;background:transparent;")
        card_qss = (f"#LandCard{{background:{t['card_bg']};border:1px solid "
                    f"{t['card_border']};border-radius:16px;}}")
        for w in self.findChildren(QtWidgets.QFrame, "LandCard"):
            w.setStyleSheet(card_qss)
        self._clock.setStyleSheet(
            f"color:{t['text']};font-size:36px;font-weight:800;background:transparent;")
        self._date.setStyleSheet(f"color:{t['muted']};font-size:12px;background:transparent;")
        head_qss = f"color:{t['text']};font-size:13px;font-weight:700;background:transparent;"
        for w in self.findChildren(QtWidgets.QLabel, "LandCardHead"):
            w.setStyleSheet(head_qss)
        self._news_all.setStyleSheet(
            f"color:{t['accent']};font-size:11px;background:transparent;")
        self._mode_btn.setStyleSheet(
            f"QPushButton#LandMode{{background:{t['surface']};color:{t['text']};"
            f"border:1px solid {t['glass_border']};border-radius:12px;padding:11px;"
            f"font-weight:600;}}QPushButton#LandMode:hover{{border:1px solid {t['accent']};"
            f"color:{t['accent']};}}")
        self._customise.setStyleSheet(
            f"QPushButton#LandCustomise{{background:{t['accent_soft']};color:{t['accent']};"
            f"border:1px solid {t['accent']};border-radius:12px;padding:8px 18px;"
            f"font-weight:700;}}QPushButton#LandCustomise:hover{{background:{t['accent']};"
            f"color:{t['on_accent']};}}")
        asst = self.findChild(QtWidgets.QFrame, "LandAssistant")
        if asst:
            asst.setStyleSheet(
                f"#LandAssistant{{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
                f"stop:0 {t['accent_soft']},stop:1 {t['surface']});border:1px solid "
                f"{t['accent']};border-radius:16px;}}")
        for lbl in self.findChildren(QtWidgets.QLabel, "LandAsstSub"):
            lbl.setStyleSheet(f"color:{t['muted']};font-size:12px;background:transparent;")

    # ---- lifecycle -------------------------------------------------------
    def showEvent(self, e) -> None:  # noqa: N802
        self._clock_timer.start()
        self._tick_clock()
        super().showEvent(e)

    def hideEvent(self, e) -> None:  # noqa: N802
        self._clock_timer.stop()
        super().hideEvent(e)
