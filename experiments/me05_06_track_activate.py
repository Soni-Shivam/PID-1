"""ME-05 + ME-06: event-driven window tracking + window activation.

ME-05 PASS: '+'/'-' lines print as windows open/close, with WM_CLASS resolved;
            watcher idles at ~0% CPU between events (verify with pidstat).
ME-06 PASS: activate_window() makes the target the _NET_ACTIVE_WINDOW.

Self-driving: launches xclock, activates it, then closes it, so the add /
activate / remove events all appear in the log without manual interaction.

Run in VM: DISPLAY=:0 python3 experiments/me05_06_track_activate.py
CPU check:  pidstat -p $(pgrep -f me05_06) 1 8   (while it idles)
"""
from __future__ import annotations

import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from Xlib import Xatom, display  # noqa: E402

from PyQt5.QtCore import QTimer  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

from core.x11 import ClientListWatcher, activate_window  # noqa: E402

_d = display.Display()
_root = _d.screen().root


def active_window() -> int:
    p = _root.get_full_property(_d.intern_atom("_NET_ACTIVE_WINDOW"),
                               Xatom.WINDOW)
    return int(p.value[0]) if p and p.value else 0


def client_list() -> list[int]:
    p = _root.get_full_property(_d.intern_atom("_NET_CLIENT_LIST"),
                               Xatom.WINDOW)
    return list(p.value) if p else []


def main() -> None:
    app = QApplication([])
    watcher = ClientListWatcher()
    watcher.window_added.connect(
        lambda cls, wid: print(f"+ {cls or '<no-class>'} 0x{wid:x}", flush=True))
    watcher.window_removed.connect(
        lambda wid: print(f"- 0x{wid:x}", flush=True))
    watcher.start()
    print("watcher started; idling (open/close apps to see events)", flush=True)

    proc: dict[str, subprocess.Popen] = {}

    def launch() -> None:
        before = set(client_list())
        proc["xclock"] = subprocess.Popen(
            ["xclock"], env={**os.environ, "DISPLAY": ":0"})
        print("launched xclock", flush=True)
        QTimer.singleShot(1500, lambda: do_activate(before))

    def do_activate(before: set[int]) -> None:
        new = [w for w in client_list() if w not in before]
        if not new:
            print("ME-06 SKIP: xclock window not found", flush=True)
            return
        target = int(new[0])
        activate_window(target)
        QTimer.singleShot(400, lambda: report_activate(target))

    def report_activate(target: int) -> None:
        act = active_window()
        ok = "PASS" if act == target else "FAIL"
        print(f"ME-06 {ok}: target=0x{target:x} active=0x{act:x}", flush=True)

    def close() -> None:
        if proc.get("xclock"):
            proc["xclock"].terminate()
            print("closed xclock", flush=True)

    def finish() -> None:
        watcher.stop()
        app.quit()

    QTimer.singleShot(2000, launch)
    QTimer.singleShot(6000, close)
    QTimer.singleShot(9000, finish)
    app.exec_()
    print("ME-05/06 done", flush=True)


if __name__ == "__main__":
    main()
