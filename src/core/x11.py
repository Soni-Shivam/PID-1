"""EWMH/X11 plumbing for the shell, via python3-xlib only (no polling).

Provides the four mechanisms the dock (and later the menu/widgets) need:

- ``set_dock_type``     : mark a window _NET_WM_WINDOW_TYPE_DOCK (verified ME-02)
- ``set_bottom_strut``  : reserve screen space so maximized windows stop at the
                          dock edge via _NET_WM_STRUT(_PARTIAL) (verified ME-02)
- ``activate_window``   : raise+focus a window via _NET_ACTIVE_WINDOW (ME-06)
- ``ClientListWatcher`` : a QThread that blocks on root PropertyNotify and emits
                          Qt signals when _NET_CLIENT_LIST changes (ME-05); 0%
                          CPU while idle because it blocks in select().

Qt is imported through core.qt_compat; Xlib is a non-Qt dependency and may be
imported directly.
"""
from __future__ import annotations

import os
import select

from Xlib import X, XK, Xatom, display, error
from Xlib import protocol

from core.qt_compat import QtCore

# One display for main-thread (GUI) calls. The watcher thread opens its own,
# because a single Xlib Display connection must not be shared across threads.
_display: display.Display | None = None


def _get_display() -> display.Display:
    global _display
    if _display is None:
        _display = display.Display()
    return _display


def _atom(d: display.Display, name: str) -> int:
    return d.intern_atom(name)


def set_dock_type(win_id: int) -> None:
    """Mark the window as an EWMH dock (undecorated, on top, all desktops).

    Set this *before* the window is mapped for reliability: realize the native
    window via ``int(widget.winId())`` (creates but does not map it), call this,
    then ``widget.show()``. Re-assert after show() to survive Qt rewrites.
    """
    d = _get_display()
    w = d.create_resource_object("window", win_id)
    w.change_property(_atom(d, "_NET_WM_WINDOW_TYPE"), Xatom.ATOM, 32,
                      [_atom(d, "_NET_WM_WINDOW_TYPE_DOCK")])
    d.sync()


def set_bottom_strut(win_id: int, reserve: int, x0: int, x1: int) -> None:
    """Reserve ``reserve`` px at the screen bottom across [x0, x1].

    Coordinates are screen-relative (use the full screen geometry, not the
    available geometry). Sets both _NET_WM_STRUT (legacy, 4 values) and
    _NET_WM_STRUT_PARTIAL (12 values) for broad WM compatibility.
    """
    d = _get_display()
    w = d.create_resource_object("window", win_id)
    w.change_property(_atom(d, "_NET_WM_STRUT"), Xatom.CARDINAL, 32,
                      [0, 0, 0, reserve])
    w.change_property(_atom(d, "_NET_WM_STRUT_PARTIAL"), Xatom.CARDINAL, 32,
                      [0, 0, 0, reserve, 0, 0, 0, 0, 0, 0, x0, x1])
    d.sync()


def activate_window(win_id: int) -> None:
    """Raise and focus a window (incl. un-minimize) via _NET_ACTIVE_WINDOW."""
    d = _get_display()
    root = d.screen().root
    win = d.create_resource_object("window", win_id)
    ev = protocol.event.ClientMessage(
        window=win,
        client_type=_atom(d, "_NET_ACTIVE_WINDOW"),
        data=(32, [2, X.CurrentTime, 0, 0, 0]),  # source 2 = direct user action
    )
    root.send_event(ev, event_mask=X.SubstructureRedirectMask
                    | X.SubstructureNotifyMask)
    d.flush()


def _client_list(d: display.Display, root) -> list[int]:
    """Current _NET_CLIENT_LIST as window ids (empty on absence)."""
    prop = root.get_full_property(_atom(d, "_NET_CLIENT_LIST"), Xatom.WINDOW)
    return list(prop.value) if prop else []


def wm_class_of(win_id: int) -> str:
    """Best-effort WM_CLASS (the res_class) of a window, '' if unavailable."""
    d = _get_display()
    try:
        win = d.create_resource_object("window", win_id)
        pair = win.get_wm_class()
    except (error.BadWindow, error.XError):
        return ""
    if not pair:
        return ""
    return pair[1] or pair[0] or ""


