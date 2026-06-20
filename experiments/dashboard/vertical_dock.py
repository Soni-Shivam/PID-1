import time
from core.qt_compat import QtCore, QtGui, QtWidgets
try:
    from core.qt_compat import pyqtSignal
except ImportError:
    from PyQt5.QtCore import pyqtSignal
from utils import get_icon

BTN = 48
ICON_SIZE = 24
PAD = 12
SPACING = 24
RADIUS = 36

MAGNIFY_FACTOR = 0.65
SCALE_MAX = 1.0 + MAGNIFY_FACTOR
SPREAD_FACTOR = 0.5
THRESHOLD = (BTN + 10) * 2.5

FRAME_MS = 16
LERP_SPEED = 22.0
EPS_SCALE = 0.01
EPS_TX = 0.5

BTN_MAX = round(BTN * SCALE_MAX)
PILL_W = BTN + 2 * PAD
WIN_W = BTN_MAX + 2 * PAD

class DockButton(QtWidgets.QToolButton):
    def __init__(self, icon_data, is_first=False):
        super().__init__()
        self.icon_data = icon_data
        self.is_first = is_first
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setToolTip(icon_data.get("name", "").capitalize())
        
        self._cur_scale = 1.0
        self._cur_ty = 0.0
        self._base_center = 0
        
    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        
        target_size = self.iconSize().width()
        rect = QtCore.QRectF((self.width() - target_size) / 2, (self.height() - target_size) / 2, target_size, target_size)
        
        bg = self.icon_data.get("bg", "#1C1C1E")
        fg = self.icon_data.get("fg", "#FFF")
        emoji = self.icon_data.get("emoji", "")
        
        p.setBrush(QtGui.QColor(bg))
        p.setPen(QtCore.Qt.NoPen)
        # Rounded square for app icons, circle for home
        radius = target_size / 2 if self.is_first else target_size / 4.5
        p.drawRoundedRect(rect, radius, radius)
        
        # Emoji or letter
        if emoji:
            f = QtGui.QFont("System", int(target_size * 0.45))
            p.setFont(f)
            p.setPen(QtGui.QColor(fg))
            p.drawText(rect, QtCore.Qt.AlignCenter, emoji)

class VerticalDockWidget(QtWidgets.QWidget):
    # Emits the 0-based index of the clicked dock icon.
    icon_clicked = QtCore.pyqtSignal(int)

    def __init__(self, icons_data):
        super().__init__()
        self.setFixedWidth(WIN_W)
        self.setMouseTracking(True)
        self.setAttribute(QtCore.Qt.WA_Hover)

        self._buttons_list = []
        for i, idata in enumerate(icons_data):
            btn = DockButton(idata, is_first=(i == 0))
            btn.setParent(self)
            btn.installEventFilter(self)
            btn.setMouseTracking(True)
            btn.clicked.connect(lambda _, idx=i: self.icon_clicked.emit(idx))
            btn.show()
            self._buttons_list.append(btn)
            
        self._cursor_sy = None
        self._last_t = None
        self._frame = QtCore.QTimer(self)
        self._frame.setInterval(FRAME_MS)
        self._frame.timeout.connect(self._tick)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout_rest()
        
    def paintEvent(self, event):
        if not self._buttons_list: return
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        
        # Pill covers all buttons resting area
        top = self._buttons_list[0]._base_center - BTN // 2 - PAD
        bot = self._buttons_list[-1]._base_center + BTN // 2 + PAD
        h = bot - top
        
        # Draw pill aligned to the left
        rect = QtCore.QRectF(0, top, PILL_W, h)
        p.setBrush(QtGui.QColor(20, 20, 24, 204))
        pen = QtGui.QPen(QtGui.QColor(255, 255, 255, 13))
        pen.setWidth(1)
        p.setPen(pen)
        p.drawRoundedRect(rect, RADIUS, RADIUS)

    def _layout_rest(self):
        n = len(self._buttons_list)
        if not n: return
        content = n * BTN + (n - 1) * SPACING
        y = (self.height() - content) // 2
        for b in self._buttons_list:
            b._base_center = y + BTN // 2
            b._cur_scale = 1.0
            b._cur_ty = 0.0
            y += BTN + SPACING
        self._apply_layout()

    def _apply_layout(self):
        baseline = PAD
        for b in self._buttons_list:
            s = b._cur_scale
            size = max(8, round(BTN * s))
            cy = round(b._base_center + b._cur_ty)
            # Center button bounding box vertically at cy, and pin left edge to baseline
            b.setGeometry(baseline, cy - size // 2, size, size)
            icon_px = max(6, round(ICON_SIZE * s))
            b.setIconSize(QtCore.QSize(icon_px, icon_px))
        self.update()

    def _compute_targets(self):
        cur = self._cursor_sy
        scales = []
        for b in self._buttons_list:
            if cur is None:
                scales.append(1.0)
                continue
            dy = abs(b._base_center - cur)
            if dy >= THRESHOLD:
                scales.append(1.0)
            else:
                p = 1.0 - dy / THRESHOLD
                raw = SCALE_MAX * (p * (2.0 - p))
                scales.append(max(1.0, raw))
                
        ty = [0.0] * len(self._buttons_list)
        for i, s in enumerate(scales):
            if s > 1.1:
                off = 1.25 * (s - 1.0) * BTN * SPREAD_FACTOR * 0.5
                for j in range(i): ty[j] -= off
                for j in range(i + 1, len(scales)): ty[j] += off
                
        if cur is not None and len(scales):
            ni = max(range(len(scales)), key=lambda k: scales[k])
            if scales[ni] > 1.0:
                adjust = ty[ni] / 2.0
                for k in range(len(ty)):
                    ty[k] -= adjust
                    
        return list(zip(scales, ty))

    def _tick(self):
        now = time.perf_counter()
        dt = 0.016 if self._last_t is None else min(0.05, now - self._last_t)
        self._last_t = now

        targets = self._compute_targets()
        a = min(1.0, LERP_SPEED * dt)
        settled = True
        
        for b, (ts, tt) in zip(self._buttons_list, targets):
            b._cur_scale += (ts - b._cur_scale) * a
            b._cur_ty += (tt - b._cur_ty) * a
            if abs(ts - b._cur_scale) > EPS_SCALE or abs(tt - b._cur_ty) > EPS_TX:
                settled = False

        self._apply_layout()

        if settled:
            for b, (ts, tt) in zip(self._buttons_list, targets):
                b._cur_scale, b._cur_ty = ts, tt
            self._apply_layout()
            self._frame.stop()
            self._last_t = None

    def _wake(self):
        if not self._frame.isActive():
            self._last_t = None
            self._frame.start()

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.MouseMove:
            self._cursor_sy = self.mapFromGlobal(obj.mapToGlobal(event.pos())).y()
            self._wake()
        elif event.type() == QtCore.QEvent.Leave:
            QtCore.QTimer.singleShot(0, self._check_leave)
        return super().eventFilter(obj, event)

    def mouseMoveEvent(self, event):
        self._cursor_sy = event.pos().y()
        self._wake()
        super().mouseMoveEvent(event)

    def _check_leave(self):
        gp = QtGui.QCursor.pos()
        rect = QtCore.QRect(self.mapToGlobal(QtCore.QPoint(0,0)), self.size())
        if not rect.contains(gp):
            self._cursor_sy = None
            self._wake()

    def leaveEvent(self, event):
        self._check_leave()
        super().leaveEvent(event)
