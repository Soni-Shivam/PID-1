"""System Health widget — live CPU, RAM and disk usage from /proc (real data).

No CMS and no hardcoded numbers: CPU% is a delta of /proc/stat between samples,
RAM% from /proc/meminfo, disk% from the root filesystem. A slow 2.5 s timer
samples only while the widget is visible (paused on hide, like the clock), so it
stays comfortably inside the idle-CPU budget. Bars and text use theme tokens.
"""
from __future__ import annotations

import shutil

from core.qt_compat import Qt, QtCore, QtGui, QtWidgets
from widgets.engine import WidgetContext, WidgetPlugin

_SAMPLE_MS = 2500


def _cpu_times() -> tuple[int, int]:
    """Return (idle, total) jiffies from /proc/stat's aggregate cpu line."""
    try:
        with open("/proc/stat") as fh:
            parts = fh.readline().split()[1:]
        vals = [int(x) for x in parts]
        idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
        return idle, sum(vals)
    except (OSError, ValueError):
        return 0, 0


def _ram_fraction() -> float:
    try:
        info: dict[str, int] = {}
        with open("/proc/meminfo") as fh:
            for line in fh:
                k, _, rest = line.partition(":")
                info[k] = int(rest.split()[0])
        total = info.get("MemTotal", 0)
        avail = info.get("MemAvailable", info.get("MemFree", 0))
        return (total - avail) / total if total else 0.0
    except (OSError, ValueError):
        return 0.0


def _load_color(frac: float) -> str:
    """Green when comfortable, amber when busy, red when saturated."""
    if frac < 0.60:
        return "#22c55e"
    if frac < 0.85:
        return "#f59e0b"
    return "#ef4444"


class _Bar(QtWidgets.QWidget):
    """A rounded progress track painted from a 0..1 fraction, coloured by load."""

    def __init__(self, theme) -> None:
        super().__init__()
        self._frac = 0.0
        self._theme = theme
        self.setFixedHeight(8)

    def set_fraction(self, frac: float) -> None:
        self._frac = max(0.0, min(1.0, frac))
        self.update()

    def paintEvent(self, _e) -> None:  # noqa: N802
        from core.colors import to_qcolor
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        t = self._theme.tokens
        h = self.height()
        track = to_qcolor(t.get("surface_alt", "#1f232c"))
        p.setPen(Qt.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(0, 0, self.width(), h, h / 2, h / 2)
        w = int(self.width() * self._frac)
        if w > 0:
            p.setBrush(QtGui.QColor(_load_color(self._frac)))
            p.drawRoundedRect(0, 0, max(h, w), h, h / 2, h / 2)
        p.end()


class _SystemHealth(QtWidgets.QFrame):
    def __init__(self, ctx: WidgetContext) -> None:
        super().__init__()
        self._ctx = ctx
        self._prev = _cpu_times()
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(10)
        self._title = QtWidgets.QLabel()
        lay.addWidget(self._title)

        self._rows: dict[str, tuple[QtWidgets.QLabel, _Bar]] = {}
        for key, label in (("cpu", "CPU"), ("ram", "Memory"), ("disk", "Disk")):
            row = QtWidgets.QHBoxLayout()
            row.setSpacing(8)
            name = QtWidgets.QLabel(label)
            name.setFixedWidth(58)
            pct = QtWidgets.QLabel("—")
            pct.setFixedWidth(42)
            pct.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            bar = _Bar(ctx.theme)
            col = QtWidgets.QVBoxLayout()
            col.setSpacing(4)
            head = QtWidgets.QHBoxLayout()
            head.addWidget(name)
            head.addStretch(1)
            head.addWidget(pct)
            col.addLayout(head)
            col.addWidget(bar)
            lay.addLayout(col)
            self._rows[key] = (pct, bar)
            self._name_lbls = getattr(self, "_name_lbls", [])
            self._name_lbls.append(name)
        lay.addStretch(1)

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(_SAMPLE_MS)
        self._timer.timeout.connect(self._sample)
        self._apply_theme()
        ctx.theme.theme_changed.connect(self._apply_theme)

    def _apply_theme(self) -> None:
        t = self._ctx.theme.tokens
        self._title.setText(
            f"<span style='color:{t['accent']};'>▍</span> "
            f"<span style='color:{t['text']};font-size:15px;font-weight:700;'>"
            f"System Health</span>")
        for name in getattr(self, "_name_lbls", []):
            name.setStyleSheet(
                f"color:{t['muted']};font-size:12px;font-weight:600;background:transparent;")
        for pct, _bar in self._rows.values():
            pct.setStyleSheet(
                f"color:{t['text']};font-size:12px;font-weight:700;background:transparent;")

    def _sample(self) -> None:
        idle, total = _cpu_times()
        pidle, ptotal = self._prev
        dt = total - ptotal
        cpu = 1.0 - (idle - pidle) / dt if dt > 0 else 0.0
        self._prev = (idle, total)
        try:
            du = shutil.disk_usage("/")
            disk = du.used / du.total if du.total else 0.0
        except OSError:
            disk = 0.0
        for key, frac in (("cpu", cpu), ("ram", _ram_fraction()), ("disk", disk)):
            pct, bar = self._rows[key]
            pct.setText(f"{int(frac * 100)}%")
            bar.set_fraction(frac)

    def showEvent(self, e) -> None:  # noqa: N802
        self._prev = _cpu_times()
        self._sample()
        self._timer.start()
        super().showEvent(e)

    def hideEvent(self, e) -> None:  # noqa: N802
        self._timer.stop()
        super().hideEvent(e)


class SystemHealthPlugin(WidgetPlugin):
    id = "system_health"
    name = "System Health"
    description = "Live CPU, memory and disk usage from your machine."
    icon = "utilities-system-monitor"
    default_size = (1, 1)
    sizes = [(1, 1), (2, 1)]
    category = "Utilities"

    def create_view(self, ctx: WidgetContext) -> QtWidgets.QWidget:
        return _SystemHealth(ctx)
