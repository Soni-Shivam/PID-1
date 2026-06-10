"""Launch usage tracking, shared by the dock and the menu.

Records per-app launch count and last-launch time to a single JSON file under
the data dir. The application menu (Phase B) reads this for Recently Used,
Most Used, and the Recommended scoring. Kept deliberately small here.
"""
from __future__ import annotations

import time
from typing import Any

from core import store
from core.paths import data_file

_USAGE = "usage.json"


def _load() -> dict[str, Any]:
    return store.read_json(data_file(_USAGE), default={}) or {}


def record_launch(app_id: str) -> None:
    """Increment the launch count and stamp the last-launch time for app_id."""
    if not app_id:
        return
    data = _load()
    entry = data.get(app_id) or {"count": 0, "last_ts": 0.0}
    entry["count"] = int(entry.get("count", 0)) + 1
    entry["last_ts"] = time.time()
    data[app_id] = entry
    store.write_json(data_file(_USAGE), data)


def stats() -> dict[str, Any]:
    """Return the raw usage map: {app_id: {count, last_ts}}."""
    return _load()
