"""Music Player widget — controls the system media player via MPRIS.

Real integration with zero new daemons: it shells out to ``playerctl`` (the
standard MPRIS CLI) to read the now-playing metadata and to play/pause, skip and
go back. Album art, title, artist and a progress bar mirror the active player;
with no ``playerctl`` installed or nothing playing it shows a tidy idle state.

Budget-safe: a refresh timer runs only while the widget is visible, ticking
every second while a track is playing and slowly otherwise; it never runs at all
when ``playerctl`` is absent. Colours come from theme tokens.
"""
from __future__ import annotations

import shutil
import subprocess

from core.qt_compat import Qt, QtCore, QtGui, QtWidgets
from widgets.engine import WidgetContext, WidgetPlugin
from widgets.image_cache import ImageCache

_PLAYERCTL = shutil.which("playerctl")
_FMT = "{{status}}|{{title}}|{{artist}}|{{mpris:artUrl}}|{{position}}|{{mpris:length}}"
_TICK_PLAYING = 1000
_TICK_IDLE = 4000


def _run(*args: str) -> str:
    if not _PLAYERCTL:
        return ""
    try:
        out = subprocess.run([_PLAYERCTL, *args], capture_output=True,
                             text=True, timeout=1.5)
        return out.stdout.strip() if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def _fmt_time(micros: int) -> str:
    secs = max(0, micros // 1_000_000)
    return f"{secs // 60}:{secs % 60:02d}"


def _glyph_button(icon_name: str, fallback: str, size: int) -> QtWidgets.QToolButton:
    b = QtWidgets.QToolButton()
    icon = QtGui.QIcon.fromTheme(icon_name)
    if icon.isNull():
        b.setText(fallback)
    else:
        b.setIcon(icon)
        b.setIconSize(QtCore.QSize(size, size))
    b.setCursor(Qt.PointingHandCursor)
    b.setAutoRaise(True)
    return b


class _MusicPlayer(QtWidgets.QFrame):
    def __init__(self, ctx: WidgetContext) -> None:
        super().__init__()
        self._ctx = ctx
        self._cache = ImageCache(self)
        self._art_url = ""
        self._playing = False

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(12)

        head = QtWidgets.QHBoxLayout()
        self._title = QtWidgets.QLabel("Music Player")
        head.addWidget(self._title, 1)
        self._more = QtWidgets.QLabel("• • •")
        head.addWidget(self._more, 0, Qt.AlignRight)
        root.addLayout(head)

        mid = QtWidgets.QHBoxLayout()
        mid.setSpacing(14)
        info = QtWidgets.QVBoxLayout()
        info.setSpacing(2)
        info.addStretch(1)
        self._track = QtWidgets.QLabel("Nothing playing")
        self._track.setWordWrap(True)
        self._artist = QtWidgets.QLabel("—")
        info.addWidget(self._track)
        info.addWidget(self._artist)
        info.addStretch(1)
        mid.addLayout(info, 1)
        self._art = QtWidgets.QLabel()
        self._art.setFixedSize(96, 96)
        self._art.setAlignment(Qt.AlignCenter)
        mid.addWidget(self._art, 0)
        root.addLayout(mid)

        self._bar = QtWidgets.QProgressBar()
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(6)
        self._bar.setRange(0, 1000)
        root.addWidget(self._bar)

        times = QtWidgets.QHBoxLayout()
        self._pos = QtWidgets.QLabel("0:00")
        self._len = QtWidgets.QLabel("0:00")
        times.addWidget(self._pos, 0, Qt.AlignLeft)
        times.addStretch(1)
        times.addWidget(self._len, 0, Qt.AlignRight)
        root.addLayout(times)

        ctrls = QtWidgets.QHBoxLayout()
        ctrls.setSpacing(10)
        ctrls.addStretch(1)
        self._b_shuffle = _glyph_button("media-playlist-shuffle", "⇄", 18)
        self._b_prev = _glyph_button("media-skip-backward", "⏮", 22)
        self._b_play = _glyph_button("media-playback-start", "▶", 24)
        self._b_next = _glyph_button("media-skip-forward", "⏭", 22)
        self._b_repeat = _glyph_button("media-playlist-repeat", "↻", 18)
        self._b_play.setObjectName("musicPlay")
        self._b_play.setFixedSize(52, 52)
        for b in (self._b_shuffle, self._b_prev, self._b_play,
                  self._b_next, self._b_repeat):
            ctrls.addWidget(b)
        ctrls.addStretch(1)
        root.addLayout(ctrls)
        root.addStretch(1)

        self._b_prev.clicked.connect(lambda: self._control("previous"))
        self._b_next.clicked.connect(lambda: self._control("next"))
        self._b_play.clicked.connect(lambda: self._control("play-pause"))
        self._b_shuffle.clicked.connect(lambda: self._control("shuffle", "Toggle"))
        self._b_repeat.clicked.connect(lambda: self._control("loop", "Track"))

        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._update)

        self._apply_theme()
        ctx.theme.theme_changed.connect(self._apply_theme)

    # --- theme ------------------------------------------------------------
    def _apply_theme(self) -> None:
        t = self._ctx.theme.tokens
        self._title.setStyleSheet(
            f"color:{t['text']};font-size:18px;font-weight:800;background:transparent;")
        self._more.setStyleSheet(
            f"color:{t['muted']};font-size:14px;background:transparent;")
        self._track.setStyleSheet(
            f"color:{t['text']};font-size:18px;font-weight:700;background:transparent;")
        self._artist.setStyleSheet(
            f"color:{t['muted']};font-size:13px;background:transparent;")
        for lbl in (self._pos, self._len):
            lbl.setStyleSheet(
                f"color:{t['muted']};font-size:10px;background:transparent;")
        self._bar.setStyleSheet(
            f"QProgressBar{{background:{t['surface_alt']};border:none;"
            f"border-radius:3px;}}"
            f"QProgressBar::chunk{{background:{t['text']};border-radius:3px;}}")
        glyph = (f"QToolButton{{color:{t['text']};background:transparent;"
                 f"border:none;font-size:18px;}}"
                 f"QToolButton:hover{{color:{t['accent']};}}")
        for b in (self._b_shuffle, self._b_prev, self._b_next, self._b_repeat):
            b.setStyleSheet(glyph)
        self._b_play.setStyleSheet(
            f"QToolButton#musicPlay{{color:#10101a;background:{t['text']};"
            f"border:none;border-radius:26px;font-size:22px;font-weight:800;}}"
            f"QToolButton#musicPlay:hover{{background:{t['accent']};color:#ffffff;}}")
        self._refresh_placeholder_art()

    # --- data -------------------------------------------------------------
    def _control(self, *args: str) -> None:
        _run(*args)
        QtCore.QTimer.singleShot(120, self._update)

    def _update(self) -> None:
        line = _run("metadata", "--format", _FMT)
        if not line:
            self._show_idle()
            return
        parts = (line.split("|") + [""] * 6)[:6]
        status, title, artist, art_url, pos, length = parts
        self._playing = status.lower() == "playing"
        self._track.setText(title or "Unknown track")
        self._artist.setText(artist or "Unknown artist")
        try:
            p_us, l_us = int(pos or 0), int(length or 0)
        except ValueError:
            p_us, l_us = 0, 0
        self._pos.setText(_fmt_time(p_us))
        self._len.setText(_fmt_time(l_us))
        self._bar.setValue(int(1000 * p_us / l_us) if l_us else 0)
        self._set_play_glyph(self._playing)
        self._load_art(art_url)
        self._retime()

    def _show_idle(self) -> None:
        self._playing = False
        self._track.setText("Nothing playing")
        msg = "Open a music app to control it here" if _PLAYERCTL \
            else "Install playerctl to enable controls"
        self._artist.setText(msg)
        self._pos.setText("0:00")
        self._len.setText("0:00")
        self._bar.setValue(0)
        self._set_play_glyph(False)
        self._art_url = ""
        self._refresh_placeholder_art()
        self._retime()

    def _set_play_glyph(self, playing: bool) -> None:
        name = "media-playback-pause" if playing else "media-playback-start"
        icon = QtGui.QIcon.fromTheme(name)
        if icon.isNull():
            self._b_play.setText("⏸" if playing else "▶")
        else:
            self._b_play.setIcon(icon)
            self._b_play.setIconSize(QtCore.QSize(24, 24))

    # --- album art --------------------------------------------------------
    def _load_art(self, url: str) -> None:
        if url == self._art_url:
            return
        self._art_url = url
        if url.startswith("file://"):
            pm = QtGui.QPixmap(url[len("file://"):])
            self._set_art(pm)
        elif url.startswith(("http://", "https://")):
            self._cache.fetch(url, QtCore.QSize(96, 96), self._on_remote_art)
        else:
            self._refresh_placeholder_art()

    def _on_remote_art(self, url: str, pixmap: QtGui.QPixmap) -> None:
        if url == self._art_url:
            self._set_art(pixmap)

    def _set_art(self, pm: QtGui.QPixmap) -> None:
        if pm is None or pm.isNull():
            self._refresh_placeholder_art()
            return
        self._art.setPixmap(self._rounded(pm, 96, 96))

    def _refresh_placeholder_art(self) -> None:
        t = self._ctx.theme.tokens
        from core.colors import to_qcolor
        pm = QtGui.QPixmap(96, 96)
        pm.fill(Qt.transparent)
        p = QtGui.QPainter(pm)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        grad = QtGui.QLinearGradient(0, 0, 96, 96)
        grad.setColorAt(0, to_qcolor(t.get("accent", "#b15cff")))
        grad.setColorAt(1, to_qcolor(t.get("accent_soft", "#2a1846")))
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(0, 0, 96, 96), 16, 16)
        p.fillPath(path, QtGui.QBrush(grad))
        p.setPen(QtGui.QColor("#ffffff"))
        f = p.font()
        f.setPointSize(30)
        p.setFont(f)
        p.drawText(pm.rect(), Qt.AlignCenter, "♪")
        p.end()
        self._art.setPixmap(pm)

    @staticmethod
    def _rounded(pm: QtGui.QPixmap, w: int, h: int, r: int = 16) -> QtGui.QPixmap:
        scaled = pm.scaled(w, h, Qt.KeepAspectRatioByExpanding,
                           Qt.SmoothTransformation)
        x = max(0, (scaled.width() - w) // 2)
        y = max(0, (scaled.height() - h) // 2)
        cropped = scaled.copy(x, y, w, h)
        out = QtGui.QPixmap(w, h)
        out.fill(Qt.transparent)
        p = QtGui.QPainter(out)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(0, 0, w, h), r, r)
        p.setClipPath(path)
        p.drawPixmap(0, 0, cropped)
        p.end()
        return out

    # --- visibility-gated timer ------------------------------------------
    def _retime(self) -> None:
        if not _PLAYERCTL or not self.isVisible():
            self._timer.stop()
            return
        self._timer.start(_TICK_PLAYING if self._playing else _TICK_IDLE)

    def showEvent(self, e) -> None:  # noqa: N802
        self._update()
        super().showEvent(e)

    def hideEvent(self, e) -> None:  # noqa: N802
        self._timer.stop()
        super().hideEvent(e)


class MusicPlayerPlugin(WidgetPlugin):
    id = "music_player"
    name = "Music Player"
    description = "Control your media player — track, art and playback."
    icon = "multimedia-audio-player"
    default_size = (2, 1)
    sizes = [(2, 1), (2, 2), (1, 2)]
    category = "Entertainment"

    def create_view(self, ctx: WidgetContext) -> QtWidgets.QWidget:
        return _MusicPlayer(ctx)
