"""Digital Wellbeing widget — activity ring + top apps from real usage.

No CMS and no hardcoded numbers: it reads the shared launch log (apps.usage),
buckets your apps into Social / Work / Entertainment by their .desktop
categories, and renders a donut ring of that split with the total in the centre
and your most-opened apps listed below. A fresh profile shows a friendly empty
state. Colours come from theme tokens; restyles on theme_changed.
"""
from __future__ import annotations

from core.qt_compat import Qt, QtCore, QtGui, QtWidgets
from apps import usage
from apps.desktop_entries import list_apps
from widgets.engine import WidgetContext, WidgetPlugin

_SOCIAL = {"Network", "Email", "InstantMessaging", "Chat", "Telephony", "News"}
_WORK = {"Office", "Development", "Utility", "System", "Settings", "Education",
         "Documentation", "Finance"}
_ENT = {"AudioVideo", "Audio", "Video", "Game", "Graphics", "Player",
        "Photography", "Recorder", "Players"}

_BUCKETS = [("Social", "#ec4899"), ("Work", "#b15cff"),
            ("Entertainment", "#3b82f6")]
_COLORS = dict(_BUCKETS)


def _bucket(categories) -> str:
    s = set(categories or ())
    if s & _ENT:
        return "Entertainment"
    if s & _SOCIAL:
        return "Social"
    return "Work"


class _Ring(QtWidgets.QWidget):
    """A donut chart of segment fractions with two-line centre text."""

    def __init__(self, theme) -> None:
        super().__init__()
        self._theme = theme
        self._segs: list[tuple[float, str]] = []
        self._main = ""
        self._sub = ""
        self.setMinimumHeight(150)

    def set_data(self, segs, main: str, sub: str) -> None:
        self._segs = segs
        self._main, self._sub = main, sub
        self.update()

    def paintEvent(self, _e) -> None:  # noqa: N802
        from core.colors import to_qcolor
        t = self._theme.tokens
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        side = min(self.width(), self.height())
        thick = max(10, int(side * 0.13))
        m = thick // 2 + 2
        rect = QtCore.QRectF(
            (self.width() - side) / 2 + m, (self.height() - side) / 2 + m,
            side - 2 * m, side - 2 * m)

        track = QtGui.QPen(to_qcolor(t.get("surface_alt", "#1f232c")), thick)
        track.setCapStyle(Qt.FlatCap)
        p.setPen(track)
        p.drawArc(rect, 0, 360 * 16)

        start = 90 * 16   # 12 o'clock
        for frac, color in self._segs:
            if frac <= 0:
                continue
            span = -int(round(frac * 360 * 16))
            pen = QtGui.QPen(QtGui.QColor(color), thick)
            pen.setCapStyle(Qt.FlatCap)
            p.setPen(pen)
            p.drawArc(rect, start, span)
            start += span

        p.setPen(to_qcolor(t.get("text", "#eef1f6")))
        f = p.font()
        f.setPointSize(max(13, int(side * 0.13)))
        f.setBold(True)
        p.setFont(f)
        p.drawText(rect, Qt.AlignCenter, self._main)
        p.setPen(to_qcolor(t.get("muted", "#8b93a3")))
        f2 = p.font()
        f2.setPointSize(max(8, int(side * 0.055)))
        f2.setBold(False)
        p.setFont(f2)
        sub_rect = QtCore.QRectF(rect)
        sub_rect.translate(0, side * 0.16)
        p.drawText(sub_rect, Qt.AlignCenter, self._sub)
        p.end()


