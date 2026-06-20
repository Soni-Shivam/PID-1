"""Greeting + live clock widget.

Personalised greeting (user's real name from the passwd GECOS field, with a
time-of-day salutation) plus a 1 s clock - the only per-second timer in the
shell, as allowed by CLAUDE.md. Text colours come from the live theme tokens and
restyle on theme_changed (Phase D).
"""
from __future__ import annotations

import time

from core import user
from core.qt_compat import QtCore, QtWidgets
from widgets.engine import WidgetContext, WidgetPlugin


class _GreetingClock(QtWidgets.QFrame):
    def __init__(self, ctx: WidgetContext) -> None:
        super().__init__()
        self._ctx = ctx
        self._username = (ctx.username.split()[0] if ctx.username
                          else user.first_name())
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(26, 24, 26, 24)
        lay.setSpacing(2)

        self._greet = QtWidgets.QLabel()
        self._greet.setWordWrap(True)
        self._clock = QtWidgets.QLabel()
        self._date = QtWidgets.QLabel()
        lay.addWidget(self._greet)
        lay.addStretch(1)
        lay.addWidget(self._clock)
        lay.addWidget(self._date)

        self._apply_theme()
        ctx.theme.theme_changed.connect(self._apply_theme)

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._tick()

    def _apply_theme(self) -> None:
        t = self._ctx.theme.tokens
        self._clock.setStyleSheet(
            f"color:{t['text']};font-size:44px;font-weight:800;")
        self._date.setStyleSheet(f"color:{t['muted']};font-size:13px;")
        self._tick()  # greeting carries accent, so refresh on theme change

    def _tick(self) -> None:
        t = self._ctx.theme.tokens
        now = time.localtime()
        self._greet.setText(
            f"<span style='color:{t['muted']};font-size:17px;font-weight:600;'>"
            f"{user.salutation(now.tm_hour)}, </span>"
            f"<span style='color:{t['accent']};font-size:17px;font-weight:700;'>"
            f"{self._username}</span>")
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
    description = "Personalized greeting with your name and a live clock."
    icon = "preferences-system-time"
    default_size = (1, 1)
    sizes = [(1, 1), (2, 1)]
    category = "Information"

    def create_view(self, ctx: WidgetContext) -> QtWidgets.QWidget:
        return _GreetingClock(ctx)
