"""Greeting + live clock widget.

Personalised greeting (user's real name from the passwd GECOS field, with a
time-of-day salutation) plus a 1 s clock - the only per-second timer in the
shell, as allowed by CLAUDE.md.
"""
from __future__ import annotations

import time

from core.qt_compat import QtCore, QtWidgets
from widgets.engine import WidgetContext, WidgetPlugin

_C = {"text": "#e6e6ea", "muted": "#9aa0ab"}


def _salutation(hour: int) -> str:
    if hour < 12:
        return "Good morning"
    if hour < 17:
        return "Good afternoon"
    return "Good evening"


class _GreetingClock(QtWidgets.QFrame):
    def __init__(self, username: str) -> None:
        super().__init__()
        self._username = username.split()[0] if username else "there"
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(4)

        self._clock = QtWidgets.QLabel()
        self._clock.setStyleSheet(f"color:{_C['text']};font-size:34px;font-weight:700;")
        self._date = QtWidgets.QLabel()
        self._date.setStyleSheet(f"color:{_C['muted']};font-size:13px;")
        self._greet = QtWidgets.QLabel()
        self._greet.setStyleSheet(f"color:{_C['text']};font-size:18px;font-weight:600;")
        lay.addWidget(self._greet)
        lay.addStretch(1)
        lay.addWidget(self._clock)
        lay.addWidget(self._date)

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._tick()

    def _tick(self) -> None:
        now = time.localtime()
        self._greet.setText(f"{_salutation(now.tm_hour)}, {self._username}")
        self._clock.setText(time.strftime("%I:%M %p", now).lstrip("0"))
        self._date.setText(time.strftime("%A, %d %B %Y", now))

    def showEvent(self, e) -> None:  # noqa: N802 - pause when not visible
        self._timer.start()
        super().showEvent(e)

    def hideEvent(self, e) -> None:  # noqa: N802
        self._timer.stop()
        super().hideEvent(e)


class GreetingClockPlugin(WidgetPlugin):
    id = "greeting_clock"
    name = "Greeting & Clock"
    default_size = (1, 1)

    def create_view(self, ctx: WidgetContext) -> QtWidgets.QWidget:
        return _GreetingClock(ctx.username)
