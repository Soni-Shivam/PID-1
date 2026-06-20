"""Hero carousel widget (CMS-fed) with a full-bleed background image.

The featured image fills the ENTIRE widget (scaled to cover, centre-cropped,
rounded corners); the eyebrow / title / subtitle / CTA / arrows / page dots sit
on top, over a bottom-up dark scrim that keeps them legible on any photo. Cycles
every 8 s while visible (timer paused on hide); the text block cross-fades and
the image swaps at the opacity trough.

Images are bundled local assets (src/widgets/assets/, referenced by the feed's
"image" field) so nothing is fetched at paint time; a remote "image_url" is used
as a fallback via ImageCache. Pixmaps are size-capped and cached for the RAM
budget. Text is light over the scrim in both themes; accents come from tokens.
"""
from __future__ import annotations

import logging
from pathlib import Path

from core.qt_compat import Qt, QtCore, QtGui, QtWidgets
from widgets.engine import WidgetContext, WidgetPlugin
from widgets.image_cache import ImageCache

log = logging.getLogger("jiopc.carousel")

_INTERVAL_MS = 8000
_FADE_OUT_MS = 130
_FADE_IN_MS = 210
_RADIUS = 18
_CAP = 1100   # px — max dimension a bundled hero is decoded at (RAM budget)

_ASSETS = Path(__file__).resolve().parent.parent / "assets"
_PIX_CACHE: dict[str, QtGui.QPixmap] = {}


def _load_local(name: str) -> QtGui.QPixmap | None:
    """Decode a bundled hero image (size-capped, cached). None if missing."""
    if not name:
        return None
    if name in _PIX_CACHE:
        return _PIX_CACHE[name]
    path = _ASSETS / name
    if not path.exists():
        return None
    reader = QtGui.QImageReader(str(path))
    sz = reader.size()
    if sz.isValid() and max(sz.width(), sz.height()) > _CAP:
        scale = _CAP / max(sz.width(), sz.height())
        reader.setScaledSize(QtCore.QSize(int(sz.width() * scale),
                                          int(sz.height() * scale)))
    img = reader.read()
    pm = QtGui.QPixmap.fromImage(img) if not img.isNull() else None
    if pm is not None:
        _PIX_CACHE[name] = pm
    return pm


