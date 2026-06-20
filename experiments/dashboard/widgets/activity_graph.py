from design_system import card_qss
from core.qt_compat import QtCore, QtGui, QtWidgets
from grid_manager import BaseWidgetCard, SlotSize


class ActivityGraph(QtWidgets.QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(80)
        self.pulse = 0.0
        self.pulse_dir = 1
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._animate)
        self._timer.start()
        self._alive = True

    def deleteLater(self):
        self._alive = False
        self._timer.stop()
        super().deleteLater()

    def _animate(self):
        try:
            self.pulse += 0.05 * self.pulse_dir
            if self.pulse >= 1.0:   self.pulse = 1.0;  self.pulse_dir = -1
            elif self.pulse <= 0.0: self.pulse = 0.0;  self.pulse_dir = 1
            self._render()
            self.update()
        except Exception:
            pass

    def resizeEvent(self, event):
        self._render()
        super().resizeEvent(event)

    def _render(self):
        w, h = self.width(), self.height()
        if w == 0 or h == 0: return
        px = QtGui.QPixmap(w, h)
        px.fill(QtCore.Qt.transparent)
        p = QtGui.QPainter(px)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        path = QtGui.QPainterPath()
        path.moveTo(0, h * 0.8)
        path.cubicTo(w*.2, h*.8, w*.3, h*.9, w*.4, h*.8)
        path.cubicTo(w*.5, h*.7, w*.55, h*.3, w*.65, h*.3)
        path.cubicTo(w*.8, h*.3, w*.85, h*.7, w, h*.4)

        fp = QtGui.QPainterPath(path)
        fp.lineTo(w, h); fp.lineTo(0, h); fp.closeSubpath()
        grad = QtGui.QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0, QtGui.QColor(138, 43, 226, 60))
        grad.setColorAt(1, QtGui.QColor(0, 191, 255, 0))
        p.fillPath(fp, QtGui.QBrush(grad))

        lg = QtGui.QLinearGradient(0, 0, w, 0)
        lg.setColorAt(0, QtGui.QColor(180, 0, 255))
        lg.setColorAt(1, QtGui.QColor(0, 200, 255))
        pen = QtGui.QPen(QtGui.QBrush(lg), 2)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        p.setPen(pen)
        p.drawPath(path)

        nr = 4 + self.pulse * 2
        gr = 7 + self.pulse * 5
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(255, 255, 255, int(80 * (1-self.pulse))))
        p.drawEllipse(QtCore.QPointF(w*.65, h*.3), gr, gr)
        p.setBrush(QtGui.QColor(255, 255, 255))
        p.drawEllipse(QtCore.QPointF(w*.65, h*.3), nr, nr)
        p.end()
        self.setPixmap(px)


class ActivityGraphWidget(BaseWidgetCard):
    SUPPORTED_SIZES = [SlotSize.WIDE, SlotSize.LARGE]

    def __init__(self, state, size=SlotSize.WIDE):
        super().__init__("activity", size)
        self.setStyleSheet(f"ActivityGraphWidget, QFrame#wcard {{ {card_qss('#221C18')} }}")
        self.state = state

        l_act = QtWidgets.QVBoxLayout(self)
        l_act.setContentsMargins(16, 36, 16, 16)

        lbl_a_title = QtWidgets.QLabel("Activity Graph")
        lbl_a_title.setStyleSheet("color:#FFFFFF; font-size:15px; font-weight:600; background:transparent;")

        graph = ActivityGraph()
        l_act.addWidget(lbl_a_title)
        l_act.addWidget(graph, 1)

        stats = QtWidgets.QHBoxLayout()
        for label, val, col in [("Users","333","#d946ef"),("Steps","243","#8b5cf6"),("Activity","12+","#3b82f6")]:
            v = QtWidgets.QLabel(f"<span style='color:{col}'>●</span> {val}<br><span style='color:#52525B;font-size:11px'>{label}</span>")
            v.setStyleSheet("color:#FFFFFF; font-size:15px; font-weight:600; background:transparent;")
            stats.addWidget(v)
            stats.addStretch()
        l_act.addLayout(stats)
