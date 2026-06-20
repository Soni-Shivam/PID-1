"""Calendar widget — the real current month with today highlighted.

No CMS, no hardcoded dates: built from Python's calendar module for the actual
current month each time it becomes visible. Today's cell gets an accent pill.
All colours come from theme tokens so light and dark render correctly.
"""
from __future__ import annotations

import calendar
import datetime as _dt

from core.qt_compat import Qt, QtCore, QtWidgets
from widgets.engine import WidgetContext, WidgetPlugin

_DAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]


class _Calendar(QtWidgets.QFrame):
    def __init__(self, ctx: WidgetContext) -> None:
        super().__init__()
        self._ctx = ctx
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(8)
        self._title = QtWidgets.QLabel()
        lay.addWidget(self._title)
        self._grid = QtWidgets.QGridLayout()
        self._grid.setSpacing(2)
        lay.addLayout(self._grid)
        lay.addStretch(1)
        self._apply_theme()
        ctx.theme.theme_changed.connect(self._render)

    def _cell(self, text: str, *, header=False, today=False) -> QtWidgets.QLabel:
        t = self._ctx.theme.tokens
        lbl = QtWidgets.QLabel(text)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFixedHeight(22)
        if header:
            lbl.setStyleSheet(
                f"color:{t['muted']};font-size:10px;font-weight:700;background:transparent;")
        elif today:
            lbl.setStyleSheet(
                f"color:{t['on_accent']};font-size:11px;font-weight:800;"
                f"background:{t['accent']};border-radius:11px;")
        else:
            lbl.setStyleSheet(
                f"color:{t['text']};font-size:11px;background:transparent;")
        return lbl

    def _render(self) -> None:
        t = self._ctx.theme.tokens
        today = _dt.date.today()
        self._title.setText(
            f"<span style='color:{t['accent']};'>▍</span> "
            f"<span style='color:{t['text']};font-size:15px;font-weight:700;'>"
            f"{today.strftime('%B %Y')}</span>")
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for c, d in enumerate(_DAYS):
            self._grid.addWidget(self._cell(d, header=True), 0, c)
        weeks = calendar.Calendar(firstweekday=0).monthdayscalendar(
            today.year, today.month)
        for r, week in enumerate(weeks, start=1):
            for c, day in enumerate(week):
                if day == 0:
                    continue
                self._grid.addWidget(
                    self._cell(str(day), today=(day == today.day)), r, c)

    def _apply_theme(self) -> None:
        self._render()

    def showEvent(self, e) -> None:  # noqa: N802
        self._render()
        super().showEvent(e)


class CalendarPlugin(WidgetPlugin):
    id = "calendar"
    name = "Calendar"
    description = "The current month at a glance, today highlighted."
    icon = "office-calendar"
    default_size = (1, 1)
    sizes = [(1, 1), (1, 2)]
    category = "Utilities"

    def create_view(self, ctx: WidgetContext) -> QtWidgets.QWidget:
        return _Calendar(ctx)
