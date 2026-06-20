"""Dock widget — macOS-style magnifying dock, anchored to the LEFT edge.

Magnification model (target state -> rendered state -> dt interpolation):

  Every button has a RESTING centre (`_base_center`) along the dock's main axis
  (vertical, Y) inside a fixed-WIDTH window.  Each animation frame computes a
  mathematical TARGET (scale + translation along Y) from the cursor's 1-D Y
  distance, then moves the RENDERED state toward it with time-delta
  interpolation for a fluid feel.

    1. proximity      p = 1 - dy/THRESHOLD          (dy = |cursor_y - center_y|)
    2. quad ease-out  raw = SCALE_MAX * p*(2-p)
    3. clamp          target_scale = max(1.0, raw)
    4. spread         magnified icons push neighbours apart (no overlap)
    5. compensation   counter-translate so the hot icon stays under the cursor
    6. interpolate    cur += (target - cur) * (LERP_SPEED * dt)

  Buttons are placed by absolute `setGeometry`; the box LEFT edge always sits on
  `_BTN_BASE_X` (left-edge pivot) so icons magnify rightward from a flat wall
  and never leave the screen edge.  The frame timer runs only while the dock is
  animating and stops the instant it settles, so idle CPU stays ~0%.

  The window is masked each frame to: pill rounded-rect  ∪  per-button overflow
  rects to the RIGHT of the pill — so the X11 desktop shows between floating
  icons with no compositor.
"""
from __future__ import annotations

import time

from core.qt_compat import Qt, QtCore, QtGui, QtWidgets
from core import x11
from core.background import paint_background
from core.colors import to_qcolor
from core.theme import ThemeManager
from apps import launcher
from dock.model import DockModel, DOCK_MIME

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
SPREAD_HEADROOM = 4 * BTN                # spare window height for the spread

FRAME_MS   = 16            # ~60 fps animation tick
LERP_SPEED = 22.0          # state approach speed (per second)
EPS_SCALE  = 0.01          # settle thresholds
EPS_T      = 0.5

# --- autohide --------------------------------------------------------
PEEK        = 5            # px of the pill left on-screen when hidden (hot edge)
SLIDE_MS    = 200          # reveal / hide slide duration
AUTOHIDE_MS = 1400         # delay before the first auto-hide on startup

BTN_MAX   = round(BTN * SCALE_MAX)        # peak box px  (79)
ICON_MAX  = round(ICON_SIZE * SCALE_MAX)  # peak icon px (56)

# --- two-layer widths -----------------------------------------------
PILL_W = BTN + 2 * PAD          # 72 px — the shelf (background bar)
WIN_W  = BTN_MAX + 2 * PAD      # window width (room for magnified boxes)

_BTN_BASE_X = PAD               # baseline: every button LEFT edge sits here

# --- drag -----------------------------------------------------------
_DRAG_THRESH = 6
_MIME        = DOCK_MIME

