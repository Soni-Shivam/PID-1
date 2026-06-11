"""Hero carousel widget (CMS-fed).

Cycles through featured cards (title, subtitle, call-to-action). Auto-advances
every 8 s but only while visible (the timer stops on hide), to respect the idle
CPU budget. Prev/next arrows and page dots for manual control. Transitions are
instant (no compositor); a slide animation is a possible polish follow-up.
"""
from __future__ import annotations

from core.qt_compat import Qt, QtCore, QtWidgets
from widgets.engine import WidgetContext, WidgetPlugin

_C = {"text": "#ffffff", "muted": "#c7d2e0", "bg": "#1b3a4b",
      "accent": "#5b9bff", "dot": "#54627a", "dot_on": "#ffffff"}
_INTERVAL_MS = 8000


class _Carousel(QtWidgets.QFrame):
    def __init__(self, ctx: WidgetContext) -> None:
        super().__init__()
        self._ctx = ctx
        self._cards: list[dict] = []
        self.setStyleSheet(f"#carouselRoot{{background:{_C['bg']};border-radius:14px;}}")
        self.setObjectName("carouselRoot")

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 18)
        self._title = QtWidgets.QLabel()
        self._title.setWordWrap(True)
        self._title.setStyleSheet(f"color:{_C['text']};font-size:24px;font-weight:700;")
        self._subtitle = QtWidgets.QLabel()
        self._subtitle.setWordWrap(True)
        self._subtitle.setStyleSheet(f"color:{_C['muted']};font-size:13px;")
        self._cta = QtWidgets.QPushButton()
        self._cta.setCursor(Qt.PointingHandCursor)
        self._cta.setStyleSheet(
            f"QPushButton{{background:{_C['accent']};color:#fff;border:none;"
            f"border-radius:16px;padding:8px 18px;font-weight:600;}}")
        self._cta.clicked.connect(self._activate_cta)

        root.addWidget(self._title)
        root.addWidget(self._subtitle)
        root.addStretch(1)
        bottom = QtWidgets.QHBoxLayout()
        bottom.addWidget(self._cta, 0, Qt.AlignLeft)
        bottom.addStretch(1)
        self._nav = QtWidgets.QHBoxLayout()
        for sym, step in (("‹", -1), ("›", +1)):
            b = QtWidgets.QToolButton()
            b.setText(sym)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(
                f"QToolButton{{color:{_C['text']};border:none;font-size:20px;"
                f"padding:0 6px;}}")
            b.clicked.connect(lambda _=False, s=step: self._advance(s))
            self._nav.addWidget(b)
        bottom.addLayout(self._nav)
        root.addLayout(bottom)
        self._dots = QtWidgets.QLabel()
        self._dots.setAlignment(Qt.AlignCenter)
        root.addWidget(self._dots)

        self._index = 0
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(_INTERVAL_MS)
        self._timer.timeout.connect(lambda: self._advance(1))

        if ctx.cms is not None:
            ctx.cms.content_updated.connect(self._load)
            self._load(ctx.cms.content())

    def _load(self, content: dict) -> None:
        self._cards = content.get("carousel", [])
        self._index = 0
        self._show()

    def _show(self) -> None:
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
        on, off = _C["dot_on"], _C["dot"]
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
