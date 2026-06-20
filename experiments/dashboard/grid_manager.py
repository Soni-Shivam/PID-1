"""
Snap-to-Slot Grid Manager for JioPC Desktop Shell.

Architecture:
  - 2 rows × 3 columns = 6 base slot units.
  - Widgets declare size as: SMALL(1×1), WIDE(2×1), TALL(1×2), LARGE(2×2).
  - Auto-flow packer: no QGridLayout. Uses a flat 2D occupancy array.
  - Drag: Grid-level eventFilter on ALL child widgets detects press+move,
    then grabMouse() takes over for zero-overhead dashed outline tracking.
  - Swap: Dropping onto occupied cell swaps the two widgets.
  - Card dims to 40% opacity during drag via setGraphicsEffect (not GPU).
  - Remove: Visible ✕ button on each card, connected via remove_request signal.
  - JSON serialisation to ~/.config/jiopc/home/layout.json.

Constraints:
  < 10% idle CPU, no GPU compositing, no box-shadow, no QML.
  #121212 bg, #1E1E1E cards, rgba(255,255,255,0.1) borders, border-radius:12px.
"""
from __future__ import annotations

import json
import os
from enum import Enum
from typing import Dict, List, Optional, Tuple

from core.qt_compat import QtCore, QtGui, QtWidgets
from design_system import card_qss

# ── theming ───────────────────────────────────────────────────────────────────
BG_DEEP  = "#121212"
BG_CARD  = "#1E1E1E"
BORDER_C = "rgba(255,255,255,0.1)"
RADIUS   = 12
SPACING  = 16

GRID_COLS   = 3
GRID_ROWS   = 2
TOTAL_SLOTS = GRID_COLS * GRID_ROWS   # 6

DRAG_THRESHOLD = 8    # px before drag activates


# ── slot size ─────────────────────────────────────────────────────────────────
class SlotSize(Enum):
    SMALL  = (1, 1)
    WIDE   = (2, 1)
    TALL   = (1, 2)
    LARGE  = (2, 2)

    @property
    def col_span(self):   return self.value[0]
    @property
    def row_span(self):   return self.value[1]
    @property
    def slot_count(self): return self.col_span * self.row_span

    @staticmethod
    def from_str(s: str) -> "SlotSize":
        return {"SMALL": SlotSize.SMALL, "WIDE": SlotSize.WIDE,
                "TALL":  SlotSize.TALL,  "LARGE": SlotSize.LARGE}[s.upper()]


# ── occupancy grid ────────────────────────────────────────────────────────────
class OccupancyGrid:
    def __init__(self):
        self._g: List[List[Optional[str]]] = [
            [None] * GRID_ROWS for _ in range(GRID_COLS)
        ]

    def is_free(self, c, r, cs, rs, skip=None) -> bool:
        if c < 0 or r < 0 or c + cs > GRID_COLS or r + rs > GRID_ROWS:
            return False
        for cc in range(c, c + cs):
            for rr in range(r, r + rs):
                occ = self._g[cc][rr]
                if occ is not None and occ != skip:
                    return False
        return True

    def occupants_in(self, c, r, cs, rs, skip=None) -> set:
        """Return set of widget IDs occupying cells in area (excluding skip)."""
        found = set()
        for cc in range(c, c + cs):
            for rr in range(r, r + rs):
                occ = self._g[cc][rr]
                if occ is not None and occ != skip:
                    found.add(occ)
        return found

    def mark(self, c, r, cs, rs, val):
        for cc in range(c, c + cs):
            for rr in range(r, r + rs):
                self._g[cc][rr] = val

    def used_slots(self) -> int:
        return sum(1 for col in self._g for cell in col if cell is not None)

    def free_slots(self) -> int:
        return TOTAL_SLOTS - self.used_slots()

    def find_first_free(self, cs, rs) -> Optional[Tuple[int, int]]:
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                if self.is_free(c, r, cs, rs):
                    return c, r
        return None

    def clear(self):
        for col in self._g:
            for i in range(len(col)):
                col[i] = None

    def dump(self) -> str:
        rows = []
        for r in range(GRID_ROWS):
            rows.append(" | ".join(
                (self._g[c][r] or "·")[:6].ljust(6) for c in range(GRID_COLS)))
        return "\n".join(rows)