class ClientListWatcher(QtCore.QThread):
    """Emit signals as top-level windows appear/disappear, event-driven.

    Subscribes to PropertyNotify on the root window and diffs _NET_CLIENT_LIST.
    Blocks in select() between events, so idle CPU is ~0. Stop with ``stop()``.
    """

    window_added = QtCore.pyqtSignal(str, int)   # (wm_class, win_id)
    window_removed = QtCore.pyqtSignal(int)       # (win_id)

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._stop_r, self._stop_w = os.pipe()

    def run(self) -> None:  # noqa: D102 (QThread entry point)
        d = display.Display()
        root = d.screen().root
        net_client_list = d.intern_atom("_NET_CLIENT_LIST")
        root.change_attributes(event_mask=X.PropertyChangeMask)
        d.sync()

        known = {int(w) for w in _client_list(d, root)}
        try:
            while True:
                readable, _, _ = select.select([d.fileno(), self._stop_r], [], [])
                if self._stop_r in readable:
                    break
                while d.pending_events():
                    ev = d.next_event()
                    if (ev.type == X.PropertyNotify
                            and ev.atom == net_client_list):
                        known = self._diff(d, root, known)
        finally:
            d.close()

    def _diff(self, d: display.Display, root, known: set[int]) -> set[int]:
        current = {int(w) for w in _client_list(d, root)}
        for win_id in current - known:
            self.window_added.emit(self._wm_class(d, win_id), win_id)
        for win_id in known - current:
            self.window_removed.emit(win_id)
        return current

    @staticmethod
    def _wm_class(d: display.Display, win_id: int) -> str:
        try:
            pair = d.create_resource_object("window", win_id).get_wm_class()
        except (error.BadWindow, error.XError):
            return ""
        if not pair:
            return ""
        return pair[1] or pair[0] or ""

    def stop(self) -> None:
        """Signal the run loop to exit and wait for the thread to finish."""
        try:
            os.write(self._stop_w, b"x")
        except OSError:
            pass
        self.wait(2000)
        for fd in (self._stop_r, self._stop_w):
            try:
                os.close(fd)
            except OSError:
                pass


_MOD_NAMES = {
    "super": X.Mod4Mask, "meta": X.Mod4Mask, "win": X.Mod4Mask,
    "ctrl": X.ControlMask, "control": X.ControlMask,
    "alt": X.Mod1Mask, "shift": X.ShiftMask,
}
# Lock-mask combinations so NumLock/CapsLock state does not defeat the grab.
_LOCK_VARIANTS = (0, X.LockMask, X.Mod2Mask, X.LockMask | X.Mod2Mask)


def parse_hotkey(spec: str) -> tuple[int, int]:
    """'Super+Space' -> (modifier_mask, keysym). Last token is the key."""
    parts = [p.strip() for p in spec.split("+") if p.strip()]
    mod = 0
    keysym = 0
    for part in parts:
        name = part.lower()
        if name in _MOD_NAMES:
            mod |= _MOD_NAMES[name]
        else:
            keysym = XK.string_to_keysym(part) or XK.string_to_keysym(name)
    return mod, keysym


class HotkeyListener(QtCore.QThread):
    """Grab a global key combo on the root window and emit ``pressed``.

    Blocks in select() between events (0% idle CPU); grabs every lock-mask
    variant so CapsLock/NumLock do not break it. Stop with ``stop()``.
    """

    pressed = QtCore.pyqtSignal()

    def __init__(self, spec: str, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._mod, self._keysym = parse_hotkey(spec)
        self._stop_r, self._stop_w = os.pipe()

    def valid(self) -> bool:
        return self._keysym != 0

    def run(self) -> None:  # noqa: D102 (QThread entry point)
        if not self.valid():
            return
        d = display.Display()
        root = d.screen().root
        keycode = d.keysym_to_keycode(self._keysym)
        if not keycode:
            d.close()
            return
        for variant in _LOCK_VARIANTS:
            root.grab_key(keycode, self._mod | variant, False,
                          X.GrabModeAsync, X.GrabModeAsync)
        d.sync()
        try:
            while True:
                readable, _, _ = select.select([d.fileno(), self._stop_r], [], [])
                if self._stop_r in readable:
                    break
                while d.pending_events():
                    ev = d.next_event()
                    if ev.type == X.KeyPress and ev.detail == keycode:
                        self.pressed.emit()
        finally:
            try:
                root.ungrab_key(keycode, X.AnyModifier)
                d.sync()
            except error.XError:
                pass
            d.close()

    def stop(self) -> None:
        """Signal the run loop to exit and wait for the thread to finish."""
        try:
            os.write(self._stop_w, b"x")
        except OSError:
            pass
        self.wait(2000)
        for fd in (self._stop_r, self._stop_w):
            try:
                os.close(fd)
            except OSError:
                pass
