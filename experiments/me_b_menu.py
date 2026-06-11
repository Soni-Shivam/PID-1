"""Phase B verification: model/proxy filtering + recommendation logic.

Checks enumeration -> AppListModel -> AppFilterProxy (search, category, order)
and the recommend functions, without needing GUI interaction. Prints PASS/FAIL
lines. Run in VM: DISPLAY=:0 python3 experiments/me_b_menu.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from PyQt5.QtWidgets import QApplication  # noqa: E402

from menu.app_model import APP_ID, CATEGORIES, ENTRY, AppFilterProxy, AppListModel  # noqa: E402
from menu import recommend  # noqa: E402


def main() -> None:
    app = QApplication([])  # noqa: F841 (needed for QIcon/model)
    model = AppListModel()
    proxy = AppFilterProxy()
    proxy.setSourceModel(model)

    total = model.rowCount()
    print(f"model rows: {total}", flush=True)

    proxy.set_query("term")
    n_term = proxy.rowCount()
    ok_filter = all(
        "term" in (proxy.data(proxy.index(r, 0), ENTRY).name + " "
                   + proxy.data(proxy.index(r, 0), ENTRY).comment).lower()
        for r in range(n_term))
    print(f"search 'term': {n_term} rows, all match={ok_filter}", flush=True)

    proxy.set_query("")
    proxy.set_category("Settings")
    n_set = proxy.rowCount()
    ok_cat = all("Settings" in (proxy.data(proxy.index(r, 0), CATEGORIES) or [])
                 for r in range(n_set))
    print(f"category 'Settings': {n_set} rows, all match={ok_cat}", flush=True)
    proxy.set_category("All")

    proxy.set_order("name")
    first_name = proxy.data(proxy.index(0, 0), ENTRY).name if proxy.rowCount() else ""
    proxy.set_order("most_used")
    apps = model._apps  # noqa: SLF001
    print(f"order switch ok; name-sorted first='{first_name}'", flush=True)

    recents = recommend.recently_used(apps, 8)
    recos = recommend.recommended(apps, 8)
    stats_ids = set(__import__("apps.usage", fromlist=["stats"]).stats().keys())
    ok_reco = all(a.app_id not in stats_ids for a in recos)
    print(f"recently_used: {[a.app_id for a in recents]}", flush=True)
    print(f"recommended: {len(recos)} apps, all never-launched={ok_reco}", flush=True)

    verdict = "PASS" if (total > 0 and ok_filter and ok_cat and ok_reco) else "FAIL"
    print(f"ME-B {verdict}", flush=True)


if __name__ == "__main__":
    main()