# ── base widget card ──────────────────────────────────────────────────────────


_CHROME_BTN = """
    QPushButton {{
        background: {bg};
        color: {fg};
        border: 1px solid {border};
        border-radius: 7px;
        font-size: 13px;
        font-weight: 700;
    }}
    QPushButton:hover   {{ background: {hover}; }}
    QPushButton:pressed {{ background: {press}; }}
"""


def _cbtn(bg="rgba(255,255,255,0.06)", fg="#a1a1aa",
          border="rgba(255,255,255,0.09)", hover="#ffffff22",
          press="#ffffff06") -> str:
    return _CHROME_BTN.format(bg=bg, fg=fg, border=border, hover=hover, press=press)


class BaseWidgetCard(QtWidgets.QFrame):
    """
    Base for every dashboard widget.

    The chrome toolbar (grab handle + expand + remove) floats at the top.
    It only becomes visible on hover to keep the UI clean at rest.
    The SnapGridManager installs itself as an event filter on this card AND
    all of its children via _watch_widget() — that is where drag detection lives.
    """

    size_toggled   = QtCore.pyqtSignal(object)   # emits self
    remove_request = QtCore.pyqtSignal(object)   # emits self

    SUPPORTED_SIZES: List[SlotSize] = [SlotSize.SMALL, SlotSize.WIDE]

    def __init__(self, w_id: str, size: SlotSize = SlotSize.SMALL, parent=None):
        super().__init__(parent)
        self.w_id         = w_id
        self.current_size = size
        self._is_dragging = False

        self.setObjectName("wcard")
        
        # Apply default widget style. Subclasses will overwrite this if they set their own style sheet.
        self.setStyleSheet(f"BaseWidgetCard, QFrame#wcard {{ {card_qss()} }}")

        # ── chrome: hidden by default, shown on hover ─────────────────────
        self._chrome = QtWidgets.QWidget(self)
        self._chrome.setObjectName("chrome")
        self._chrome.setStyleSheet("QWidget#chrome { background: transparent; }")
        self._chrome.hide()

        cl = QtWidgets.QHBoxLayout(self._chrome)
        cl.setContentsMargins(8, 6, 6, 0)
        cl.setSpacing(4)

        # Drag handle label (leftmost — gives users a visual cue)
        handle = QtWidgets.QLabel("⠿")
        handle.setStyleSheet("color: rgba(255,255,255,0.3); font-size: 16px; background: transparent;")
        handle.setCursor(QtCore.Qt.SizeAllCursor)
        handle.setToolTip("Drag to rearrange")

        cl.addWidget(handle)
        cl.addStretch()

        # Expand / collapse
        self._btn_toggle = QtWidgets.QPushButton("⤢")
        self._btn_toggle.setFixedSize(24, 24)
        self._btn_toggle.setToolTip("Resize widget")
        self._btn_toggle.setCursor(QtCore.Qt.PointingHandCursor)
        self._btn_toggle.setStyleSheet(_cbtn())
        self._btn_toggle.clicked.connect(self.toggle_size)

        # Remove
        self._btn_remove = QtWidgets.QPushButton("✕")
        self._btn_remove.setFixedSize(24, 24)
        self._btn_remove.setToolTip("Remove widget")
        self._btn_remove.setCursor(QtCore.Qt.PointingHandCursor)
        self._btn_remove.setStyleSheet(_cbtn(hover="rgba(220,38,38,0.8)",
                                             press="rgba(185,28,28,0.9)"))
        self._btn_remove.clicked.connect(lambda: self.remove_request.emit(self))

        cl.addWidget(self._btn_toggle)
        cl.addWidget(self._btn_remove)

    # ── hover to reveal chrome ────────────────────────────────────────────────
    def enterEvent(self, e):
        self._chrome.show()
        super().enterEvent(e)

    def leaveEvent(self, e):
        # Only hide if cursor actually left the whole card
        gp = QtGui.QCursor.pos()
        if not self.rect().contains(self.mapFromGlobal(gp)):
            self._chrome.hide()
        super().leaveEvent(e)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._chrome.setGeometry(0, 0, self.width(), 34)

    # ── drag visual ──────────────────────────────────────────────────────────
    def set_dragging(self, active: bool):
        self._is_dragging = active
        if active:
            self._chrome.hide()
            eff = QtWidgets.QGraphicsOpacityEffect(self)
            eff.setOpacity(0.4)
            self.setGraphicsEffect(eff)
        else:
            self.setGraphicsEffect(None)

    # ── size toggle ───────────────────────────────────────────────────────────
    def toggle_size(self):
        idx  = self.SUPPORTED_SIZES.index(self.current_size)
        next_sz = self.SUPPORTED_SIZES[(idx + 1) % len(self.SUPPORTED_SIZES)]
        self.current_size = next_sz
        self._btn_toggle.setText("⤡" if next_sz != self.SUPPORTED_SIZES[0] else "⤢")
        self.size_toggled.emit(self)


