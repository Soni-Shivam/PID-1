"""Dock widget — macOS-style magnifying dock.

Magnification model (target state -> rendered state -> dt interpolation):

  Every button has a RESTING centre (`_base_center`) inside a fixed-width
  window.  Each animation frame computes a mathematical TARGET (scale +
  horizontal translation) from the cursor's 1-D X distance, then moves the
  RENDERED state toward it with time-delta interpolation for a fluid feel.

    1. proximity      p = 1 - dx/THRESHOLD          (dx = |cursor_x - center_x|)
    2. quad ease-out  raw = SCALE_MAX * p*(2-p)
    3. clamp          target_scale = max(1.0, raw)
    4. spread         magnified icons push neighbours apart (no overlap)
    5. compensation   counter-translate so the hot icon stays under the cursor
    6. interpolate    cur += (target - cur) * (LERP_SPEED * dt)

  Buttons are placed by absolute `setGeometry`; the box BOTTOM always sits on
  `_BTN_BASE_Y` (bottom-centre pivot) so icons magnify upward from a flat
  baseline and never leave the floor.  The frame timer runs only while the
  dock is animating and stops the instant it settles, so idle CPU stays ~0%.

  The window is masked each frame to: pill rounded-rect  ∪  per-button
  overflow rects above the pill — so the X11 desktop shows between floating
  icons with no compositor.
"""
from __future__ import annotations

import time

from core.qt_compat import Qt, QtCore, QtGui, QtWidgets
from core import x11
from core.background import paint_background
from core.theme import ThemeManager
from apps import launcher
from dock.model import DockModel

# --- geometry -------------------------------------------------------
BTN       = 48
ICON_SIZE = 34
PAD       = 12
SPACING   = 8
GAP       = 10
RADIUS    = 18
DOT       = 5
DOT_HALO  = 10

# --- magnification (target state + dt interpolation) ----------------
MAGNIFY_FACTOR  = 0.65                   # peak extra scale
SCALE_MAX       = 1.0 + MAGNIFY_FACTOR   # icon-under-cursor multiplier (1.65)
SPREAD_FACTOR   = 0.5                    # how far neighbours part
THRESHOLD       = (BTN + 10) * 2.5       # 1-D activation radius px (= 145)
SPREAD_HEADROOM = 4 * BTN                # spare window width for the spread

FRAME_MS   = 16            # ~60 fps animation tick
LERP_SPEED = 22.0          # state approach speed (per second)
EPS_SCALE  = 0.01          # settle thresholds
EPS_TX     = 0.5

BTN_MAX   = round(BTN * SCALE_MAX)        # peak box px  (79)
ICON_MAX  = round(ICON_SIZE * SCALE_MAX)  # peak icon px (56)

# --- two-layer heights ----------------------------------------------
PILL_H = BTN + 2 * PAD          # 72 px — the shelf (background bar)
WIN_H  = BTN_MAX + 2 * PAD      # window height (room for magnified boxes)

_PILL_TOP   = WIN_H - PILL_H    # top of the pill within the window
_BTN_BASE_Y = WIN_H - PAD       # baseline: every button BOTTOM sits here

# --- drag -----------------------------------------------------------
_DRAG_THRESH = 6
_MIME        = "application/x-jiopc-dock-app"

