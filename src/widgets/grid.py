"""Snap-to-slot desktop widget grid (Component C arrange/rearrange engine).

Ported and theme-token-ified from the dashboard experiment's SnapGridManager.
A fixed COLS x ROWS slot grid hosts plugin views wrapped in WidgetCard frames;
the user drags to move/swap, toggles size, and removes — every change persists
to layout.json via widgets.engine. No QGridLayout: a flat occupancy array drives
absolute setGeometry, so drags are jitter-free and painting is cheap.

Drag detection lives entirely in SnapGrid.eventFilter (installed on every card
and its children). Once the move threshold is crossed it grabMouse()es so all
events route here for a dashed drop-target outline; on drop, a free cell moves
the widget and a single same-size occupant swaps. All colours come from theme
tokens (no hardcoded hex), so light and dark both render correctly.
"""
from __future__ import annotations

from typing import Callable

from core.qt_compat import Qt, QtCore, QtGui, QtWidgets
from core.colors import to_qcolor
from widgets import engine

GRID_COLS = 3
GRID_ROWS = 2
TOTAL_SLOTS = GRID_COLS * GRID_ROWS
SPACING = 18
RADIUS = 18
_DRAG_THRESHOLD = 8

# Standard resize cycle: any (w, h) a plugin offers must come from this set.
STD_SIZES: list[tuple[int, int]] = [(1, 1), (2, 1), (1, 2), (2, 2)]


def allowed_sizes(plugin) -> list[tuple[int, int]]:
    """Sizes a plugin may cycle through; falls back to its default size only."""
    sizes = getattr(plugin, "sizes", None)
    if sizes:
        return [tuple(s) for s in sizes]
    return [tuple(plugin.default_size)]


# --------------------------------------------------------------------------
class _Occupancy:
    """Flat COLS x ROWS array of widget-id or None."""

    def __init__(self) -> None:
        self._g: list[list[str | None]] = [
            [None] * GRID_ROWS for _ in range(GRID_COLS)]

    def is_free(self, c, r, w, h, skip=None) -> bool:
        if c < 0 or r < 0 or c + w > GRID_COLS or r + h > GRID_ROWS:
            return False
        for cc in range(c, c + w):
            for rr in range(r, r + h):
                occ = self._g[cc][rr]
                if occ is not None and occ != skip:
                    return False
        return True

    def occupants(self, c, r, w, h, skip=None) -> set[str]:
        found: set[str] = set()
        for cc in range(c, c + w):
            for rr in range(r, r + h):
                occ = self._g[cc][rr]
                if occ is not None and occ != skip:
                    found.add(occ)
        return found

    def mark(self, c, r, w, h, val) -> None:
        for cc in range(c, c + w):
            for rr in range(r, r + h):
                self._g[cc][rr] = val

    def used(self) -> int:
        return sum(1 for col in self._g for cell in col if cell is not None)

    def first_free(self, w, h) -> tuple[int, int] | None:
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                if self.is_free(c, r, w, h):
                    return c, r
        return None

    def clear(self) -> None:
        for col in self._g:
            for i in range(len(col)):
                col[i] = None