# ────────────────────────────────────────────────────────────────────
class DockButton(QtWidgets.QToolButton):
    """Dock icon.

    Holds its own rendered magnification state (`_cur_scale`, `_cur_t`) and
    resting centre (`_base_center`, along Y); the DockWindow animator writes
    these and repositions the button by absolute geometry.  The icon is painted
    pinned to the box LEFT so its base stays level with the dock wall at any
    scale.
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

        # rendered (interpolated) magnification state + resting centre (Y)
        self._cur_scale   = 1.0
        self._cur_t       = 0.0
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
        # widget is fully opaque — no reliance on see-through.
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
        """Paint the box background, then the icon anchored left-centre.

        The box straddles two zones: left of the shelf line it fills the pill
        colour, right of it (the overflow zone) it reproduces the EXACT desktop
        background (screen-aligned). So a magnified box poking past the shelf is
        pixel-identical to the desktop behind it — no square shows — while the
        icon itself, pinned by its own left edge, stays grounded as it magnifies
        rightward.
        """
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        t        = self._theme.tokens
        boundary = max(0, min(self.width(), PILL_W - self.x()))  # shelf line (x)

        # left of the shelf line: pill colour (seamless with the pill shelf).
        # to_qcolor is mandatory: dock_bg is an rgba() token and bare QColor()
        # would render it as opaque BLACK. Force full opacity so the
        # WA_OpaquePaintEvent box leaves no backing-store gaps.
        if boundary > 0:
            col = to_qcolor(t.get("dock_bg") or t.get("surface", "#181b22"))
            col.setAlpha(255)
            p.fillRect(0, 0, boundary, self.height(), col)
        # right of the shelf line: the desktop's own background, screen-aligned
        if boundary < self.width():
            gpos = self.mapToGlobal(QtCore.QPoint(0, 0))
            sc   = QtWidgets.QApplication.primaryScreen().geometry()
            p.save()
            p.setClipRect(boundary, 0, self.width() - boundary, self.height())
            paint_background(p, sc.width(), sc.height(), t, -gpos.x(), -gpos.y())
            p.restore()

        target  = self.iconSize().width()            # grows with magnification
        pm      = self._base_pm.scaled(
            target, target, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        dot_res = (DOT_HALO // 2 + 6) if self._running else 4
        icon_x  = dot_res                            # pin ACTUAL left edge
        icon_y  = (self.height() - pm.height()) // 2
        p.drawPixmap(max(0, icon_x), max(0, icon_y), pm)

        if self._running:
            accent = to_qcolor(t.get("indicator", "#5b9bff"))
            halo   = QtGui.QColor(accent); halo.setAlpha(55)
            cx = DOT_HALO // 2 + 1
            cy = self.height() // 2
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
    """Left-edge dock with macOS-style magnification.

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
        self.setAcceptDrops(True)   # apps dragged from the menu pin here

        # ── pill shelf (narrow, fixed-width, lives at window left) ──
        self._pill = QtWidgets.QFrame(self)
        self._pill.setObjectName("DockRoot")
        self._pill.setAttribute(Qt.WA_StyledBackground, True)
        self._pill.setFixedWidth(PILL_W)

        self._watcher = x11.ClientListWatcher()
        self._watcher.window_added.connect(self._on_window_added)
        self._watcher.window_removed.connect(self._on_window_removed)

        # ── animation state (target vs rendered, dt-interpolated) ──────
        self._cursor_sy: float | None = None   # cursor screen-y, None = away
        self._last_t: float | None = None
        self._frame = QtCore.QTimer(self)
        self._frame.setInterval(FRAME_MS)
        self._frame.timeout.connect(self._tick)

        # ── autohide state (slide the dock off the left edge) ──────────
        self._hidden = False
        self._revealed_x = 0
        self._hidden_x = 0
        self._slide: QtCore.QPropertyAnimation | None = None

        self._build()
        self._pill.lower()   # pill renders behind buttons
        theme.theme_changed.connect(self._on_theme_changed)

    # ── lifecycle ────────────────────────────────────────────────────
    def start(self) -> None:
        x11.set_dock_type(int(self.winId()))
        self.show()
        QtCore.QTimer.singleShot(0, self._apply_dock_geometry)
        # Reveal at boot so the dock is discoverable, then tuck away so apps get
        # the full screen; a left-edge touch slides it back (see _reveal/_hide).
        QtCore.QTimer.singleShot(AUTOHIDE_MS, self._auto_hide_initial)
        self._watcher.start()

    def _auto_hide_initial(self) -> None:
        if not self._cursor_over_dock():
            self._hide()

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
        """Paint the EXACT desktop background in the overflow zone (right of pill).

        By reproducing the desktop's own multi-layer background — offset by the
        dock's screen position and clipped to the overflow strip — the patch
        behind each floating icon is pixel-identical to the desktop underneath,
        so no rectangle shows.  The pill zone paints itself (child widget).
        """
        p  = QtGui.QPainter(self)
        p.setClipRect(PILL_W, 0, self.width() - PILL_W, self.height())
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
        win_h   = content + 2 * PAD + SPREAD_HEADROOM
        self.setFixedSize(WIN_W, win_h)

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
        g._cur_t     = 0.0      # type: ignore[attr-defined]
        g._base_center = 0      # type: ignore[attr-defined]
        g.clicked.connect(self.menu_requested.emit)
        g.setContextMenuPolicy(Qt.CustomContextMenu)
        g.customContextMenuRequested.connect(
            lambda pos: self._grid_menu(g.mapToGlobal(pos)))
        g.dragEnterEvent = lambda e: (  # type: ignore[method-assign]
            e.acceptProposedAction() if e.mimeData().hasFormat(_MIME) else e.ignore())
        g.dropEvent = self._grid_drop  # type: ignore[method-assign]
        return g

    def _grid_menu(self, gpos: QtCore.QPoint) -> None:
        menu = QtWidgets.QMenu()
        menu.addAction("Open Applications", self.menu_requested.emit)
        menu.addSeparator()
        menu.addAction("Choose dock apps…", self._open_customize)
        menu.exec_(gpos)

    def _open_customize(self) -> None:
        from dock.customize import DockCustomizeDialog
        self._reveal()
        dlg = DockCustomizeDialog(self.model, self._theme, self._build)
        dlg.exec_()

    def _grid_drop(self, e: QtGui.QDropEvent) -> None:
        if e.mimeData().hasFormat(_MIME):
            src  = e.mimeData().data(_MIME).data().decode()
            pins = [a for a in self.model.pins if a != src] + [src]
            self.model.reorder(pins); self._build()
            e.acceptProposedAction()

    # ── geometry ─────────────────────────────────────────────────────
    def _apply_dock_geometry(self) -> None:
        screen = QtWidgets.QApplication.primaryScreen().geometry()
        h = self.height()
        # Revealed: pill flush to the wall so the cursor stays over it after the
        # slide (a gap would let it re-hide instantly). Hidden: slide left until
        # only a PEEK-wide sliver of the pill's right edge remains as a hot edge.
        self._revealed_x = screen.x()
        self._hidden_x = screen.x() + PEEK - PILL_W
        y = screen.y() + (screen.height() - h) // 2
        x = self._hidden_x if self._hidden else self._revealed_x
        self.move(x, y)
        self._mask_key = ()
        self._refresh_pill_and_mask()
        wid = int(self.winId())
        x11.set_dock_type(wid)
        # Autohide: reserve no space so maximized windows use the full width;
        # the dock floats on top and reveals on demand.
        x11.set_left_strut(wid, 0, 0, 0)

    # ── layout: place buttons by absolute geometry ───────────────────
    def _layout_rest(self) -> None:
        """Compute resting centres (Y) and snap every button to scale 1.0."""
        n       = len(self._order)
        content = n * BTN + (n - 1) * SPACING
        y       = (self.height() - content) // 2
        for b in self._order:
            b._base_center = y + BTN // 2    # type: ignore[attr-defined]
            b._cur_scale   = 1.0             # type: ignore[attr-defined]
            b._cur_t       = 0.0             # type: ignore[attr-defined]
            y += BTN + SPACING
        self._apply_layout()

    def _apply_layout(self) -> None:
        """Position every button from its rendered (cur) state, left-pinned."""
        baseline = _BTN_BASE_X
        for b in self._order:
            s    = getattr(b, "_cur_scale", 1.0)
            size = max(8, round(BTN * s))
            cy   = round(b._base_center + getattr(b, "_cur_t", 0.0))  # type: ignore[attr-defined]
            b.setGeometry(baseline, cy - size // 2, size, size)
            if isinstance(b, DockButton):
                icon_px = max(6, round(ICON_SIZE * s))
                b.setIconSize(QtCore.QSize(icon_px, icon_px))
        self._refresh_pill_and_mask()
        self.update()   # repaint overflow gradient under the moved icons

    # ── pill position + window mask ──────────────────────────────────
    def _refresh_pill_and_mask(self) -> None:
        """Position the pill to span the icons and rebuild the window mask.

        mask = rounded pill rect ∪ {overflow rect of each button right of pill}
        Between-icon areas in the overflow zone fall outside the mask → the
        desktop X11 layer shows through (no compositor needed).
        """
        order = self._order
        if not order:
            return
        geos = [b.geometry() for b in order]

        top    = max(0, min(g.top() for g in geos) - PAD)
        bottom = min(self.height() - 1, max(g.bottom() for g in geos) + PAD)
        pill_h = max(1, bottom - top + 1)

        self._pill.setGeometry(0, top, PILL_W, pill_h)
        pill_path = QtGui.QPainterPath()
        pill_path.addRoundedRect(QtCore.QRectF(0, 0, PILL_W, pill_h), RADIUS, RADIUS)
        self._pill.setMask(QtGui.QRegion(pill_path.toFillPolygon().toPolygon()))

        key = (top, pill_h, tuple(
            (g.top(), g.left(), g.height(), getattr(b, "_running", False))
            for b, g in zip(order, geos)))
        if key == self._mask_key:
            return
        self._mask_key = key

        outer = QtGui.QPainterPath()
        outer.addRoundedRect(QtCore.QRectF(0, top, PILL_W, pill_h),
                             RADIUS, RADIUS)
        region = QtGui.QRegion(outer.toFillPolygon().toPolygon())
        # Right of the shelf, cut the mask TIGHTLY to the scaled icon — not the
        # full layout box. The box is ~BTN*s wide but the icon is only
        # ~ICON_SIZE*s, so masking the box would expose a strip of painted
        # fake-background that reads as a hard rectangle. Hugging the icon
        # excludes that strip, so the genuine X11 desktop shows there instead.
        PAD_AA = 2   # spare px so the icon's antialiased edge is not clipped
        for b, g in zip(order, geos):
            s        = getattr(b, "_cur_scale", 1.0)
            icon_px  = max(6, round(ICON_SIZE * s))
            dot_res  = (DOT_HALO // 2 + 6) if getattr(b, "_running", False) else 4
            icon_x   = g.left() + dot_res
            icon_y   = g.top()  + (g.height() - icon_px) // 2
            icon_r   = icon_x + icon_px
            if icon_r <= PILL_W:
                continue
            left = max(PILL_W, icon_x) - PAD_AA
            w    = icon_r - left + PAD_AA
            if w > 0:
                region = region.united(QtGui.QRegion(
                    left, icon_y - PAD_AA, w, icon_px + 2 * PAD_AA))
        self.setMask(region)

    # ── animation driver ─────────────────────────────────────────────
    def _wake(self) -> None:
        if not self._frame.isActive():
            self._last_t = None
            self._frame.start()

    def _compute_targets(self) -> list[tuple[float, float]]:
        """Mathematical target (scale, t) per button from the cursor Y."""
        order   = self._order
        n       = len(order)
        cur     = self._cursor_sy
        dock_sy = self.y()

        scales: list[float] = []
        for b in order:
            if cur is None or b is self._grid_btn:
                scales.append(1.0); continue
            dy = abs(dock_sy + b._base_center - cur)   # type: ignore[attr-defined]
            if dy >= THRESHOLD:
                scales.append(1.0)
            else:
                p   = 1.0 - dy / THRESHOLD
                raw = SCALE_MAX * (p * (2.0 - p))      # quadratic ease-out
                scales.append(max(1.0, raw))

        # spread: each magnified icon pushes neighbours outward (along Y)
        t = [0.0] * n
        for i, s in enumerate(scales):
            if s > 1.1:
                off = 1.25 * (s - 1.0) * BTN * SPREAD_FACTOR * 0.5
                for j in range(i):       t[j] -= off
                for j in range(i + 1, n): t[j] += off

        # centering compensation: keep the hot icon under the cursor
        if cur is not None and n:
            ni = max(range(n), key=lambda k: scales[k])
            if scales[ni] > 1.0:
                adjust = t[ni] / 2.0
                for k in range(n):
                    t[k] -= adjust

        return list(zip(scales, t))

    def _tick(self) -> None:
        now = time.perf_counter()
        dt  = 0.016 if self._last_t is None else min(0.05, now - self._last_t)
        self._last_t = now

        targets = self._compute_targets()
        a       = min(1.0, LERP_SPEED * dt)
        settled = True
        for b, (ts, tt) in zip(self._order, targets):
            b._cur_scale += (ts - b._cur_scale) * a   # type: ignore[attr-defined]
            b._cur_t     += (tt - b._cur_t) * a       # type: ignore[attr-defined]
            if (abs(ts - b._cur_scale) > EPS_SCALE     # type: ignore[attr-defined]
                    or abs(tt - b._cur_t) > EPS_T):    # type: ignore[attr-defined]
                settled = False

        self._apply_layout()

        if settled:                          # snap exactly and stop → 0% idle
            for b, (ts, tt) in zip(self._order, targets):
                b._cur_scale, b._cur_t = ts, tt   # type: ignore[attr-defined]
            self._apply_layout()
            self._frame.stop()
            self._last_t = None

    # ── mouse tracking ───────────────────────────────────────────────
    def eventFilter(self, obj: QtCore.QObject,
                    event: QtCore.QEvent) -> bool:
        t = event.type()
        if t == QtCore.QEvent.MouseMove:
            self._cursor_sy = obj.mapToGlobal(event.pos()).y()  # type: ignore[attr-defined]
            self._wake()
        elif t == QtCore.QEvent.Leave:
            QtCore.QTimer.singleShot(0, self._check_leave)
        return super().eventFilter(obj, event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        if self._hidden:
            self._reveal()
        self._cursor_sy = self.mapToGlobal(event.pos()).y()
        self._wake()
        super().mouseMoveEvent(event)

    def enterEvent(self, event) -> None:  # noqa: N802
        # Touching the left-edge sliver brings the dock back.
        if self._hidden:
            self._reveal()
        super().enterEvent(event)

    # ── autohide slide ───────────────────────────────────────────────
    def _reveal(self) -> None:
        if not self._hidden:
            return
        self._hidden = False
        self._slide_to(self._revealed_x)

    def _hide(self) -> None:
        if self._hidden or self._cursor_over_dock():
            return
        self._hidden = True
        self._cursor_sy = None
        self._wake()                 # deflate any magnification as it leaves
        self._slide_to(self._hidden_x)

    def _slide_to(self, target_x: int) -> None:
        if self._slide is not None:
            self._slide.stop()
        anim = QtCore.QPropertyAnimation(self, b"pos", self)
        anim.setDuration(SLIDE_MS)
        anim.setStartValue(self.pos())
        anim.setEndValue(QtCore.QPoint(target_x, self.y()))
        anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        anim.start()
        self._slide = anim

    def _cursor_over_dock(self) -> bool:
        """True only if the cursor is over VISIBLE dock content.

        The window is far taller than the visible dock (it carries spread
        headroom on both ends), so testing ``self.rect()`` would report the
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
            self._cursor_sy = None
            self._wake()
            self._hide()             # tuck the dock away once the cursor leaves

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._check_leave()
        super().leaveEvent(event)

    # ── external drag (an app dragged in from the menu) ──────────────
    def begin_external_drag(self) -> None:
        """Reveal the dock and lift it above everything so an app drag can drop.

        Reveal instantly (not animated): a QDrag runs a nested loop that may not
        tick the slide animation, and the dock must already be on-screen to
        accept the drop.
        """
        self._hidden = False
        if self._slide is not None:
            self._slide.stop()
        self.move(self._revealed_x, self.y())
        self.raise_()

    def dragEnterEvent(self, e: QtGui.QDragEnterEvent) -> None:  # noqa: N802
        if e.mimeData().hasFormat(_MIME):
            if self._hidden:
                self._reveal()
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragMoveEvent(self, e: QtGui.QDragMoveEvent) -> None:  # noqa: N802
        if e.mimeData().hasFormat(_MIME):
            e.acceptProposedAction()

    def dropEvent(self, e: QtGui.QDropEvent) -> None:  # noqa: N802
        if e.mimeData().hasFormat(_MIME):
            self._pin(e.mimeData().data(_MIME).data().decode())
            e.acceptProposedAction()

    # ── drag reorder ─────────────────────────────────────────────────
    def _on_drop_reorder(self, src: str, tgt: str) -> None:
        pins = list(self.model.pins)
        if src not in pins:
            # An app dragged in from the menu and dropped onto a dock icon:
            # pin it just before the icon it landed on.
            if tgt in pins:
                pins.insert(pins.index(tgt), src)
            else:
                pins.append(src)
            self.model.reorder(pins); self._build(); return
        if tgt not in pins: return
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
            menu.addAction("Move up",         lambda: self._move(app_id, -1))
            menu.addAction("Move down",       lambda: self._move(app_id, +1))
            menu.addAction("Unpin from dock", lambda: self._unpin(app_id))
        else:
            menu.addAction("Pin to dock", lambda: self._pin(app_id))
        menu.addSeparator()
        menu.addAction("Choose dock apps…", self._open_customize)
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
