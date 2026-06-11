"""Hero carousel widget (CMS-fed).

Cycles through featured cards (title, subtitle, call-to-action). Auto-advances
every 8 s but only while visible (the timer stops on hide), to respect the idle
CPU budget. Prev/next arrows and page dots for manual control. Transitions are
instant (no compositor); a slide animation is a possible polish follow-up.
Colours come from the live theme tokens and restyle on theme_changed (Phase D).
"""
from __future__ import annotations

from core.qt_compat import Qt, QtCore, QtWidgets
from widgets.engine import WidgetContext, WidgetPlugin

_INTERVAL_MS = 8000


class _Carousel(QtWidgets.QFrame):
    def __init__(self, ctx: WidgetContext) -> None:
        super().__init__()
        self._ctx = ctx
        self._cards: list[dict] = []
        self.setObjectName("carouselRoot")
        self.setAttribute(Qt.WA_StyledBackground, True)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 18)
        self._title = QtWidgets.QLabel()
        self._title.setWordWrap(True)
        self._subtitle = QtWidgets.QLabel()
        self._subtitle.setWordWrap(True)
        self._cta = QtWidgets.QPushButton()
        self._cta.setCursor(Qt.PointingHandCursor)
        self._cta.clicked.connect(self._activate_cta)

        root.addWidget(self._title)
        root.addWidget(self._subtitle)
        root.addStretch(1)
        bottom = QtWidgets.QHBoxLayout()
        bottom.addWidget(self._cta, 0, Qt.AlignLeft)
        bottom.addStretch(1)
        self._nav = QtWidgets.QHBoxLayout()
        self._nav_btns: list[QtWidgets.QToolButton] = []
        for sym, step in (("‹", -1), ("›", +1)):
            b = QtWidgets.QToolButton()
            b.setText(sym)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, s=step: self._advance(s))
            self._nav.addWidget(b)
            self._nav_btns.append(b)
        bottom.addLayout(self._nav)
        root.addLayout(bottom)
        self._dots = QtWidgets.QLabel()
        self._dots.setAlignment(Qt.AlignCenter)
        root.addWidget(self._dots)

        self._index = 0
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(_INTERVAL_MS)
        self._timer.timeout.connect(lambda: self._advance(1))

        self._apply_theme()
        ctx.theme.theme_changed.connect(self._apply_theme)
        if ctx.cms is not None:
            ctx.cms.content_updated.connect(self._load)
            self._load(ctx.cms.content())

    def _apply_theme(self) -> None:
        t = self._ctx.theme.tokens
        self.setStyleSheet(
            f"#carouselRoot{{background:{t['hero']};border-radius:14px;}}")
        self._title.setStyleSheet(
            f"color:{t['hero_text']};font-size:24px;font-weight:700;")
        self._subtitle.setStyleSheet(f"color:{t['hero_muted']};font-size:13px;")
        self._cta.setStyleSheet(
            f"QPushButton{{background:{t['accent']};color:{t['on_accent']};"
            f"border:none;border-radius:16px;padding:8px 18px;font-weight:600;}}")
        for b in self._nav_btns:
            b.setStyleSheet(
                f"QToolButton{{color:{t['hero_text']};border:none;font-size:20px;"
                f"padding:0 6px;}}")
        self._show()

    def _load(self, content: dict) -> None:
        self._cards = (content or {}).get("carousel", [])
        self._index = 0
        self._show()

    def _show(self) -> None:
        t = self._ctx.theme.tokens
        if not self._cards:
            self._title.setText("Welcome to JioPC")
            self._subtitle.setText("Content will appear here once connected.")
            self._cta.hide()
            self._dots.clear()
            return
        card = self._cards[self._index % len(self._cards)]
        self._title.setText(card.get("title", ""))
        self._subtitle.setText(card.get("subtitle", ""))
        label = card.get("cta_label", "")
        self._cta.setVisible(bool(label))
        self._cta.setText(label)
        on, off = t["dot_on"], t["dot"]
        self._dots.setText(" ".join(
            f"<span style='color:{on if i == self._index % len(self._cards) else off}'>●</span>"
            for i in range(len(self._cards))))

    def _advance(self, step: int) -> None:
        if self._cards:
            self._index = (self._index + step) % len(self._cards)
            self._show()

    def _activate_cta(self) -> None:
        if self._cards:
            action = self._cards[self._index % len(self._cards)].get("cta_action", "")
            if action:
                self._ctx.run_action(action)

    def showEvent(self, e) -> None:  # noqa: N802 - advance only while visible
        if self._cards:
            self._timer.start()
        super().showEvent(e)

    def hideEvent(self, e) -> None:  # noqa: N802
        self._timer.stop()
        super().hideEvent(e)


class CarouselPlugin(WidgetPlugin):
    id = "carousel"
    name = "Featured Carousel"
    default_size = (1, 2)
    needs_cms = True

    def create_view(self, ctx: WidgetContext) -> QtWidgets.QWidget:
        return _Carousel(ctx)
