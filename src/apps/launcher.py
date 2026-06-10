"""Launch applications from their .desktop Exec= line (ME-04).

Strips desktop-entry field codes (%f %F %u %U ...), runs the command detached
so it survives our process and leaves no zombies, and records the launch in
usage.py. Used by both the dock and the application menu.
"""
from __future__ import annotations

import shlex

from core.qt_compat import QtCore
from apps import usage
from apps.desktop_entries import AppEntry

# Field codes per the desktop-entry spec; all dropped (we pass no files/URLs).
_FIELD_CODES = {"%f", "%F", "%u", "%U", "%i", "%c", "%k",
                "%d", "%D", "%n", "%N", "%v", "%m"}


def strip_field_codes(exec_cmd: str) -> str:
    """Remove Exec= field codes, collapsing '%%' to a literal '%'."""
    out: list[str] = []
    for token in shlex.split(exec_cmd):
        if token in _FIELD_CODES:
            continue
        out.append(token.replace("%%", "%"))
    return " ".join(shlex.quote(t) for t in out)


def launch(app: AppEntry) -> bool:
    """Launch an app detached; record usage. Returns True if it started."""
    cmd = strip_field_codes(app.exec_cmd)
    if not cmd:
        return False
    ok = QtCore.QProcess.startDetached("/bin/sh", ["-c", cmd])
    if ok:
        usage.record_launch(app.app_id)
    return bool(ok)