# ────────────────────────────────────────────────────────────────────
class DockButton(QtWidgets.QToolButton):
    """Dock icon.

    Holds its own rendered magnification state (`_cur_scale`, `_cur_tx`) and
    resting centre (`_base_center`); the DockWindow animator writes these and
    repositions the button by absolute geometry.  The icon is painted pinned
    to the box BOTTOM so its base stays level with the dock floor at any scale.
    """

    activated    = QtCore.pyqtSignal(str)
    context      = QtCore.pyqtSignal(str, QtCore.QPoint)
    drop_reorder = QtCore.pyqtSignal(str, str)

    def __init__(self, app_id: str, name: str, icon: QtGui.QIcon,
                 theme: ThemeManager) -> None:
        super().__init__()
        self.app_id   = app_id
        self._icon    = icon
        self._theme   = theme
        self._running = False
        self._drag_start: QtCore.QPoint | None = None

        # rendered (interpolated) magnification state + resting centre-x
        self._cur_scale   = 1.0
        self._cur_tx      = 0.0
        self._base_center = 0

        # High-res base pixmap rendered once; every frame scales DOWN from
        # this to the target size, so magnified icons grow uniformly and
        # crisply and never float (QIcon would cap raster icons short).
        self._base_pm = icon.pixmap(QtCore.QSize(ICON_MAX * 2, ICON_MAX * 2))

        self.setIcon(icon)
        self.setIconSize(QtCore.QSize(ICON_SIZE, ICON_SIZE))
        self.resize(BTN, BTN)
        self.setToolTip(name)
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("dockbtn", True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setAcceptDrops(True)
        # We paint EVERY pixel of the box ourselves (background + icon), so the
        # widget is fully opaque — no reliance on see-through, which is what
        # left a square box poking above the shelf.
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)

        self.clicked.connect(lambda: self.activated.emit(self.app_id))
        self.customContextMenuRequested.connect(
            lambda pos: self.context.emit(self.app_id, self.mapToGlobal(pos)))

    # ------------------------------------------------------------------
    def set_running(self, running: bool) -> None:
        if running != self._running:
            self._running = running
            self.update()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802
        """Paint the box background, then the icon anchored bottom-centre.

        The box straddles two zones: above the shelf line it reproduces the
        EXACT desktop background (screen-aligned), below it fills the pill
        colour.  So a magnified box poking above the shelf is pixel-identical
        to the desktop behind it — no square shows — while the icon itself,
        pinned by its own bottom edge, stays grounded as it magnifies upward.
        """
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        t        = self._theme.tokens
        boundary = max(0, min(self.height(), _PILL_TOP - self.y()))  # shelf line

        # below the shelf line: pill colour (seamless with the pill shelf)
        if boundary < self.height():
            p.fillRect(0, boundary, self.width(), self.height() - boundary,
                       QtGui.QColor(t.get("dock_bg", t.get("surface", "#181b22"))))
        # above the shelf line: the desktop's own background, screen-aligned
        if boundary > 0:
            gpos = self.mapToGlobal(QtCore.QPoint(0, 0))
            sc   = QtWidgets.QApplication.primaryScreen().geometry()
            p.save()
            p.setClipRect(0, 0, self.width(), boundary)
            paint_background(p, sc.width(), sc.height(), t, -gpos.x(), -gpos.y())
            p.restore()

        target  = self.iconSize().width()            # grows with magnification
        pm      = self._base_pm.scaled(
            target, target, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        dot_res = (DOT_HALO // 2 + 6) if self._running else 4
        icon_x  = (self.width()  - pm.width())  // 2
        icon_y  = self.height() - pm.height() - dot_res   # pin ACTUAL bottom
        p.drawPixmap(icon_x, max(0, icon_y), pm)

        if self._running:
            t      = self._theme.tokens
            accent = QtGui.QColor(t.get("indicator", "#5b9bff"))
            halo   = QtGui.QColor(accent); halo.setAlpha(55)
            cx = self.width() // 2
            cy = self.height() - DOT_HALO // 2 - 3
            p.setBrush(halo); p.setPen(Qt.NoPen)
            p.drawEllipse(cx - DOT_HALO//2, cy - DOT_HALO//2, DOT_HALO, DOT_HALO)
            p.setBrush(accent)
            p.drawEllipse(cx - DOT//2, cy - DOT//2, DOT, DOT)

    # --- drag source --------------------------------------------------
    def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:  # noqa: N802
        if e.button() == Qt.LeftButton:
            self._drag_start = e.pos()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QtGui.QMouseEvent) -> None:  # noqa: N802
        if (e.buttons() & Qt.LeftButton and self._drag_start is not None
                and (e.pos() - self._drag_start).manhattanLength() >= _DRAG_THRESH):
            self._drag_start = None; self._start_drag(); return
        super().mouseMoveEvent(e)

    def _start_drag(self) -> None:
        mime = QtCore.QMimeData()
        mime.setData(_MIME, self.app_id.encode())
        px    = self._icon.pixmap(ICON_SIZE, ICON_SIZE)
        ghost = QtGui.QPixmap(px.size()); ghost.fill(Qt.transparent)
        ptr   = QtGui.QPainter(ghost); ptr.setOpacity(0.75)
        ptr.drawPixmap(0, 0, px); ptr.end()
        drag = QtGui.QDrag(self)
        drag.setMimeData(mime); drag.setPixmap(ghost)
        drag.setHotSpot(QtCore.QPoint(ghost.width()//2, ghost.height()//2))
        drag.exec_(Qt.MoveAction)

    # --- drop target --------------------------------------------------
    def dragEnterEvent(self, e: QtGui.QDragEnterEvent) -> None:  # noqa: N802
        e.acceptProposedAction() if e.mimeData().hasFormat(_MIME) else e.ignore()
    def dragMoveEvent(self, e: QtGui.QDragMoveEvent) -> None:  # noqa: N802
        if e.mimeData().hasFormat(_MIME): e.acceptProposedAction()
    def dropEvent(self, e: QtGui.QDropEvent) -> None:  # noqa: N802
        if e.mimeData().hasFormat(_MIME):
            src = e.mimeData().data(_MIME).data().decode()
            if src != self.app_id: self.drop_reorder.emit(src, self.app_id)
            e.acceptProposedAction()


# ────────────────────────────────────────────────────────────────────
class DockWindow(QtWidgets.QWidget):
    """Bottom dock with macOS-style magnification.

    Fixed-width window; buttons are positioned by absolute geometry each
    animation frame (no layout reflow → no jitter).  See module docstring
    for the magnification model.
    """

    menu_requested = QtCore.pyqtSignal()

    def __init__(self, theme: ThemeManager,
                 model: DockModel | None = None) -> None:
        super().__init__()
        self._theme = theme
        self.model  = model or DockModel()
        self._buttons: dict[str, DockButton] = {}
        self._order: list[QtWidgets.QAbstractButton] = []   # display order
        self._grid_btn: QtWidgets.QToolButton | None = None
        self._mask_key: tuple = ()   # cached to skip redundant setMask calls

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_StyledBackground, False)  # we paint manually
        self.setMouseTracking(True)

        # ── pill shelf (narrow, fixed-height, lives at window bottom) ──
        self._pill = QtWidgets.QFrame(self)
        self._pill.setObjectName("DockRoot")
        self._pill.setAttribute(Qt.WA_StyledBackground, True)
        self._pill.setFixedHeight(PILL_H)
        # No QGraphicsDropShadowEffect: the tight window mask clips any outer
        # shadow, so its only visible pixels were a dark halo bleeding up into
        # the overflow zone behind the floating icons (and it re-rendered the
        # pill to a pixmap every animation frame). Removed on both counts.

        self._watcher = x11.ClientListWatcher()
        self._watcher.window_added.connect(self._on_window_added)
        self._watcher.window_removed.connect(self._on_window_removed)

        # ── animation state (target vs rendered, dt-interpolated) ──────
        self._cursor_sx: float | None = None   # cursor screen-x, None = away
        self._last_t: float | None = None
        self._frame = QtCore.QTimer(self)
        self._frame.setInterval(FRAME_MS)
        self._frame.timeout.connect(self._tick)

        self._build()
        self._pill.lower()   # pill renders behind buttons
        theme.theme_changed.connect(self._on_theme_changed)

    # ── lifecycle ────────────────────────────────────────────────────
    def start(self) -> None:
        x11.set_dock_type(int(self.winId()))
        self.show()
        QtCore.QTimer.singleShot(0, self._apply_dock_geometry)
        self._watcher.start()

    def stop(self) -> None:
        self._frame.stop()
        self._watcher.stop()

    def closeEvent(self, e: QtGui.QCloseEvent) -> None:  # noqa: N802
        self.stop(); super().closeEvent(e)

    def _on_theme_changed(self) -> None:
        self.update()
        for btn in self._buttons.values():
            btn.update()

    # ── gradient in overflow zone only ───────────────────────────────
    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802
        """Paint the EXACT desktop background in the overflow zone (above pill).

        By reproducing the desktop's own multi-layer background — offset by the
        dock's screen position and clipped to the overflow strip — the patch
        behind each floating icon is pixel-identical to the desktop underneath,
        so no rectangle shows.  The pill zone paints itself (child widget).
        """
        p  = QtGui.QPainter(self)
        p.setClipRect(0, 0, self.width(), _PILL_TOP)   # overflow strip only
        sc = QtWidgets.QApplication.primaryScreen().geometry()
        paint_background(p, sc.width(), sc.height(), self._theme.tokens,
                         -self.x(), -self.y())

    # ── building ─────────────────────────────────────────────────────
    def _build(self) -> None:
        for b in self._order:
            b.setParent(None); b.deleteLater()
        self._order = []
        self._buttons.clear()
        self._grid_btn = None

        style = self.style()
        for app_id in self.model.visible_items():
            app = self.model.app(app_id)
            if not app: continue
            icon = QtGui.QIcon.fromTheme(app.icon)
            if icon.isNull():
                icon = style.standardIcon(QtWidgets.QStyle.SP_FileIcon)
            btn = DockButton(app_id, app.name, icon, self._theme)
            btn.set_running(self.model.is_running(app_id))
            btn.activated.connect(self._on_activated)
            btn.context.connect(self._show_menu)
            btn.drop_reorder.connect(self._on_drop_reorder)
            btn.setMouseTracking(True)
            btn.installEventFilter(self)
            btn.setParent(self)
            btn.show()
            self._buttons[app_id] = btn
            self._order.append(btn)

        self._grid_btn = self._make_grid_button()
        self._grid_btn.setMouseTracking(True)
        self._grid_btn.installEventFilter(self)
        self._grid_btn.setParent(self)
        self._grid_btn.show()
        self._order.append(self._grid_btn)

        n       = len(self._order)
        content = n * BTN + (n - 1) * SPACING
        win_w   = content + 2 * PAD + SPREAD_HEADROOM
        self.setFixedSize(win_w, WIN_H)

        self._layout_rest()
        self._mask_key = ()
        self._refresh_pill_and_mask()
        self._pill.lower()
        if self.isVisible():
            QtCore.QTimer.singleShot(0, self._apply_dock_geometry)

    def _make_grid_button(self) -> QtWidgets.QToolButton:
        g = QtWidgets.QToolButton()
        g.setText("☰")
        g.setObjectName("DockGrid")
        g.setFixedSize(BTN, BTN)
        g.setCursor(Qt.PointingHandCursor)
        g.setToolTip("Applications")
        g.setAcceptDrops(True)
        g._cur_scale = 1.0      # type: ignore[attr-defined]  (does not magnify)
        g._cur_tx    = 0.0      # type: ignore[attr-defined]
        g._base_center = 0      # type: ignore[attr-defined]
        g.clicked.connect(self.menu_requested.emit)
        g.dragEnterEvent = lambda e: (  # type: ignore[method-assign]
            e.acceptProposedAction() if e.mimeData().hasFormat(_MIME) else e.ignore())
        g.dropEvent = self._grid_drop  # type: ignore[method-assign]
        return g

    def _grid_drop(self, e: QtGui.QDropEvent) -> None:
        if e.mimeData().hasFormat(_MIME):
            src  = e.mimeData().data(_MIME).data().decode()
            pins = [a for a in self.model.pins if a != src] + [src]
            self.model.reorder(pins); self._build()
            e.acceptProposedAction()

    # ── geometry ─────────────────────────────────────────────────────
    def _apply_dock_geometry(self) -> None:
        screen = QtWidgets.QApplication.primaryScreen().geometry()
        w = self.width()
        x = screen.x() + (screen.width() - w) // 2
        y = screen.y() + screen.height() - WIN_H - GAP
        self.move(x, y)
        self._mask_key = ()
        self._refresh_pill_and_mask()
        wid = int(self.winId())
        x11.set_dock_type(wid)
        # Strut reserves only the resting pill band; magnified icons overflow
        # into non-reserved space above it.
        n       = len(self._order)
        content = n * BTN + (n - 1) * SPACING
        pill_l  = x + (w - content) // 2 - PAD
        pill_r  = pill_l + content + 2 * PAD - 1
        x11.set_bottom_strut(wid, PILL_H + GAP, pill_l, pill_r)

    # ── layout: place buttons by absolute geometry ───────────────────
    def _layout_rest(self) -> None:
        """Compute resting centres and snap every button to scale 1.0."""
        n       = len(self._order)
        content = n * BTN + (n - 1) * SPACING
        x       = (self.width() - content) // 2
        for b in self._order:
            b._base_center = x + BTN // 2   # type: ignore[attr-defined]
            b._cur_scale   = 1.0            # type: ignore[attr-defined]
            b._cur_tx      = 0.0            # type: ignore[attr-defined]
            x += BTN + SPACING
        self._apply_layout()

    def _apply_layout(self) -> None:
        """Position every button from its rendered (cur) state, bottom-pinned."""
        baseline = _BTN_BASE_Y
        for b in self._order:
            s    = getattr(b, "_cur_scale", 1.0)
            size = max(8, round(BTN * s))
            cx   = round(b._base_center + getattr(b, "_cur_tx", 0.0))  # type: ignore[attr-defined]
            b.setGeometry(cx - size // 2, baseline - size, size, size)
            if isinstance(b, DockButton):
                icon_px = max(6, round(ICON_SIZE * s))
                b.setIconSize(QtCore.QSize(icon_px, icon_px))
        self._refresh_pill_and_mask()
        self.update()   # repaint overflow gradient under the moved icons

    # ── pill position + window mask ──────────────────────────────────
    def _refresh_pill_and_mask(self) -> None:
        """Position the pill to span the icons and rebuild the window mask.

        mask = rounded pill rect ∪ {overflow rect of each button above pill}
        Between-icon areas in the overflow zone fall outside the mask → the
        desktop X11 layer shows through (no compositor needed).
        """
        order = self._order
        if not order:
            return
        geos = [b.geometry() for b in order]

        left   = max(0, min(g.left() for g in geos) - PAD)
        right  = min(self.width() - 1, max(g.right() for g in geos) + PAD)
        pill_w = max(1, right - left + 1)

        self._pill.setGeometry(left, _PILL_TOP, pill_w, PILL_H)
        pill_path = QtGui.QPainterPath()
        pill_path.addRoundedRect(QtCore.QRectF(0, 0, pill_w, PILL_H), RADIUS, RADIUS)
        self._pill.setMask(QtGui.QRegion(pill_path.toFillPolygon().toPolygon()))

        key = (left, pill_w,
               tuple((g.left(), g.top(), g.width()) for g in geos))
        if key == self._mask_key:
            return
        self._mask_key = key

        outer = QtGui.QPainterPath()
        outer.addRoundedRect(QtCore.QRectF(left, _PILL_TOP, pill_w, PILL_H),
                             RADIUS, RADIUS)
        region = QtGui.QRegion(outer.toFillPolygon().toPolygon())
        for g in geos:
            if g.top() < _PILL_TOP:    # box overflows above the pill
                region = region.united(QtGui.QRegion(
                    QtCore.QRect(g.left(), g.top(), g.width(), _PILL_TOP - g.top())))
        self.setMask(region)

    # ── animation driver ─────────────────────────────────────────────
    def _wake(self) -> None:
        if not self._frame.isActive():
            self._last_t = None
            self._frame.start()

    def _compute_targets(self) -> list[tuple[float, float]]:
        """Mathematical target (scale, tx) per button from the cursor X."""
        order   = self._order
        n       = len(order)
        cur     = self._cursor_sx
        dock_sx = self.x()

        scales: list[float] = []
        for b in order:
            if cur is None or b is self._grid_btn:
                scales.append(1.0); continue
            dx = abs(dock_sx + b._base_center - cur)   # type: ignore[attr-defined]
            if dx >= THRESHOLD:
                scales.append(1.0)
            else:
                p   = 1.0 - dx / THRESHOLD
                raw = SCALE_MAX * (p * (2.0 - p))      # quadratic ease-out
                scales.append(max(1.0, raw))

        # spread: each magnified icon pushes neighbours outward
        tx = [0.0] * n
        for i, s in enumerate(scales):
            if s > 1.1:
                off = 1.25 * (s - 1.0) * BTN * SPREAD_FACTOR * 0.5
                for j in range(i):       tx[j] -= off
                for j in range(i + 1, n): tx[j] += off

        # centering compensation: keep the hot icon under the cursor
        if cur is not None and n:
            ni = max(range(n), key=lambda k: scales[k])
            if scales[ni] > 1.0:
                adjust = tx[ni] / 2.0
                for k in range(n):
                    tx[k] -= adjust

        return list(zip(scales, tx))

    def _tick(self) -> None:
        now = time.perf_counter()
        dt  = 0.016 if self._last_t is None else min(0.05, now - self._last_t)
        self._last_t = now

        targets = self._compute_targets()
        a       = min(1.0, LERP_SPEED * dt)
        settled = True
        for b, (ts, tt) in zip(self._order, targets):
            b._cur_scale += (ts - b._cur_scale) * a   # type: ignore[attr-defined]
            b._cur_tx    += (tt - b._cur_tx) * a      # type: ignore[attr-defined]
            if (abs(ts - b._cur_scale) > EPS_SCALE     # type: ignore[attr-defined]
                    or abs(tt - b._cur_tx) > EPS_TX):  # type: ignore[attr-defined]
                settled = False

        self._apply_layout()

        if settled:                          # snap exactly and stop → 0% idle
            for b, (ts, tt) in zip(self._order, targets):
                b._cur_scale, b._cur_tx = ts, tt   # type: ignore[attr-defined]
            self._apply_layout()
            self._frame.stop()
            self._last_t = None

    # ── mouse tracking ───────────────────────────────────────────────
    def eventFilter(self, obj: QtCore.QObject,
                    event: QtCore.QEvent) -> bool:
        t = event.type()
        if t == QtCore.QEvent.MouseMove:
            self._cursor_sx = obj.mapToGlobal(event.pos()).x()  # type: ignore[attr-defined]
            self._wake()
        elif t == QtCore.QEvent.Leave:
            QtCore.QTimer.singleShot(0, self._check_leave)
        return super().eventFilter(obj, event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        self._cursor_sx = self.mapToGlobal(event.pos()).x()
        self._wake()
        super().mouseMoveEvent(event)

    def _cursor_over_dock(self) -> bool:
        """True only if the cursor is over VISIBLE dock content.

        The window is far wider than the visible dock (it carries spread
        headroom on both sides), so testing ``self.rect()`` would report the
        cursor as 'inside' while it sits in the invisible margin and the dock
        would never deflate.  Test the pill and the buttons instead.
        """
        gp = QtGui.QCursor.pos()
        pr = self._pill.geometry()
        if QtCore.QRect(self.mapToGlobal(pr.topLeft()), pr.size()).contains(gp):
            return True
        for b in self._order:
            g = b.geometry()
            if QtCore.QRect(self.mapToGlobal(g.topLeft()), g.size()).contains(gp):
                return True
        return False

    def _check_leave(self) -> None:
        if not self._cursor_over_dock():
            self._cursor_sx = None
            self._wake()

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._check_leave()
        super().leaveEvent(event)

    # ── drag reorder ─────────────────────────────────────────────────
    def _on_drop_reorder(self, src: str, tgt: str) -> None:
        pins = list(self.model.pins)
        if src not in pins or tgt not in pins: return
        pins.remove(src); pins.insert(pins.index(tgt), src)
        self.model.reorder(pins); self._build()

    # ── interaction ──────────────────────────────────────────────────
    def _on_activated(self, app_id: str) -> None:
        wins = self.model.windows(app_id)
        if wins: x11.activate_window(wins[-1])
        else:
            app = self.model.app(app_id)
            if app: launcher.launch(app)

    def _show_menu(self, app_id: str, gpos: QtCore.QPoint) -> None:
        menu = QtWidgets.QMenu()
        app  = self.model.app(app_id)
        if app:
            menu.addAction("Open new window", lambda: launcher.launch(app))
            menu.addSeparator()
        if self.model.is_pinned(app_id):
            menu.addAction("Move left",       lambda: self._move(app_id, -1))
            menu.addAction("Move right",      lambda: self._move(app_id, +1))
            menu.addAction("Unpin from dock", lambda: self._unpin(app_id))
        else:
            menu.addAction("Pin to dock", lambda: self._pin(app_id))
        menu.exec_(gpos)

    def _pin(self, a):     self.model.pin(a);     self._build()
    def _unpin(self, a):   self.model.unpin(a);   self._build()
    def _move(self, a, d): self.model.move(a, d); self._build()

    # ── running state ────────────────────────────────────────────────
    def _on_window_added(self, wm_class: str, win_id: int) -> None:
        app_id = self.model.add_window(wm_class, win_id)
        if not app_id: return
        if app_id in self._buttons: self._buttons[app_id].set_running(True)
        else: self._build()

    def _on_window_removed(self, win_id: int) -> None:
        app_id = self.model.remove_window(win_id)
        if not app_id: return
        still = self.model.is_running(app_id)
        if app_id in self._buttons:
            if not still and not self.model.is_pinned(app_id): self._build()
            else: self._buttons[app_id].set_running(still)