class _DigitalWellbeing(QtWidgets.QFrame):
    def __init__(self, ctx: WidgetContext) -> None:
        super().__init__()
        self._ctx = ctx
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(12)
        self._title = QtWidgets.QLabel()
        lay.addWidget(self._title)

        self._ring = _Ring(ctx.theme)
        lay.addWidget(self._ring)

        self._legend = QtWidgets.QHBoxLayout()
        self._legend.setSpacing(14)
        lay.addLayout(self._legend)

        self._apps_lay = QtWidgets.QVBoxLayout()
        self._apps_lay.setSpacing(6)
        lay.addLayout(self._apps_lay)
        lay.addStretch(1)

        self._apply_theme()
        ctx.theme.theme_changed.connect(self._apply_theme)

    def _apply_theme(self) -> None:
        t = self._ctx.theme.tokens
        self._title.setText(
            f"<span style='color:{t['accent']};'>▍</span> "
            f"<span style='color:{t['text']};font-size:15px;font-weight:700;'>"
            f"Digital Wellbeing</span>")
        self._refresh()

    def _refresh(self) -> None:
        t = self._ctx.theme.tokens
        stats = usage.stats()
        apps = {a.app_id: a for a in list_apps()}

        totals = {name: 0 for name, _ in _BUCKETS}
        per_app: list[tuple[str, int, object]] = []
        for app_id, rec in stats.items():
            count = int((rec or {}).get("count", 0))
            if count <= 0 or app_id not in apps:
                continue
            app = apps[app_id]
            totals[_bucket(app.categories)] += count
            per_app.append((app.name, count, app))

        grand = sum(totals.values())
        segs = [(totals[name] / grand if grand else 0, color)
                for name, color in _BUCKETS]
        if grand:
            self._ring.set_data(segs, str(grand), "app opens")
        else:
            self._ring.set_data([], "0", "no activity yet")

        # legend
        while self._legend.count():
            item = self._legend.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._legend.addStretch(1)
        for name, color in _BUCKETS:
            chip = QtWidgets.QLabel(
                f"<span style='color:{color};'>●</span> "
                f"<span style='color:{t['muted']};font-size:11px;'>{name} "
                f"{totals[name]}</span>")
            self._legend.addWidget(chip)
        self._legend.addStretch(1)

        # top apps
        while self._apps_lay.count():
            item = self._apps_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        per_app.sort(key=lambda x: -x[1])
        for name, count, app in per_app[:4]:
            self._apps_lay.addWidget(self._app_row(name, count, app, t))
        if not per_app:
            hint = QtWidgets.QLabel("Open some apps to see your activity here.")
            hint.setStyleSheet(
                f"color:{t['muted']};font-size:11px;background:transparent;")
            hint.setWordWrap(True)
            self._apps_lay.addWidget(hint)

    def _app_row(self, name, count, app, t) -> QtWidgets.QWidget:
        row = QtWidgets.QWidget()
        row.setStyleSheet("background:transparent;")
        h = QtWidgets.QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(10)
        icon = QtWidgets.QLabel()
        icon.setPixmap(QtGui.QIcon.fromTheme(app.icon).pixmap(22, 22))
        icon.setFixedSize(22, 22)
        h.addWidget(icon)
        nl = QtWidgets.QLabel(name)
        nl.setStyleSheet(
            f"color:{t['text']};font-size:12px;font-weight:600;background:transparent;")
        h.addWidget(nl, 1)
        cl = QtWidgets.QLabel(f"{count} opens")
        cl.setStyleSheet(
            f"color:{t['muted']};font-size:11px;background:transparent;")
        h.addWidget(cl, 0, Qt.AlignRight)
        return row

    def showEvent(self, e) -> None:  # noqa: N802 - usage may have changed
        self._refresh()
        super().showEvent(e)


class DigitalWellbeingPlugin(WidgetPlugin):
    id = "digital_wellbeing"
    name = "Digital Wellbeing"
    description = "Your app activity ring and most-opened apps."
    icon = "preferences-desktop-screensaver"
    default_size = (1, 2)
    sizes = [(1, 2), (2, 2)]
    category = "Utilities"

    def create_view(self, ctx: WidgetContext) -> QtWidgets.QWidget:
        return _DigitalWellbeing(ctx)
