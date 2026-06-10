"""Dock state: pinned apps (persisted) and running-window tracking.

Pinned app ids live in ~/.config/jiopc/home/dock.json as an ordered list, so
order survives restarts. Running state is held in memory, fed by the
ClientListWatcher (WM_CLASS -> app via the desktop-entry index).
"""
from __future__ import annotations

from core import store
from core.paths import config_file
from apps.desktop_entries import AppEntry, index_by_wm_class, list_apps

_DOCK_JSON = "dock.json"

# First-run default pins, in order; only those actually installed are kept.
_DEFAULT_CANDIDATES = (
    "firefox", "firefox-esr", "chromium", "google-chrome",   # browser
    "pcmanfm-qt", "org.kde.dolphin", "nautilus",             # file manager
    "qterminal", "lxterminal", "xterm",                      # terminal
    "featherpad", "org.gnome.gedit",                         # editor
    "lxqt-config",                                           # settings
)


class DockModel:
    """Holds pinned order, the app catalogue, and live running state."""

    def __init__(self) -> None:
        self._apps: dict[str, AppEntry] = {a.app_id: a for a in list_apps()}
        self._wm_index = index_by_wm_class(list(self._apps.values()))
        self.pins: list[str] = self._load_pins()
        # app_id -> list of running window ids (insertion order = age)
        self.running: dict[str, list[int]] = {}

    # --- pins -------------------------------------------------------------
    def _load_pins(self) -> list[str]:
        saved = store.read_json(config_file(_DOCK_JSON), default=None)
        if isinstance(saved, list) and saved:
            return [a for a in saved if a in self._apps]
        pins = self._default_pins()
        self._save(pins)
        return pins

    def _default_pins(self) -> list[str]:
        chosen: list[str] = []
        for app_id in _DEFAULT_CANDIDATES:
            if app_id in self._apps and app_id not in chosen:
                chosen.append(app_id)
        return chosen

    def _save(self, pins: list[str] | None = None) -> None:
        store.write_json(config_file(_DOCK_JSON),
                         pins if pins is not None else self.pins)

    def pin(self, app_id: str) -> None:
        if app_id in self._apps and app_id not in self.pins:
            self.pins.append(app_id)
            self._save()

    def unpin(self, app_id: str) -> None:
        if app_id in self.pins:
            self.pins.remove(app_id)
            self._save()

    def move(self, app_id: str, delta: int) -> None:
        """Shift a pinned app left (-1) or right (+1), persisting the order."""
        if app_id not in self.pins:
            return
        i = self.pins.index(app_id)
        j = max(0, min(len(self.pins) - 1, i + delta))
        if i != j:
            self.pins.insert(j, self.pins.pop(i))
            self._save()

    def reorder(self, ordered_ids: list[str]) -> None:
        """Replace pin order wholesale (used by drag-reorder)."""
        self.pins = [a for a in ordered_ids if a in self._apps]
        self._save()

    # --- catalogue / running ---------------------------------------------
    def app(self, app_id: str) -> AppEntry | None:
        return self._apps.get(app_id)

    def is_pinned(self, app_id: str) -> bool:
        return app_id in self.pins

    def is_running(self, app_id: str) -> bool:
        return bool(self.running.get(app_id))

    def windows(self, app_id: str) -> list[int]:
        return self.running.get(app_id, [])

    def add_window(self, wm_class: str, win_id: int) -> str | None:
        """Record a new running window; return the matched app_id (or None)."""
        app = self._wm_index.get((wm_class or "").lower())
        if not app:
            return None
        self.running.setdefault(app.app_id, [])
        if win_id not in self.running[app.app_id]:
            self.running[app.app_id].append(win_id)
        return app.app_id

    def remove_window(self, win_id: int) -> str | None:
        """Drop a closed window; return the affected app_id (or None)."""
        for app_id, wins in self.running.items():
            if win_id in wins:
                wins.remove(win_id)
                if not wins:
                    del self.running[app_id]
                return app_id
        return None

    def visible_items(self) -> list[str]:
        """Pinned apps in order, followed by running-but-unpinned apps."""
        items = list(self.pins)
        for app_id in self.running:
            if app_id not in items:
                items.append(app_id)
        return items
