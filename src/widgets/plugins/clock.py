"""Clock widget — large time + date for the sidebar.

The single per-second timer the shell allows (CLAUDE.md); it is paused while
the view is hidden. Colours come from theme tokens and restyle on theme_changed.
"""
from __future__ import annotations

import time

from core.qt_compat import QtCore, QtWidgets
from widgets.engine import WidgetContext, WidgetPlugin


class _Clock(QtWidgets.QWidget):
    def __init__(self, ctx: WidgetContext) -> None:
        super().__init__()
        self._ctx = ctx
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(2)
        self._time = QtWidgets.QLabel()
        self._date = QtWidgets.QLabel()
        lay.addWidget(self._time)
        lay.addWidget(self._date)

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

        self._apply_theme()
        ctx.theme.theme_changed.connect(self._apply_theme)

    def _apply_theme(self) -> None:
        t = self._ctx.theme.tokens
        self._time.setStyleSheet(
            f"color:{t['text']};font-size:36px;font-weight:800;background:transparent;")
        self._date.setStyleSheet(
            f"color:{t['muted']};font-size:12px;background:transparent;")
        self._tick()

    def _tick(self) -> None:
        now = time.localtime()
        self._time.setText(time.strftime("%I:%M %p", now).lstrip("0"))
        self._date.setText(time.strftime("%A, %d %B %Y", now))

    def showEvent(self, e) -> None:  # noqa: N802
        self._timer.start(); self._tick(); super().showEvent(e)

    def hideEvent(self, e) -> None:  # noqa: N802
        self._timer.stop(); super().hideEvent(e)


class ClockPlugin(WidgetPlugin):
    id = "clock"
    name = "Clock"
    description = "A large time and date display."
    icon = "preferences-system-time"
    category = "Information"

    def create_view(self, ctx: WidgetContext) -> QtWidgets.QWidget:
        return _Clock(ctx)
