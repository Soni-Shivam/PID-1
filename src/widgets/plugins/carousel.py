"""Hero carousel widget (CMS-fed).

Cycles through featured cards (title, subtitle, call-to-action). Auto-advances
every 8 s but only while visible (the timer stops on hide), to respect the idle
CPU budget. Prev/next arrows and page dots for manual control.

Card-to-card transitions cross-fade the headline text via a QGraphicsOpacity
effect: the new card is set at the fade trough so there is no flicker. The
effect is software-composited by Qt (no X compositor needed) and animates a
small static text block for ~330 ms, so the periodic cost stays negligible.
Each transition's animations are parented + DeleteWhenStopped, so nothing
accumulates across advances. Colours come from theme tokens (Phase D).
"""
from __future__ import annotations

from core.qt_compat import Qt, QtCore, QtWidgets
from widgets.engine import WidgetContext, WidgetPlugin

_INTERVAL_MS = 8000
_FADE_OUT_MS = 130
_FADE_IN_MS = 210


class _Carousel(QtWidgets.QFrame):
    def __init__(self, ctx: WidgetContext) -> None:
        super().__init__()
        self._ctx = ctx
        self._cards: list[dict] = []
        self.setObjectName("carouselRoot")
        self.setAttribute(Qt.WA_StyledBackground, True)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(28, 26, 28, 20)
        root.setSpacing(6)

        # Text block grouped so a single opacity effect can cross-fade it.
        self._textwrap = QtWidgets.QWidget()
        self._textwrap.setAttribute(Qt.WA_StyledBackground, False)
        tw = QtWidgets.QVBoxLayout(self._textwrap)
        tw.setContentsMargins(0, 0, 0, 0)
        tw.setSpacing(6)
        self._eyebrow = QtWidgets.QLabel("FEATURED")
        self._title = QtWidgets.QLabel()
        self._title.setWordWrap(True)
        self._subtitle = QtWidgets.QLabel()
        self._subtitle.setWordWrap(True)
        tw.addWidget(self._eyebrow)
        tw.addWidget(self._title)
        tw.addWidget(self._subtitle)

        self._opacity = QtWidgets.QGraphicsOpacityEffect(self._textwrap)
        self._opacity.setOpacity(1.0)
        self._textwrap.setGraphicsEffect(self._opacity)

        self._cta = QtWidgets.QPushButton()
        self._cta.setCursor(Qt.PointingHandCursor)
        self._cta.clicked.connect(self._activate_cta)

        root.addWidget(self._textwrap)
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
            f"#carouselRoot{{background:{t['hero']};border:none;"
            f"border-radius:18px;}}")
        self._eyebrow.setStyleSheet(
            f"color:{t['accent']};font-size:11px;font-weight:800;"
            f"letter-spacing:2px;")
        self._title.setStyleSheet(
            f"color:{t['hero_text']};font-size:26px;font-weight:800;")
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
        if len(self._cards) < 2:
            return
        self._index = (self._index + step) % len(self._cards)
        if self.isVisible():
            self._animate_swap()
        else:
            self._show()   # off-screen: no point animating

    def _animate_swap(self) -> None:
        """Cross-fade the text block: fade out, swap content at the trough,
        fade back in. Animations are parented and DeleteWhenStopped so each
        advance leaves nothing behind."""
        out = QtCore.QPropertyAnimation(self._opacity, b"opacity", self)
        out.setDuration(_FADE_OUT_MS)
        out.setStartValue(self._opacity.opacity())
        out.setEndValue(0.0)
        out.setEasingCurve(QtCore.QEasingCurve.InCubic)

        fade_in = QtCore.QPropertyAnimation(self._opacity, b"opacity", self)
        fade_in.setDuration(_FADE_IN_MS)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QtCore.QEasingCurve.OutCubic)

        out.finished.connect(self._show)   # set new card while invisible
        group = QtCore.QSequentialAnimationGroup(self)
        group.addAnimation(out)
        group.addAnimation(fade_in)
        group.start(QtCore.QAbstractAnimation.DeleteWhenStopped)

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
    description = "Rotating featured content cards from the JioPC content feed."
    icon = "media-playback-start"
    default_size = (1, 2)
    needs_cms = True

    def create_view(self, ctx: WidgetContext) -> QtWidgets.QWidget:
        return _Carousel(ctx)