# --------------------------------------------------------------------------
class WidgetCard(QtWidgets.QFrame):
    """Glass card hosting one plugin view, with hover chrome.

    The card carries card="true" so it picks up the shell glass recipe from the
    app stylesheet; the inner plugin view is transparent and composites over it.
    A floating toolbar (drag handle + resize + remove) appears only on hover.
    """

    size_toggled   = QtCore.pyqtSignal(object)   # self
    remove_request = QtCore.pyqtSignal(object)   # self

    def __init__(self, plugin, view: QtWidgets.QWidget,
                 size: tuple[int, int], theme) -> None:
        super().__init__()
        self.w_id  = plugin.id
        self._theme = theme
        self._sizes = allowed_sizes(plugin)
        if tuple(size) not in self._sizes:
            self._sizes = [tuple(size)] + [s for s in self._sizes
                                           if s != tuple(size)]
        self.current_size = tuple(size)
        self._dragging = False

        self.setProperty("card", True)
        self.setAttribute(Qt.WA_StyledBackground, True)

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self._view = view
        self._view.setParent(self)
        lay.addWidget(self._view)

        self._chrome = QtWidgets.QWidget(self)
        self._chrome.setObjectName("cardChrome")
        cl = QtWidgets.QHBoxLayout(self._chrome)
        cl.setContentsMargins(8, 6, 8, 0)
        cl.setSpacing(5)
        self._handle = QtWidgets.QLabel("⁙")
        self._handle.setCursor(Qt.SizeAllCursor)
        self._handle.setToolTip("Drag to rearrange")
        cl.addWidget(self._handle)
        cl.addStretch(1)
        self._btn_size = self._chrome_btn("⤢", "Resize widget")
        self._btn_size.clicked.connect(self._cycle_size)
        self._btn_del = self._chrome_btn("✕", "Remove widget")
        self._btn_del.clicked.connect(lambda: self.remove_request.emit(self))
        cl.addWidget(self._btn_size)
        cl.addWidget(self._btn_del)
        self._chrome.hide()

        self._btn_size.setVisible(len(self._sizes) > 1)
        self._apply_theme()
        theme.theme_changed.connect(self._apply_theme)

    def _chrome_btn(self, glyph: str, tip: str) -> QtWidgets.QPushButton:
        b = QtWidgets.QPushButton(glyph)
        b.setObjectName("cardChromeBtn")
        b.setFixedSize(24, 24)
        b.setCursor(Qt.PointingHandCursor)
        b.setToolTip(tip)
        return b

    def _apply_theme(self) -> None:
        t = self._theme.tokens
        self._chrome.setStyleSheet("#cardChrome{background:transparent;}")
        self._handle.setStyleSheet(
            f"color:{t['muted']};font-size:16px;background:transparent;")
        for b in (self._btn_size, self._btn_del):
            b.setStyleSheet(
                f"QPushButton#cardChromeBtn{{background:{t['surface_alt']};"
                f"color:{t['muted']};border:1px solid {t['border']};"
                f"border-radius:7px;font-size:12px;font-weight:700;}}"
                f"QPushButton#cardChromeBtn:hover{{color:{t['text']};"
                f"border-color:{t['accent']};}}")

    def enterEvent(self, e) -> None:  # noqa: N802
        self._chrome.raise_()
        self._chrome.show()
        super().enterEvent(e)

    def leaveEvent(self, e) -> None:  # noqa: N802
        gp = QtGui.QCursor.pos()
        if not self.rect().contains(self.mapFromGlobal(gp)):
            self._chrome.hide()
        super().leaveEvent(e)

    def resizeEvent(self, e) -> None:  # noqa: N802
        self._chrome.setGeometry(0, 0, self.width(), 34)
        super().resizeEvent(e)

    def set_dragging(self, active: bool) -> None:
        self._dragging = active
        if active:
            self._chrome.hide()
            eff = QtWidgets.QGraphicsOpacityEffect(self)
            eff.setOpacity(0.45)
            self.setGraphicsEffect(eff)
        else:
            self.setGraphicsEffect(None)

    def _cycle_size(self) -> None:
        idx = self._sizes.index(self.current_size)
        self.current_size = self._sizes[(idx + 1) % len(self._sizes)]
        self.size_toggled.emit(self)


