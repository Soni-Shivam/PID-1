"""Hero carousel widget (CMS-fed, with RAM-safe hero images).

Cycles through featured cards (image, title, subtitle, call-to-action).
Auto-advances every 8 s but only while visible (the timer stops on hide)
to respect the idle CPU budget. Prev/next arrows and page dots for manual
control.

Card-to-card transitions cross-fade the hero image + text block via a single
QGraphicsOpacityEffect on the entire content stack: the new card is set while
opacity is at the trough so there is no flicker. Effect is software-composited
by Qt (no X compositor needed). Each transition's animations are parented +
DeleteWhenStopped so nothing accumulates across advances.

Image pipeline (RAM budget compliance):
  - QNetworkAccessManager downloads asynchronously; bytes go straight to disk
    at ~/.cache/jiopc/home/images/ and the QByteArray is released.
  - QImageReader with setScaledSize() pre-scales the image to the label
    dimensions BEFORE allocation, so only the rendered pixels ever live in RAM.
  - In-session QPixmap cache prevents redundant decodes.
  - Rounded corners are applied via QSS border-radius on the image container.

Colours come from theme tokens (Phase D).
"""
from __future__ import annotations

import logging

from core.qt_compat import Qt, QtCore, QtGui, QtWidgets
from widgets.engine import WidgetContext, WidgetPlugin
from widgets.image_cache import ImageCache

log = logging.getLogger("jiopc.carousel")

_INTERVAL_MS = 8000
_FADE_OUT_MS = 130
_FADE_IN_MS = 210
_IMAGE_H = 160       # target height (px) for hero image — proportional to widget
_RADIUS = 18         # border-radius for image container and card background


class _HeroImage(QtWidgets.QLabel):
    """A QLabel that holds a scaled, rounded hero image.

    The image is fetched once and cached by ImageCache.  While loading (or if
    no URL is provided) the widget shows a gradient placeholder so the layout
    does not jump.
    """

    def __init__(self, cache: ImageCache, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._cache = cache
        self._current_url: str = ""
        self._pixmap_full: QtGui.QPixmap | None = None

        self.setMinimumHeight(_IMAGE_H)
        self.setMaximumHeight(_IMAGE_H)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Fixed,
        )
        self.setAlignment(Qt.AlignCenter)
        self.setObjectName("heroImageLabel")
        # Rounded clip via QSS — no compositor, purely software-painted.
        self.setStyleSheet(
            f"#heroImageLabel{{border-radius:{_RADIUS}px;"
            "background:transparent;}"
        )

    def load_url(self, url: str) -> None:
        """Request the pixmap for *url*.  Re-uses cache for same URL."""
        if url == self._current_url:
            return
        self._current_url = url
        self._pixmap_full = None
        self._show_placeholder()
        if not url:
            return
        size = QtCore.QSize(self.width() or 400, _IMAGE_H)
        self._cache.fetch(url, size, self._on_pixmap)

    def _on_pixmap(self, _url: str, pixmap: QtGui.QPixmap) -> None:
        """Called (main thread) when ImageCache has a scaled QPixmap ready."""
        self._pixmap_full = pixmap
        self._apply_pixmap()

    def _apply_pixmap(self) -> None:
        if self._pixmap_full is None:
            return
        # Crop to fill (centre-crop to our exact label size).
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return
        scaled = self._pixmap_full.scaled(
            w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
        )
        # Centre-crop
        x = max(0, (scaled.width() - w) // 2)
        y = max(0, (scaled.height() - h) // 2)
        cropped = scaled.copy(x, y, w, h)

        # Round corners by painting through a rounded clip path.
        rounded = QtGui.QPixmap(cropped.size())
        rounded.fill(Qt.transparent)
        painter = QtGui.QPainter(rounded)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        path = QtGui.QPainterPath()
        path.addRoundedRect(
            QtCore.QRectF(0, 0, cropped.width(), cropped.height()),
            _RADIUS, _RADIUS,
        )
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, cropped)
        painter.end()

        self.setPixmap(rounded)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        # Re-apply existing pixmap at new size so layout changes look correct.
        if self._pixmap_full is not None:
            self._apply_pixmap()

    def _show_placeholder(self) -> None:
        """Draw a subtle gradient rect so space is reserved while loading."""
        w = self.width() or 400
        h = _IMAGE_H
        pm = QtGui.QPixmap(w, h)
        pm.fill(Qt.transparent)
        painter = QtGui.QPainter(pm)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        grad = QtGui.QLinearGradient(0, 0, w, h)
        grad.setColorAt(0, QtGui.QColor(80, 80, 120, 120))
        grad.setColorAt(1, QtGui.QColor(30, 30, 60, 120))
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(0, 0, w, h), _RADIUS, _RADIUS)
        painter.fillPath(path, grad)
        painter.end()
        self.setPixmap(pm)


