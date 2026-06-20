"""Widget Store overlay (Component C — add widgets to the desktop).

A full work-area frameless window, opened on demand from the desktop, that
presents every discovered WidgetPlugin as a preview card grouped by category,
with live search. "Add to home" places the widget in the SnapGrid (which then
persists layout.json). Token-themed throughout so light and dark both render.

Ported in spirit from the dashboard experiment's Widget Library, but driven by
the real plugin registry instead of a hardcoded catalog, and painted from theme
tokens instead of fixed hex. Preview swatches are painted once (no live widget
instances, no idle timers) to stay inside the CPU budget.
"""
from __future__ import annotations

from typing import Callable

from core.qt_compat import Qt, QtCore, QtGui, QtWidgets
from core.background import paint_background
from core.colors import to_qcolor

_CARD_W = 264
_PREV_H = 150

# Per-category accent so the painted swatches feel varied yet themed.
_CAT_ACCENT = {
    "Information":   "#3b82f6",
    "Productivity":  "#6366f1",
    "Entertainment": "#ec4899",
    "Finance":       "#22c55e",
    "Education":     "#f59e0b",
    "AI":            "#8b5cf6",
    "Utilities":     "#0ea5e9",
}


def _accent_for(plugin) -> str:
    return _CAT_ACCENT.get(getattr(plugin, "category", ""), "#5b9bff")


