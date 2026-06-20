"""
Widget 3: Focus Timer — 2×1 Wide (collapsible to 1×1)
=======================================================
Spec-accurate optimisations:
  • QTimer interval = 1000ms exactly — 1Hz update, never polls.
  • Only the QLabel text string changes each second. No layout recalculation.
  • Zero graphical transitions at idle (timer stopped = no CPU).
  • Deep purple #4A3B69 background per spec.
  • White pill QPushButton for Start/Pause.
"""
import math
from core.qt_compat import QtCore, QtGui, QtWidgets
from grid_manager import BaseWidgetCard, SlotSize
from design_system import (
    card_qss, label_qss, pill_btn_qss, ghost_btn_qss,
    FAUX_BORDER_QSS, RADIUS, TEXT_PRIMARY, TEXT_SECONDARY,
    BG_FOCUS, BG_FOCUS_BTN,
)

WORK_SECS  = 25 * 60    # 25:00 Pomodoro
BREAK_SECS = 5  * 60    # 5:00  break


class FocusTimerWidget(BaseWidgetCard):
    """2×1 Focus / Pomodoro timer. 1Hz update, zero idle CPU."""
    SUPPORTED_SIZES = [SlotSize.WIDE, SlotSize.LARGE]

    def __init__(self, state=None, size: SlotSize = SlotSize.WIDE):
        super().__init__("focus", size)

        # Faux-depth border + deep purple bg
        self.setStyleSheet(f"""
            FocusTimerWidget {{
                background: {BG_FOCUS};
                border-radius: {RADIUS}px;
                border-top:    1px solid rgba(255,255,255,0.12);
                border-left:   1px solid rgba(255,255,255,0.12);
                border-bottom: 1px solid rgba(0,0,0,0.50);
                border-right:  1px solid rgba(0,0,0,0.50);
            }}
        """)

        self._remaining  = WORK_SECS
        self._total      = WORK_SECS
        self._running    = False
        self._phase      = "Focus"   # "Focus" | "Break"

        # ── Layout ───────────────────────────────────────────────────────────
        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(28, 44, 28, 24)
        root.setSpacing(0)

        # Left: labels + controls
        left = QtWidgets.QVBoxLayout()
        left.setSpacing(0)

        # Phase label ("Focus" / "Break")
        self._lbl_phase = QtWidgets.QLabel(self._phase.upper())
        self._lbl_phase.setStyleSheet(
            "color:rgba(255,255,255,0.45); font-size:11px; font-weight:700;"
            " letter-spacing:2px; background:transparent;")

        # Big time display — bold, large, monospaced digits
        self._lbl_time = QtWidgets.QLabel("25:00")
        self._lbl_time.setStyleSheet(
            "color:#FFFFFF; font-size:52px; font-weight:800;"
            " background:transparent; letter-spacing:-1px;")

        # Mode tabs (Focus / Break / Rest)
        tabs = QtWidgets.QHBoxLayout()
        tabs.setSpacing(6)
        for mode in ["Focus", "Break", "Rest"]:
            btn = QtWidgets.QPushButton(mode)
            btn.setFixedHeight(26)
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            if mode == "Focus":
                btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(255,255,255,0.15);
                        color: #FFFFFF;
                        border: none;
                        border-radius: 13px;
                        font-size: 12px;
                        font-weight: 600;
                        padding: 0 12px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        color: rgba(255,255,255,0.40);
                        border: none;
                        border-radius: 13px;
                        font-size: 12px;
                        padding: 0 12px;
                    }
                    QPushButton:hover { color: rgba(255,255,255,0.70); }
                """)
            btn.clicked.connect(lambda _, m=mode: self._set_mode(m))
            tabs.addWidget(btn)
        tabs.addStretch()

        left.addWidget(self._lbl_phase)
        left.addSpacing(4)
        left.addWidget(self._lbl_time)
        left.addSpacing(18)
        left.addLayout(tabs)
        left.addSpacing(14)

        # Start / Pause button
        self._btn_start = QtWidgets.QPushButton("▶  Start")
        self._btn_start.setFixedSize(130, 44)
        self._btn_start.setCursor(QtCore.Qt.PointingHandCursor)
        self._btn_start.setStyleSheet(pill_btn_qss(radius=22))
        self._btn_start.clicked.connect(self._toggle)
        left.addWidget(self._btn_start)
        left.addStretch()

        root.addLayout(left)
        root.addStretch()

        # Right: arc progress indicator (lightweight QPainter, no animation at idle)
        self._arc = _ArcProgress(self)
        self._arc.setFixedSize(110, 110)
        root.addWidget(self._arc, 0, QtCore.Qt.AlignVCenter)

        # QTimer: 1000ms interval — 1 Hz, zero idle CPU when stopped
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

        self._update_display()

    # ── Timer logic ──────────────────────────────────────────────────────────
    def _toggle(self):
        if self._running:
            self._timer.stop()
            self._running = False
            self._btn_start.setText("▶  Resume")
        else:
            self._timer.start()
            self._running = True
            self._btn_start.setText("⏸  Pause")

    def _tick(self):
        """Called at exactly 1 Hz. Only the string changes — no layout churn."""
        if self._remaining > 0:
            self._remaining -= 1
            self._update_display()
        else:
            self._timer.stop()
            self._running = False
            self._btn_start.setText("▶  Start")
            self._remaining = self._total

    def _update_display(self):
        m, s = divmod(self._remaining, 60)
        self._lbl_time.setText(f"{m:02d}:{s:02d}")
        progress = self._remaining / max(1, self._total)
        self._arc.set_progress(progress)

    def _set_mode(self, mode: str):
        self._timer.stop()
        self._running = False
        self._phase   = mode
        self._lbl_phase.setText(mode.upper())
        if mode == "Focus":
            self._total = WORK_SECS
        elif mode == "Break":
            self._total = BREAK_SECS
        else:
            self._total = 15 * 60
        self._remaining = self._total
        self._btn_start.setText("▶  Start")
        self._update_display()


class _ArcProgress(QtWidgets.QWidget):
    """
    Lightweight arc ring drawn directly in QPainter.
    Only redraws when set_progress() is called (1 Hz max).
    No animation timer of its own.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 1.0
        self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent, False)
        self.setStyleSheet("background:transparent;")

    def set_progress(self, p: float):
        self._progress = max(0.0, min(1.0, p))
        self.update()   # single, synchronous repaint

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        w, h = self.width(), self.height()
        m    = 8
        rect = QtCore.QRectF(m, m, w - 2*m, h - 2*m)

        # Track ring
        pen = QtGui.QPen(QtGui.QColor(255, 255, 255, 25), 7,
                         QtCore.Qt.SolidLine, QtCore.Qt.RoundCap)
        p.setPen(pen)
        p.drawArc(rect, 0, 360 * 16)

        # Progress arc
        angle = int(self._progress * 360 * 16)
        pen.setColor(QtGui.QColor(255, 255, 255, 220))
        p.setPen(pen)
        p.drawArc(rect, 90 * 16, -angle)   # start at top

        # Centre text
        p.setPen(QtGui.QColor(255, 255, 255, 120))
        f = QtGui.QFont()
        f.setPointSize(9)
        p.setFont(f)
        pct = f"{int(self._progress * 100)}%"
        p.drawText(rect, QtCore.Qt.AlignCenter, pct)