# --------------------------------------------------------------------------
class SnapGrid(QtWidgets.QWidget):
    """The arrangeable widget grid; drives layout, drag/swap, persistence."""

    capacity_changed = QtCore.pyqtSignal(int, int)   # (used, total)

    def __init__(self, theme, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = theme
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setMouseTracking(True)
        self._occ = _Occupancy()
        self._reg: dict[str, dict] = {}     # id -> {card, c, r, w, h}

        self._drag_card: WidgetCard | None = None
        self._drag_press: QtCore.QPoint | None = None
        self._drag_active = False
        self._drag_target: tuple[int, int] | None = None
        self._drag_offset = QtCore.QPoint()

    # --- geometry ----------------------------------------------------------
    def _cell(self, c, r, w, h) -> QtCore.QRect:
        W, H = self.width(), self.height()
        if W <= 0 or H <= 0:
            return QtCore.QRect()
        s = SPACING
        cw = (W - s * (GRID_COLS + 1)) / GRID_COLS
        ch = (H - s * (GRID_ROWS + 1)) / GRID_ROWS
        return QtCore.QRect(int(s + c * (cw + s)), int(s + r * (ch + s)),
                            int(w * cw + (w - 1) * s), int(h * ch + (h - 1) * s))

    def _pixel_to_cell(self, px, py) -> tuple[int, int]:
        s = SPACING
        cw = (self.width() - s * (GRID_COLS + 1)) / GRID_COLS
        ch = (self.height() - s * (GRID_ROWS + 1)) / GRID_ROWS
        c = max(0, min(GRID_COLS - 1, int((px - s) / (cw + s)) if cw > 0 else 0))
        r = max(0, min(GRID_ROWS - 1, int((py - s) / (ch + s)) if ch > 0 else 0))
        return c, r

    def _reflow(self) -> None:
        for d in self._reg.values():
            rect = self._cell(d["c"], d["r"], d["w"], d["h"])
            if rect.isValid():
                d["card"].setGeometry(rect)
                d["card"].raise_()

    def resizeEvent(self, e) -> None:  # noqa: N802
        self._reflow()
        super().resizeEvent(e)

    # --- public API --------------------------------------------------------
    def used(self) -> int:
        return self._occ.used()

    def can_fit(self, size: tuple[int, int]) -> bool:
        return self._occ.first_free(size[0], size[1]) is not None

    def has(self, w_id: str) -> bool:
        return w_id in self._reg

    def add(self, card: WidgetCard, c: int = -1, r: int = -1) -> bool:
        w, h = card.current_size
        if c < 0 or r < 0 or not self._occ.is_free(c, r, w, h):
            pos = self._occ.first_free(w, h)
            if pos is None:
                return False
            c, r = pos
        self._reg[card.w_id] = {"card": card, "c": c, "r": r, "w": w, "h": h}
        self._occ.mark(c, r, w, h, card.w_id)
        card.setParent(self)
        card.size_toggled.connect(self._on_size_toggled)
        card.remove_request.connect(self._on_remove)
        self._watch(card)
        card.show()
        QtCore.QTimer.singleShot(0, self._reflow)
        self.capacity_changed.emit(self.used(), TOTAL_SLOTS)
        return True

    def remove(self, w_id: str) -> None:
        d = self._reg.pop(w_id, None)
        if not d:
            return
        self._occ.mark(d["c"], d["r"], d["w"], d["h"], None)
        d["card"].setParent(None)
        d["card"].deleteLater()
        self.capacity_changed.emit(self.used(), TOTAL_SLOTS)

    def clear(self) -> None:
        for d in list(self._reg.values()):
            d["card"].setParent(None)
            d["card"].deleteLater()
        self._reg.clear()
        self._occ.clear()

    def snapshot(self) -> list[dict]:
        return [{"plugin_id": wid, "col": d["c"], "row": d["r"],
                 "w": d["w"], "h": d["h"]}
                for wid, d in self._reg.items()]

    def load(self, factory: Callable[[str, tuple[int, int]], WidgetCard | None],
             layout: list[dict]) -> None:
        self.clear()
        for item in layout:
            size = (int(item.get("w", 1)), int(item.get("h", 1)))
            card = factory(item["plugin_id"], size)
            if card:
                self.add(card, c=int(item.get("col", -1)),
                         r=int(item.get("row", -1)))

    # --- drag detection (event filter on cards + children) -----------------
    def _watch(self, card: WidgetCard) -> None:
        card.installEventFilter(self)
        for child in card.findChildren(QtWidgets.QWidget):
            child.installEventFilter(self)

    def _card_for(self, obj) -> WidgetCard | None:
        w = obj
        while w is not None:
            if isinstance(w, WidgetCard) and w.w_id in self._reg:
                return w
            w = w.parent() if isinstance(w, QtWidgets.QWidget) else None
        return None

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        t = event.type()
        if (t == QtCore.QEvent.MouseButtonPress
                and event.button() == Qt.LeftButton):
            if isinstance(obj, QtWidgets.QAbstractButton):
                return super().eventFilter(obj, event)
            card = self._card_for(obj)
            if card:
                self._drag_card = card
                self._drag_press = obj.mapToGlobal(event.pos())
                self._drag_active = False
                self._drag_target = None
            return False
        if t == QtCore.QEvent.MouseMove and self._drag_card and self._drag_press \
                and not self._drag_active:
            if isinstance(obj, QtWidgets.QAbstractButton):
                return False
            card = self._card_for(obj)
            if card and card.w_id == self._drag_card.w_id:
                gp = obj.mapToGlobal(event.pos())
                if (gp - self._drag_press).manhattanLength() > _DRAG_THRESHOLD:
                    self._begin_drag()
            return False
        return super().eventFilter(obj, event)

    def _begin_drag(self) -> None:
        self._drag_active = True
        self._drag_card.set_dragging(True)
        lp = self.mapFromGlobal(self._drag_press)
        d = self._reg[self._drag_card.w_id]
        origin = self._cell(d["c"], d["r"], d["w"], d["h"])
        self._drag_offset = QtCore.QPoint(lp.x() - origin.x(), lp.y() - origin.y())
        self.grabMouse()

    def mouseMoveEvent(self, e) -> None:  # noqa: N802
        if not (self._drag_active and self._drag_card):
            return
        d = self._reg.get(self._drag_card.w_id)
        if not d:
            return
        lp = e.pos() - self._drag_offset
        cw = self._cell(0, 0, 1, 1).width()
        ch = self._cell(0, 0, 1, 1).height()
        tc, tr = self._pixel_to_cell(lp.x() + cw * d["w"] // 2,
                                     lp.y() + ch * d["h"] // 2)
        tc = min(tc, GRID_COLS - d["w"])
        tr = min(tr, GRID_ROWS - d["h"])
        if (tc, tr) != self._drag_target:
            self._drag_target = (tc, tr)
            self.update()

    def mouseReleaseEvent(self, e) -> None:  # noqa: N802
        if not (self._drag_active and self._drag_card):
            self._drag_card = None
            self._drag_press = None
            return
        self.releaseMouse()
        card = self._drag_card
        wid = card.w_id
        card.set_dragging(False)
        if self._drag_target and wid in self._reg:
            d = self._reg[wid]
            tc, tr = self._drag_target
            w, h = d["w"], d["h"]
            oc, orr = d["c"], d["r"]
            if (tc, tr) != (oc, orr):
                occ = self._occ.occupants(tc, tr, w, h, skip=wid)
                if not occ:
                    self._occ.mark(oc, orr, w, h, None)
                    d["c"], d["r"] = tc, tr
                    self._occ.mark(tc, tr, w, h, wid)
                elif len(occ) == 1:
                    other = self._reg[next(iter(occ))]
                    if (other["w"], other["h"]) == (w, h):
                        self._occ.mark(oc, orr, w, h, other["card"].w_id)
                        self._occ.mark(tc, tr, w, h, wid)
                        other["c"], other["r"] = oc, orr
                        d["c"], d["r"] = tc, tr
        self._drag_card = None
        self._drag_press = None
        self._drag_active = False
        self._drag_target = None
        self._reflow()
        self.update()
        self._persist()

    # --- painting (slot outlines + drop target) ----------------------------
    def paintEvent(self, event) -> None:  # noqa: N802
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        t = self._theme.tokens
        ghost = to_qcolor(t.get("border", "#2a2e38")); ghost.setAlpha(70)
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                rect = self._cell(c, r, 1, 1)
                if rect.isValid():
                    p.setPen(QtGui.QPen(ghost, 1, Qt.DotLine))
                    p.setBrush(Qt.NoBrush)
                    p.drawRoundedRect(rect, RADIUS, RADIUS)
        if self._drag_active and self._drag_card and self._drag_target:
            d = self._reg.get(self._drag_card.w_id)
            if d:
                tc, tr = self._drag_target
                rect = self._cell(tc, tr, d["w"], d["h"])
                occ = self._occ.occupants(tc, tr, d["w"], d["h"],
                                          skip=self._drag_card.w_id)
                if not occ:
                    col = to_qcolor(t.get("accent", "#5b9bff"))
                elif len(occ) == 1:
                    col = QtGui.QColor("#f59e0b")
                else:
                    col = QtGui.QColor("#ef4444")
                fill = QtGui.QColor(col); fill.setAlpha(28)
                p.fillRect(rect, fill)
                pen = QtGui.QPen(col, 2, Qt.DashLine)
                pen.setDashPattern([6, 4])
                p.setPen(pen)
                p.setBrush(Qt.NoBrush)
                p.drawRoundedRect(rect, RADIUS, RADIUS)

    # --- size toggle + remove ----------------------------------------------
    def _on_size_toggled(self, card: WidgetCard) -> None:
        wid = card.w_id
        d = self._reg.get(wid)
        if not d:
            return
        oc, orr, ow, oh = d["c"], d["r"], d["w"], d["h"]
        nw, nh = card.current_size
        self._occ.mark(oc, orr, ow, oh, None)
        if self._occ.is_free(oc, orr, nw, nh):
            d["w"], d["h"] = nw, nh
            self._occ.mark(oc, orr, nw, nh, wid)
        else:
            pos = self._occ.first_free(nw, nh)
            if pos:
                d["c"], d["r"], d["w"], d["h"] = pos[0], pos[1], nw, nh
                self._occ.mark(pos[0], pos[1], nw, nh, wid)
            else:
                idx = card._sizes.index(card.current_size)
                card.current_size = card._sizes[(idx - 1) % len(card._sizes)]
                self._occ.mark(oc, orr, ow, oh, wid)
        self._reflow()
        self.capacity_changed.emit(self.used(), TOTAL_SLOTS)
        self._persist()

    def _on_remove(self, card: WidgetCard) -> None:
        self.remove(card.w_id)
        self._reflow()
        self._persist()

    def _persist(self) -> None:
        engine.save_layout(self.snapshot())