def _rounded(pm: QtGui.QPixmap, w: int, h: int, r: int = 12) -> QtGui.QPixmap:
    """Cover-fit *pm* into w x h with rounded corners."""
    scaled = pm.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    x = max(0, (scaled.width() - w) // 2)
    y = max(0, (scaled.height() - h) // 2)
    cropped = scaled.copy(x, y, w, h)
    out = QtGui.QPixmap(w, h)
    out.fill(Qt.transparent)
    p = QtGui.QPainter(out)
    p.setRenderHint(QtGui.QPainter.Antialiasing)
    path = QtGui.QPainterPath()
    path.addRoundedRect(QtCore.QRectF(0, 0, w, h), r, r)
    p.setClipPath(path)
    p.drawPixmap(0, 0, cropped)
    p.end()
    return out


def _live_preview(plugin, ctx, w: int, h: int) -> QtGui.QPixmap | None:
    """Render the plugin's real view to a pixmap once (no lingering timers).

    A QShowEvent is delivered so widgets that populate on show (system health,
    clocks) fill in before the grab; the temporary view is then discarded, which
    tears down any timer it started — so the store costs nothing while idle.
    """
    try:
        view = plugin.create_view(ctx)
        frame = QtWidgets.QFrame()
        frame.setProperty("card", True)
        frame.setAttribute(Qt.WA_StyledBackground, True)
        frame.setAttribute(Qt.WA_DontShowOnScreen, True)
        lay = QtWidgets.QVBoxLayout(frame)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(view)
        frame.resize(w, h)
        frame.ensurePolished()
        frame.layout().activate()
        QtWidgets.QApplication.sendEvent(view, QtGui.QShowEvent())
        pm = frame.grab()
        frame.deleteLater()
        return pm if not pm.isNull() else None
    except Exception:  # a misbehaving plugin must not break the store
        return None


class _PreviewCard(QtWidgets.QFrame):
    add_clicked = QtCore.pyqtSignal(str, tuple)   # (plugin_id, size)

    def __init__(self, plugin, ctx, theme) -> None:
        super().__init__()
        self._plugin = plugin
        self._theme = theme
        self._added = False
        self._full = False
        self.setFixedWidth(_CARD_W)
        self.setProperty("card", True)
        self.setAttribute(Qt.WA_StyledBackground, True)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)
        pw = _CARD_W - 24
        preview = QtWidgets.QLabel()
        preview.setFixedHeight(_PREV_H)
        preview.setAlignment(Qt.AlignCenter)
        preview.setStyleSheet("background:transparent;")
        pm = _live_preview(plugin, ctx, pw, _PREV_H)
        if pm is not None:
            preview.setPixmap(_rounded(pm, pw, _PREV_H))
        else:
            icon = QtGui.QIcon.fromTheme(plugin.icon).pixmap(56, 56)
            preview.setPixmap(icon)
        root.addWidget(preview)

        self._name = QtWidgets.QLabel(plugin.name)
        self._desc = QtWidgets.QLabel(plugin.description or "")
        self._desc.setWordWrap(True)
        self._desc.setMaximumHeight(34)
        root.addWidget(self._name)
        root.addWidget(self._desc)
        root.addStretch(1)

        self._btn = QtWidgets.QPushButton("＋  Add to home")
        self._btn.setFixedHeight(34)
        self._btn.setCursor(Qt.PointingHandCursor)
        self._btn.clicked.connect(
            lambda: self.add_clicked.emit(
                self._plugin.id, tuple(self._plugin.default_size)))
        root.addWidget(self._btn)

        self._apply_theme()
        theme.theme_changed.connect(self._apply_theme)

    def _apply_theme(self) -> None:
        t = self._theme.tokens
        self._name.setStyleSheet(
            f"color:{t['text']};font-size:14px;font-weight:700;background:transparent;")
        self._desc.setStyleSheet(
            f"color:{t['muted']};font-size:11px;background:transparent;")
        self._restyle_btn()

    def _restyle_btn(self) -> None:
        t = self._theme.tokens
        if self._added:
            self._btn.setText("✓  Added")
            self._btn.setStyleSheet(
                f"QPushButton{{background:#22c55e;color:#fff;border:none;"
                f"border-radius:10px;font-size:12px;font-weight:700;}}")
        elif self._full:
            self._btn.setText("Home is full")
            self._btn.setStyleSheet(
                f"QPushButton{{background:{t['surface_alt']};color:{t['muted']};"
                f"border:1px solid {t['border']};border-radius:10px;"
                f"font-size:12px;font-weight:600;}}")
        else:
            self._btn.setText("＋  Add to home")
            self._btn.setStyleSheet(
                f"QPushButton{{background:{t['surface_alt']};color:{t['text']};"
                f"border:1px solid {t['border']};border-radius:10px;"
                f"font-size:12px;font-weight:600;}}"
                f"QPushButton:hover{{background:{t['accent']};color:{t['on_accent']};"
                f"border-color:{t['accent']};}}")
        self._btn.setEnabled(not self._added and not self._full)

    def set_state(self, added: bool, full: bool) -> None:
        self._added, self._full = added, full
        self._restyle_btn()


class WidgetStore(QtWidgets.QWidget):
    """On-top overlay listing plugins; adds to the grid on demand."""

    def __init__(self, plugins: dict, grid, theme, ctx,
                 on_add: Callable[[str, tuple], None]) -> None:
        super().__init__()
        self._plugins = plugins
        self._grid = grid
        self._theme = theme
        self._ctx = ctx
        self._on_add = on_add
        self._cards: dict[str, _PreviewCard] = {}
        self._filter_cat: str | None = None
        self._query = ""

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_StyledBackground, False)
        self._build()
        grid.capacity_changed.connect(lambda *_: self._sync_states())

    # --- background --------------------------------------------------------
    def paintEvent(self, _e) -> None:  # noqa: N802
        p = QtGui.QPainter(self)
        paint_background(p, self.width(), self.height(), self._theme.tokens)
        scrim = to_qcolor(self._theme.tokens.get("bg", "#0f1117"))
        scrim.setAlpha(150)
        p.fillRect(self.rect(), scrim)
        p.end()

    # --- build -------------------------------------------------------------
    def _build(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(40, 32, 40, 32)
        root.setSpacing(22)

        hdr = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("Widget Store")
        title.setObjectName("Greeting")
        self._badge = QtWidgets.QLabel()
        self._badge.setObjectName("GreetingSub")
        close = QtWidgets.QPushButton("✕")
        close.setFixedSize(40, 40)
        close.setCursor(Qt.PointingHandCursor)
        close.clicked.connect(self.hide)
        hdr.addWidget(title)
        hdr.addSpacing(14)
        hdr.addWidget(self._badge)
        hdr.addStretch(1)
        hdr.addWidget(close)
        root.addLayout(hdr)

        body = QtWidgets.QHBoxLayout()
        body.setSpacing(22)

        # sidebar: search + categories
        side = QtWidgets.QVBoxLayout()
        side.setSpacing(8)
        self._search = QtWidgets.QLineEdit()
        self._search.setPlaceholderText("Search widgets")
        self._search.setFixedWidth(220)
        self._search.textChanged.connect(self._on_search)
        side.addWidget(self._search)

        self._cat_btns: dict[str, QtWidgets.QPushButton] = {}
        cats = ["All"] + sorted({getattr(p, "category", "Information")
                                 for p in self._plugins.values()})
        for cat in cats:
            b = QtWidgets.QPushButton(cat)
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setProperty("chip", True)
            b.setStyleSheet("text-align:left;padding:9px 16px;")
            b.clicked.connect(lambda _=False, c=cat: self._on_cat(c))
            self._cat_btns[cat] = b
            side.addWidget(b)
        side.addStretch(1)
        self._cat_btns["All"].setChecked(True)
        body.addLayout(side)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background:transparent;")
        container = QtWidgets.QWidget()
        container.setStyleSheet("background:transparent;")
        self._grid_lay = QtWidgets.QGridLayout(container)
        self._grid_lay.setSpacing(18)
        self._grid_lay.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        for pid, plugin in sorted(self._plugins.items(),
                                  key=lambda kv: kv[1].name):
            card = _PreviewCard(plugin, self._ctx, self._theme)
            card.add_clicked.connect(self._add)
            self._cards[pid] = card
        scroll.setWidget(container)
        self._container = container
        body.addWidget(scroll, 1)
        root.addLayout(body, 1)

    # --- behaviour ---------------------------------------------------------
    def open_over(self, geo: QtCore.QRect) -> None:
        self.setGeometry(geo)
        self.show()
        self.raise_()
        self.activateWindow()
        self._relayout()
        self._search.setFocus()

    def resizeEvent(self, e) -> None:  # noqa: N802
        self._relayout()
        super().resizeEvent(e)

    def _on_search(self, text: str) -> None:
        self._query = text.strip().lower()
        self._relayout()

    def _on_cat(self, cat: str) -> None:
        self._filter_cat = None if cat == "All" else cat
        for name, b in self._cat_btns.items():
            b.setChecked(name == cat)
        self._relayout()

    def _matches(self, plugin) -> bool:
        if self._filter_cat and getattr(plugin, "category", "") != self._filter_cat:
            return False
        if self._query:
            blob = f"{plugin.name} {plugin.description}".lower()
            return self._query in blob
        return True

    def _relayout(self) -> None:
        avail = max(1, self._container.parent().width() - 28)
        cols = max(1, avail // (_CARD_W + 18))
        for card in self._cards.values():
            self._grid_lay.removeWidget(card)
            card.hide()
        i = 0
        for pid, plugin in sorted(self._plugins.items(),
                                  key=lambda kv: kv[1].name):
            if not self._matches(plugin):
                continue
            card = self._cards[pid]
            self._grid_lay.addWidget(card, i // cols, i % cols)
            card.show()
            i += 1
        self._sync_states()

    def _sync_states(self) -> None:
        from widgets.grid import TOTAL_SLOTS
        used = self._grid.used()
        self._badge.setText(f"{used} / {TOTAL_SLOTS} slots used")
        for pid, card in self._cards.items():
            added = self._grid.has(pid)
            full = (not added) and not self._grid.can_fit(
                tuple(self._plugins[pid].default_size))
            card.set_state(added, full)

    def _add(self, plugin_id: str, size: tuple) -> None:
        self._on_add(plugin_id, size)
        self._sync_states()

    def keyPressEvent(self, e) -> None:  # noqa: N802
        if e.key() == Qt.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(e)