# ── snap-to-slot grid manager ─────────────────────────────────────────────────
class SnapGridManager(QtWidgets.QWidget):
    """
    Core layout engine.

    Drag detection is handled entirely by this class via eventFilter() installed
    on every widget card and its children. Once threshold is crossed, grabMouse()
    is called so all mouse events route here directly.

    On drop onto occupied cell → SWAP the two widgets.
    On drop onto free cell     → MOVE.
    On drop back to origin     → no change.
    """

    capacity_changed = QtCore.pyqtSignal(int, int)   # (used, total)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("SnapGridManager { background: transparent; }")
        self.setMouseTracking(True)

        self._occ = OccupancyGrid()
        self._reg: Dict[str, dict] = {}   # id → {widget, c, r, cs, rs}

        # drag state
        self._drag_card:   Optional[BaseWidgetCard] = None
        self._drag_press:  Optional[QtCore.QPoint]  = None   # global pos at press
        self._drag_active: bool                     = False
        self._drag_target: Optional[Tuple[int, int]]= None
        self._drag_offset: QtCore.QPoint            = QtCore.QPoint()

    # ── geometry ──────────────────────────────────────────────────────────────
    def _cell_rect(self, c, r, cs, rs) -> QtCore.QRect:
        W, H = self.width(), self.height()
        if W == 0 or H == 0:
            return QtCore.QRect()
        s  = SPACING
        cw = (W - s * (GRID_COLS + 1)) / GRID_COLS
        ch = (H - s * (GRID_ROWS + 1)) / GRID_ROWS
        return QtCore.QRect(
            int(s + c * (cw + s)),
            int(s + r * (ch + s)),
            int(cs * cw + (cs - 1) * s),
            int(rs * ch + (rs - 1) * s),
        )

    def _pixel_to_cell(self, px, py) -> Tuple[int, int]:
        W, H = max(1, self.width()), max(1, self.height())
        s  = SPACING
        cw = (W - s * (GRID_COLS + 1)) / GRID_COLS
        ch = (H - s * (GRID_ROWS + 1)) / GRID_ROWS
        c  = max(0, min(GRID_COLS - 1, int((px - s) / (cw + s))))
        r  = max(0, min(GRID_ROWS - 1, int((py - s) / (ch + s))))
        return c, r

    # ── reflow ────────────────────────────────────────────────────────────────
    def _reflow(self):
        for wid, d in self._reg.items():
            rect = self._cell_rect(d["c"], d["r"], d["cs"], d["rs"])
            if rect.isValid():
                d["widget"].setGeometry(rect)
                d["widget"].raise_()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._reflow()

    # ── public API ────────────────────────────────────────────────────────────
    def slots_used(self)          -> int:  return self._occ.used_slots()
    def slots_free(self)          -> int:  return self._occ.free_slots()
    def can_fit(self, sz: SlotSize) -> bool: return self._occ.find_first_free(sz.col_span, sz.row_span) is not None

    def add_widget(self, card: BaseWidgetCard, c=-1, r=-1) -> bool:
        sz = card.current_size
        cs, rs = sz.col_span, sz.row_span

        if c < 0 or r < 0:
            pos = self._occ.find_first_free(cs, rs)
            if pos is None:
                return False
            c, r = pos
        elif not self._occ.is_free(c, r, cs, rs):
            pos = self._occ.find_first_free(cs, rs)
            if pos is None:
                return False
            c, r = pos

        self._reg[card.w_id] = {"widget": card, "c": c, "r": r, "cs": cs, "rs": rs}
        self._occ.mark(c, r, cs, rs, card.w_id)

        card.setParent(self)
        card.size_toggled.connect(self._on_size_toggled)
        card.remove_request.connect(self._on_remove)
        self._watch_widget(card)   # install event filter for drag detection
        card.show()

        QtCore.QTimer.singleShot(0, self._reflow)
        self.capacity_changed.emit(self.slots_used(), TOTAL_SLOTS)
        return True

    def remove_widget(self, card: BaseWidgetCard):
        wid = card.w_id
        if wid not in self._reg:
            return
        d = self._reg.pop(wid)
        self._occ.mark(d["c"], d["r"], d["cs"], d["rs"], None)
        card.setParent(None)
        card.deleteLater()
        self.capacity_changed.emit(self.slots_used(), TOTAL_SLOTS)

    def clear_all(self):
        for d in list(self._reg.values()):
            d["widget"].setParent(None)
            d["widget"].deleteLater()
        self._reg.clear()
        self._occ.clear()
        self.capacity_changed.emit(0, TOTAL_SLOTS)

    # ── event filter: installed on every widget + child ───────────────────────
    def _watch_widget(self, card: BaseWidgetCard):
        card.installEventFilter(self)
        for child in card.findChildren(QtWidgets.QWidget):
            child.installEventFilter(self)

    def _card_for(self, obj: QtWidgets.QWidget) -> Optional[BaseWidgetCard]:
        """Walk up parent chain to find which registered BaseWidgetCard owns obj."""
        w = obj
        while w is not None:
            if isinstance(w, BaseWidgetCard) and w.w_id in self._reg:
                return w
            w = w.parent() if isinstance(w, QtWidgets.QWidget) else None
        return None

    def eventFilter(self, obj, event):
        t = event.type()

        # ── press: record start position (don't consume — let buttons work) ─
        if t == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.LeftButton:
            # Don't hijack button clicks
            if isinstance(obj, QtWidgets.QPushButton):
                return super().eventFilter(obj, event)
            card = self._card_for(obj)
            if card:
                self._drag_card   = card
                self._drag_press  = obj.mapToGlobal(event.pos())
                self._drag_active = False
                self._drag_target = None
            return False   # don't consume — child widgets still receive it

        # ── move: activate drag after threshold ──────────────────────────────
        elif t == QtCore.QEvent.MouseMove:
            if self._drag_card and self._drag_press and not self._drag_active:
                if isinstance(obj, QtWidgets.QPushButton):
                    return False
                card = self._card_for(obj)
                if card and card.w_id == self._drag_card.w_id:
                    gp   = obj.mapToGlobal(event.pos())
                    dist = (gp - self._drag_press).manhattanLength()
                    if dist > DRAG_THRESHOLD:
                        self._drag_active = True
                        self._drag_card.set_dragging(True)
                        # Pre-compute offset for snapping
                        lp = self.mapFromGlobal(self._drag_press)
                        d  = self._reg[self._drag_card.w_id]
                        self._drag_offset = QtCore.QPoint(
                            lp.x() - self._cell_rect(d["c"], d["r"], d["cs"], d["rs"]).x(),
                            lp.y() - self._cell_rect(d["c"], d["r"], d["cs"], d["rs"]).y(),
                        )
                        self.grabMouse()  # ← all subsequent events come to grid
            return False

        # ── release: handled by mouseReleaseEvent after grabMouse ────────────
        return super().eventFilter(obj, event)

    # ── live drag tracking (after grabMouse) ──────────────────────────────────
    def mouseMoveEvent(self, e):
        if not (self._drag_active and self._drag_card):
            return
        d  = self._reg.get(self._drag_card.w_id)
        if not d:
            return
        lp = e.pos() - self._drag_offset
        tc, tr = self._pixel_to_cell(lp.x() + self._cell_width() * d["cs"] // 2,
                                     lp.y() + self._cell_height() * d["rs"] // 2)
        tc = min(tc, GRID_COLS - d["cs"])
        tr = min(tr, GRID_ROWS - d["rs"])
        if (tc, tr) != self._drag_target:
            self._drag_target = (tc, tr)
            self.update()   # repaint dashed outline only

    def mouseReleaseEvent(self, e):
        if not (self._drag_active and self._drag_card):
            self._drag_card  = None
            self._drag_press = None
            return
        self.releaseMouse()

        card = self._drag_card
        wid  = card.w_id
        card.set_dragging(False)

        if self._drag_target and wid in self._reg:
            d      = self._reg[wid]
            tc, tr = self._drag_target
            cs, rs = d["cs"], d["rs"]
            oc, or_ = d["c"], d["r"]

            if (tc, tr) != (oc, or_):   # actually moved
                occupants = self._occ.occupants_in(tc, tr, cs, rs, skip=wid)

                if not occupants:
                    # Simple move into free space
                    self._occ.mark(oc, or_, cs, rs, None)
                    d["c"], d["r"] = tc, tr
                    self._occ.mark(tc, tr, cs, rs, wid)

                elif len(occupants) == 1:
                    # Swap with exactly one neighbour (same size only for safety)
                    other_id = next(iter(occupants))
                    other_d  = self._reg[other_id]
                    if other_d["cs"] == cs and other_d["rs"] == rs:
                        # Swap occupancy
                        self._occ.mark(oc, or_, cs, rs, other_id)
                        self._occ.mark(tc, tr, cs, rs, wid)
                        other_d["c"], other_d["r"] = oc, or_
                        d["c"], d["r"] = tc, tr
                    # else: incompatible sizes — revert (do nothing)
                # else: multiple occupants — revert (do nothing)

        self._drag_card   = None
        self._drag_press  = None
        self._drag_active = False
        self._drag_target = None
        self._reflow()
        self.update()

    def _cell_width(self) -> int:
        s = SPACING
        return max(1, int((self.width() - s * (GRID_COLS + 1)) / GRID_COLS))

    def _cell_height(self) -> int:
        s = SPACING
        return max(1, int((self.height() - s * (GRID_ROWS + 1)) / GRID_ROWS))

    # ── painting ──────────────────────────────────────────────────────────────
    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        # ── draw grid slot outlines (faint) so user sees the slots ───────────
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                rect = self._cell_rect(c, r, 1, 1)
                if rect.isValid():
                    p.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 8), 1,
                                        QtCore.Qt.DotLine))
                    p.setBrush(QtCore.Qt.NoBrush)
                    p.drawRoundedRect(rect, RADIUS, RADIUS)

        # ── drag target outline ───────────────────────────────────────────────
        if self._drag_active and self._drag_card and self._drag_target:
            d = self._reg.get(self._drag_card.w_id)
            if d:
                tc, tr = self._drag_target
                rect   = self._cell_rect(tc, tr, d["cs"], d["rs"])
                if rect.isValid():
                    occupants = self._occ.occupants_in(tc, tr, d["cs"], d["rs"],
                                                       skip=self._drag_card.w_id)
                    # Colour: white = free/swappable, orange = multi-occupant
                    if not occupants:
                        colour = QtGui.QColor(255, 255, 255, 150)
                    elif len(occupants) == 1:
                        colour = QtGui.QColor(251, 191, 36, 200)   # amber = swap
                    else:
                        colour = QtGui.QColor(239, 68, 68, 200)    # red = blocked

                    fill = QtGui.QColor(colour)
                    fill.setAlpha(22)
                    p.fillRect(rect, fill)

                    pen = QtGui.QPen(colour, 2, QtCore.Qt.DashLine)
                    pen.setDashPattern([6, 4])
                    p.setPen(pen)
                    p.setBrush(QtCore.Qt.NoBrush)
                    p.drawRoundedRect(rect, RADIUS, RADIUS)

    # ── size toggle ───────────────────────────────────────────────────────────
    def _on_size_toggled(self, card: BaseWidgetCard):
        wid = card.w_id
        if wid not in self._reg:
            return
        d = self._reg[wid]
        old_c, old_r, old_cs, old_rs = d["c"], d["r"], d["cs"], d["rs"]
        ncs, nrs = card.current_size.col_span, card.current_size.row_span

        self._occ.mark(old_c, old_r, old_cs, old_rs, None)

        if self._occ.is_free(old_c, old_r, ncs, nrs):
            d["cs"], d["rs"] = ncs, nrs
            self._occ.mark(old_c, old_r, ncs, nrs, wid)
        else:
            pos = self._occ.find_first_free(ncs, nrs)
            if pos:
                d["c"], d["r"], d["cs"], d["rs"] = pos[0], pos[1], ncs, nrs
                self._occ.mark(pos[0], pos[1], ncs, nrs, wid)
            else:
                # Revert
                prev = card.SUPPORTED_SIZES[
                    (card.SUPPORTED_SIZES.index(card.current_size) - 1)
                    % len(card.SUPPORTED_SIZES)
                ]
                card.current_size = prev
                d["cs"], d["rs"] = old_cs, old_rs
                self._occ.mark(old_c, old_r, old_cs, old_rs, wid)

        self._reflow()
        self.capacity_changed.emit(self.slots_used(), TOTAL_SLOTS)

    def _on_remove(self, card: BaseWidgetCard):
        self.remove_widget(card)
        self._reflow()
        self.save_layout()

    # ── JSON ──────────────────────────────────────────────────────────────────
    def save_layout(self):
        conf = os.path.expanduser("~/.config/jiopc/home")
        os.makedirs(conf, exist_ok=True)
        path = os.path.join(conf, "layout.json")
        data = {
            "version": 2,
            "grid": {"cols": GRID_COLS, "rows": GRID_ROWS},
            "widgets": [
                {"id": wid, "col": d["c"], "row": d["r"],
                 "col_span": d["cs"], "row_span": d["rs"],
                 "size": d["widget"].current_size.name}
                for wid, d in self._reg.items()
            ],
        }
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as ex:
            print(f"[Grid] Save failed: {ex}")

    def load_layout(self, factory) -> bool:
        path = os.path.expanduser("~/.config/jiopc/home/layout.json")
        if not os.path.exists(path):
            return False
        try:
            with open(path) as f:
                data = json.load(f)
            entries = data.get("widgets", [])
            for e in entries:
                sz   = SlotSize.from_str(e.get("size", "SMALL"))
                card = factory(e["id"], sz)
                if card:
                    self.add_widget(card, c=e["col"], r=e["row"])
            return bool(entries)
        except Exception as ex:
            print(f"[Grid] Load failed: {ex}")
            return False
