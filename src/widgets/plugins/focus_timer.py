"""Focus timer widget — a self-styled accent card with a countdown.

A 25:00 focus countdown with Start/Pause and Reset. The 1 s timer runs only
while counting (stopped when paused/idle and when hidden), so it costs nothing
at rest. card_chrome is False: it paints its own accent card. Demonstrates that
adding a widget is just dropping one file in widgets/plugins/.
"""
from __future__ import annotations

from core.qt_compat import Qt, QtCore, QtWidgets
from widgets.engine import WidgetContext, WidgetPlugin

_DEFAULT_SECONDS = 25 * 60


class _FocusTimer(QtWidgets.QFrame):
    def __init__(self, ctx: WidgetContext) -> None:
        super().__init__()
        self._ctx = ctx
        self._remaining = _DEFAULT_SECONDS
        self._running = False
        self.setObjectName("FocusCard")
        self.setAttribute(Qt.WA_StyledBackground, True)

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(8)
        self._label = QtWidgets.QLabel("Focus timer")
        self._time = QtWidgets.QLabel(self._fmt())
        self._time.setAlignment(Qt.AlignCenter)
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(8)
        self._start = QtWidgets.QPushButton("Start")
        self._reset = QtWidgets.QPushButton("Reset")
        for b in (self._start, self._reset):
            b.setCursor(Qt.PointingHandCursor)
        self._start.clicked.connect(self._toggle)
        self._reset.clicked.connect(self._do_reset)
        row.addWidget(self._start); row.addWidget(self._reset)
        lay.addWidget(self._label)
        lay.addWidget(self._time)
        lay.addLayout(row)

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

        self._apply_theme()
        ctx.theme.theme_changed.connect(self._apply_theme)

    def _fmt(self) -> str:
        return f"{self._remaining // 60:02d}:{self._remaining % 60:02d}"

    def _toggle(self) -> None:
        self._running = not self._running
        if self._running:
            self._timer.start(); self._start.setText("Pause")
        else:
            self._timer.stop(); self._start.setText("Start")

    def _do_reset(self) -> None:
        self._timer.stop(); self._running = False
        self._remaining = _DEFAULT_SECONDS
        self._start.setText("Start"); self._time.setText(self._fmt())

    def _tick(self) -> None:
        if self._remaining > 0:
            self._remaining -= 1
            self._time.setText(self._fmt())
        if self._remaining == 0:
            self._timer.stop(); self._running = False; self._start.setText("Start")

    def _apply_theme(self) -> None:
        t = self._ctx.theme.tokens
        self.setStyleSheet(
            f"#FocusCard{{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            f"stop:0 {t['accent']},stop:1 {t['accent_soft']});"
            f"border:1px solid {t['accent']};border-radius:16px;}}")
        self._label.setStyleSheet(
            f"color:{t['on_accent']};font-size:12px;font-weight:700;"
            f"background:transparent;")
        self._time.setStyleSheet(
            f"color:{t['on_accent']};font-size:38px;font-weight:800;"
            f"background:transparent;")
        btn = (f"QPushButton{{background:{t['on_accent']};color:{t['accent']};"
               f"border:none;border-radius:10px;padding:6px 12px;font-weight:700;}}"
               f"QPushButton:hover{{background:{t['surface']};color:{t['text']};}}")
        self._start.setStyleSheet(btn)
        self._reset.setStyleSheet(btn)

    def showEvent(self, e) -> None:  # noqa: N802
        if self._running:
            self._timer.start()
        super().showEvent(e)

    def hideEvent(self, e) -> None:  # noqa: N802
        self._timer.stop(); super().hideEvent(e)


class FocusTimerPlugin(WidgetPlugin):
    id = "focus_timer"
    name = "Focus Timer"
    description = "A Pomodoro-style countdown to keep you on task."
    icon = "appointment-soon"
    category = "Productivity"
    card_chrome = False

    def create_view(self, ctx: WidgetContext) -> QtWidgets.QWidget:
        return _FocusTimer(ctx)
