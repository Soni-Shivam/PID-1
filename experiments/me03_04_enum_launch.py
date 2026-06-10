"""ME-03 + ME-04: enumerate .desktop apps, then launch from Exec=.

ME-03 PASS: prints visible apps (id/name/categories/icon?), NoDisplay excluded,
            count in the same ballpark as LxQt's own menu; Flatpak apps (if any)
            appear; WM_CLASS index resolves a known app.
ME-04 PASS: launches real apps via parsed Exec=, no zombies, usage.json updated.

Run in VM: DISPLAY=:0 python3 experiments/me03_04_enum_launch.py
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from PyQt5.QtCore import QTimer  # noqa: E402
from PyQt5.QtGui import QIcon  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

from apps import launcher, usage  # noqa: E402
from apps.desktop_entries import index_by_wm_class, list_apps  # noqa: E402


def main() -> None:
    app = QApplication([])  # needed for QIcon.fromTheme + QProcess

    apps = list_apps()
    print(f"ME-03: {len(apps)} visible apps enumerated", flush=True)
    flatpaks = [a for a in apps if "/flatpak/" in a.path]
    print(f"ME-03: flatpak-exported apps: {len(flatpaks)}", flush=True)
    print("--- sample (first 12) ---", flush=True)
    for a in apps[:12]:
        has_icon = not QIcon.fromTheme(a.icon).isNull() if a.icon else False
        print(f"  {a.app_id:32.32} | {a.name:22.22} | icon={'Y' if has_icon else 'n'}"
              f" | {','.join(a.categories[:3])}", flush=True)

    idx = index_by_wm_class(apps)
    for probe in ("qterminal", "pcmanfm-qt", "firefox"):
        hit = idx.get(probe)
        print(f"ME-03 wm_class '{probe}' -> {hit.app_id if hit else 'NO MATCH'}",
              flush=True)

    # ME-04: launch a couple of real apps via parsed Exec=.
    targets = [a for a in apps if a.app_id in ("qterminal", "featherpad")]
    launched = []
    for a in targets:
        ok = launcher.launch(a)
        print(f"ME-04 launch {a.app_id}: exec='{a.exec_cmd}' -> {ok}", flush=True)
        if ok:
            launched.append(a.app_id)

    def check_then_quit() -> None:
        print("ME-04 usage.json:", {k: v["count"] for k, v in usage.stats().items()
                                     if k in launched}, flush=True)
        # leave zombie check to the shell (ps) after we close the apps
        for name in ("qterminal", "featherpad"):
            os.system(f"pkill -x {name} 2>/dev/null")
        time.sleep(0.5)
        z = os.popen("ps -eo stat,comm | awk '$1 ~ /Z/ {print}'").read().strip()
        print(f"ME-04 zombies after close: {z or 'none'}", flush=True)
        app.quit()

    QTimer.singleShot(2500, check_then_quit)
    app.exec_()
    print("ME-03/04 done", flush=True)


if __name__ == "__main__":
    main()