class _Carousel(QtWidgets.QFrame):
    def __init__(self, ctx: WidgetContext) -> None:
        super().__init__()
        self._ctx = ctx
        self._cards: list[dict] = []
        self._cache = ImageCache(self)
        self.setObjectName("carouselRoot")
        self.setAttribute(Qt.WA_StyledBackground, True)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Hero image ──────────────────────────────────────────────────────
        self._hero_image = _HeroImage(self._cache, self)
        root.addWidget(self._hero_image)

        # ── Text + controls block (opacity-faded as a unit) ─────────────────
        self._content = QtWidgets.QWidget()
        self._content.setAttribute(Qt.WA_StyledBackground, False)
        cl = QtWidgets.QVBoxLayout(self._content)
        cl.setContentsMargins(20, 14, 20, 14)
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
        cl.addLayout(bottom)

        self._dots = QtWidgets.QLabel()
        self._dots.setAlignment(Qt.AlignCenter)
        cl.addWidget(self._dots)

        root.addWidget(self._content)

        # Single opacity effect covers the text block (image fades separately
        # via _HeroImage replacement, which is instant at the trough).
        self._opacity = QtWidgets.QGraphicsOpacityEffect(self._content)
        self._opacity.setOpacity(1.0)
        self._content.setGraphicsEffect(self._opacity)

        self._index = 0
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(_INTERVAL_MS)
        self._timer.timeout.connect(lambda: self._advance(1))

        self._apply_theme()
        ctx.theme.theme_changed.connect(self._apply_theme)
        if ctx.cms is not None:
            ctx.cms.content_updated.connect(self._load)
            self._load(ctx.cms.content())

    # ── Theme ─────────────────────────────────────────────────────────────

    def _apply_theme(self) -> None:
        t = self._ctx.theme.tokens
        self.setStyleSheet(
            f"#carouselRoot{{background:{t['hero']};border:none;"
            f"border-radius:{_RADIUS}px;}}"
        )
        self._eyebrow.setStyleSheet(
            f"color:{t['accent']};font-size:11px;font-weight:800;"
            "letter-spacing:2px;"
        )
        self._title.setStyleSheet(
            f"color:{t['hero_text']};font-size:22px;font-weight:800;"
        )
        self._subtitle.setStyleSheet(f"color:{t['hero_muted']};font-size:12px;")
        self._cta.setStyleSheet(
            f"QPushButton{{background:{t['accent']};color:{t['on_accent']};"
            f"border:none;border-radius:14px;padding:7px 16px;font-weight:600;}}"
        )
        for b in self._nav_btns:
            b.setStyleSheet(
                f"QToolButton{{color:{t['hero_text']};border:none;"
                "font-size:20px;padding:0 6px;}"
            )
        self._show()

    # ── Data ──────────────────────────────────────────────────────────────

    def _load(self, content: dict) -> None:
        self._cards = (content or {}).get("carousel", [])
        self._index = 0
        self._show()

    def _show(self) -> None:
        t = self._ctx.theme.tokens
        if not self._cards:
            self._hero_image.load_url("")
            self._title.setText("Welcome to JioPC")
            self._subtitle.setText("Content will appear here once connected.")
            self._cta.hide()
            self._dots.clear()
            return

        card = self._cards[self._index % len(self._cards)]
        image_url = card.get("image_url", "")
        self._hero_image.load_url(image_url)
        self._hero_image.setVisible(bool(image_url))

        self._title.setText(card.get("title", ""))
        self._subtitle.setText(card.get("subtitle", ""))
        label = card.get("cta_label", "")
        self._cta.setVisible(bool(label))
        self._cta.setText(label)

        n = len(self._cards)
        idx = self._index % n
        on, off = t["dot_on"], t["dot"]
        self._dots.setText(" ".join(
            f"<span style='color:{on if i == idx else off}'>●</span>"
            for i in range(n)
        ))

    # ── Navigation ────────────────────────────────────────────────────────

    def _advance(self, step: int) -> None:
        if len(self._cards) < 2:
            return
        self._index = (self._index + step) % len(self._cards)
        if self.isVisible():
            self._animate_swap()
        else:
            self._show()

    def _animate_swap(self) -> None:
        """Cross-fade text block; image updates at the opacity trough."""
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

        # Swap content (image + text) at the invisible trough.
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
    description = "Rotating featured content cards with hero images from the JioPC content feed."
    icon = "media-playback-start"
    default_size = (1, 2)
    needs_cms = True

    def create_view(self, ctx: WidgetContext) -> QtWidgets.QWidget:
        return _Carousel(ctx)