class _Carousel(QtWidgets.QFrame):
    def __init__(self, ctx: WidgetContext) -> None:
        super().__init__()
        self._ctx = ctx
        self._cards: list[dict] = []
        self._index = 0
        self._pixmap: QtGui.QPixmap | None = None
        self._pending_url = ""
        self._cache = ImageCache(self)
        self.setObjectName("carouselRoot")
        self.setAttribute(Qt.WA_StyledBackground, False)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addStretch(1)

        self._content = QtWidgets.QWidget()
        self._content.setAttribute(Qt.WA_StyledBackground, False)
        cl = QtWidgets.QVBoxLayout(self._content)
        cl.setContentsMargins(22, 16, 22, 18)
        cl.setSpacing(6)
        self._eyebrow = QtWidgets.QLabel("FEATURED")
        self._title = QtWidgets.QLabel()
        self._title.setWordWrap(True)
        self._subtitle = QtWidgets.QLabel()
        self._subtitle.setWordWrap(True)
        cl.addWidget(self._eyebrow)
        cl.addWidget(self._title)
        cl.addWidget(self._subtitle)

        bottom = QtWidgets.QHBoxLayout()
        self._cta = QtWidgets.QPushButton()
        self._cta.setCursor(Qt.PointingHandCursor)
        self._cta.clicked.connect(self._activate_cta)
        bottom.addWidget(self._cta, 0, Qt.AlignLeft)
        bottom.addStretch(1)
        self._nav_btns: list[QtWidgets.QToolButton] = []
        for sym, step in (("‹", -1), ("›", +1)):
            b = QtWidgets.QToolButton()
            b.setText(sym)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, s=step: self._advance(s))
            bottom.addWidget(b)
            self._nav_btns.append(b)
        cl.addLayout(bottom)
        self._dots = QtWidgets.QLabel()
        self._dots.setAlignment(Qt.AlignCenter)
        cl.addWidget(self._dots)
        root.addWidget(self._content)

        self._opacity = QtWidgets.QGraphicsOpacityEffect(self._content)
        self._opacity.setOpacity(1.0)
        self._content.setGraphicsEffect(self._opacity)

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(_INTERVAL_MS)
        self._timer.timeout.connect(lambda: self._advance(1))

        self._apply_theme()
        ctx.theme.theme_changed.connect(self._apply_theme)
        if ctx.cms is not None:
            ctx.cms.content_updated.connect(self._load)
            self._load(ctx.cms.content())

    # --- full-bleed background -------------------------------------------
    def paintEvent(self, _e) -> None:  # noqa: N802
        from core.colors import to_qcolor
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        rect = self.rect()
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(rect), _RADIUS, _RADIUS)
        p.setClipPath(path)

        t = self._ctx.theme.tokens
        if self._pixmap is not None and not self._pixmap.isNull():
            pm = self._pixmap.scaled(rect.width(), rect.height(),
                                     Qt.KeepAspectRatioByExpanding,
                                     Qt.SmoothTransformation)
            x = (pm.width() - rect.width()) // 2
            y = (pm.height() - rect.height()) // 2
            p.drawPixmap(rect, pm, QtCore.QRect(x, y, rect.width(), rect.height()))
        else:
            grad = QtGui.QLinearGradient(0, 0, rect.width(), rect.height())
            grad.setColorAt(0, to_qcolor(t.get("hero", "#173a5e")))
            grad.setColorAt(1, to_qcolor(t.get("accent_soft", "#1c2d4a")))
            p.fillRect(rect, grad)

        # Bottom-up dark scrim so the overlaid text stays legible on any image.
        scrim = QtGui.QLinearGradient(0, rect.height() * 0.30, 0, rect.height())
        scrim.setColorAt(0.0, QtGui.QColor(0, 0, 0, 0))
        scrim.setColorAt(0.55, QtGui.QColor(0, 0, 0, 120))
        scrim.setColorAt(1.0, QtGui.QColor(0, 0, 0, 215))
        p.fillRect(rect, scrim)
        p.end()

    # --- theme -----------------------------------------------------------
    def _apply_theme(self) -> None:
        t = self._ctx.theme.tokens
        self._eyebrow.setStyleSheet(
            "color:rgba(255,255,255,0.85);font-size:11px;font-weight:800;"
            "letter-spacing:2px;background:transparent;")
        self._title.setStyleSheet(
            "color:#ffffff;font-size:23px;font-weight:800;background:transparent;")
        self._subtitle.setStyleSheet(
            "color:rgba(255,255,255,0.82);font-size:12px;background:transparent;")
        self._cta.setStyleSheet(
            f"QPushButton{{background:{t['accent']};color:{t['on_accent']};"
            f"border:none;border-radius:15px;padding:8px 18px;font-weight:700;}}"
            f"QPushButton:hover{{background:{t['indicator']};}}")
        for b in self._nav_btns:
            b.setStyleSheet(
                "QToolButton{color:#ffffff;border:none;font-size:22px;"
                "padding:0 6px;background:transparent;}"
                "QToolButton:hover{color:rgba(255,255,255,0.7);}")
        self._show()

    # --- data ------------------------------------------------------------
    def _load(self, content: dict) -> None:
        self._cards = (content or {}).get("carousel", [])
        self._index = 0
        self._show()

    def _show(self) -> None:
        t = self._ctx.theme.tokens
        if not self._cards:
            self._pixmap = None
            self._title.setText("Welcome to JioPC")
            self._subtitle.setText("Content will appear here once connected.")
            self._cta.hide()
            self._dots.clear()
            self.update()
            return
        card = self._cards[self._index % len(self._cards)]
        self._resolve_image(card)
        self._title.setText(card.get("title", ""))
        self._subtitle.setText(card.get("subtitle", ""))
        label = card.get("cta_label", "")
        self._cta.setVisible(bool(label))
        self._cta.setText(label)
        n = len(self._cards)
        idx = self._index % n
        self._dots.setText(" ".join(
            f"<span style='color:{'#ffffff' if i == idx else 'rgba(255,255,255,0.35)'}'>●</span>"
            for i in range(n)))
        self.update()

    def _resolve_image(self, card: dict) -> None:
        pm = _load_local(card.get("image", ""))
        if pm is not None:
            self._pixmap = pm
            self._pending_url = ""
            return
        url = card.get("image_url", "")
        self._pixmap = None
        self._pending_url = url
        if url:
            self._cache.fetch(url, QtCore.QSize(self.width() or 600,
                                                self.height() or 400),
                              self._on_remote)

    def _on_remote(self, url: str, pixmap: QtGui.QPixmap) -> None:
        if url == self._pending_url:
            self._pixmap = pixmap
            self.update()

    # --- navigation ------------------------------------------------------
    def _advance(self, step: int) -> None:
        if len(self._cards) < 2:
            return
        self._index = (self._index + step) % len(self._cards)
        if self.isVisible():
            self._animate_swap()
        else:
            self._show()

    def _animate_swap(self) -> None:
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
        out.finished.connect(self._show)
        group = QtCore.QSequentialAnimationGroup(self)
        group.addAnimation(out)
        group.addAnimation(fade_in)
        group.start(QtCore.QAbstractAnimation.DeleteWhenStopped)

    def _activate_cta(self) -> None:
        if self._cards:
            action = self._cards[self._index % len(self._cards)].get("cta_action", "")
            if action:
                self._ctx.run_action(action)

    def showEvent(self, e) -> None:  # noqa: N802
        if self._cards:
            self._timer.start()
        super().showEvent(e)

    def hideEvent(self, e) -> None:  # noqa: N802
        self._timer.stop()
        super().hideEvent(e)


class CarouselPlugin(WidgetPlugin):
    id = "carousel"
    name = "Featured Carousel"
    description = "Full-bleed featured cards with hero images from the content feed."
    icon = "media-playback-start"
    default_size = (1, 2)
    sizes = [(1, 2), (2, 2), (2, 1)]
    needs_cms = True
    category = "Entertainment"

    def create_view(self, ctx: WidgetContext) -> QtWidgets.QWidget:
        return _Carousel(ctx)
