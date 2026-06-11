"""Enumerate installed applications from .desktop files (ME-03).

Scans system, per-user, and Flatpak export directories, parses each entry with
PyXDG, skips hidden/no-display entries, and de-duplicates by desktop-file id
with precedence user > system. Also builds a WM_CLASS -> app index the dock
uses to match running windows to their launcher icon.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from xdg.BaseDirectory import xdg_data_dirs, xdg_data_home
from xdg.DesktopEntry import DesktopEntry


@dataclass(frozen=True)
class AppEntry:
    app_id: str                       # desktop-file id (filename minus .desktop)
    name: str
    comment: str
    categories: tuple[str, ...]
    exec_cmd: str
    icon: str
    startup_wm_class: str
    terminal: bool
    path: str

    @property
    def wm_class_keys(self) -> tuple[str, ...]:
        """Lowercased keys for matching a running window's WM_CLASS, ordered
        most-specific first: StartupWMClass, app-id, app-id last segment, the
        executable basename, then Name.

        The executable key is essential for apps that lack StartupWMClass and
        whose window class follows their binary - e.g. Flatpak GNOME apps, whose
        wrapper carries ``--command=gnome-calculator`` while the app-id is
        ``org.gnome.Calculator`` (the live window reports ``gnome-calculator``)."""
        keys: list[str] = []
        for raw in (self.startup_wm_class, self.app_id,
                    self.app_id.rsplit(".", 1)[-1], _exec_basename(self.exec_cmd),
                    self.name):
            k = (raw or "").lower()
            if k and k not in keys:
                keys.append(k)
        return tuple(keys)


_EXEC_WRAPPERS = {"flatpak", "env", "sh", "bash", "run", "snap", "gtk-launch"}


def _exec_basename(exec_cmd: str) -> str:
    """Best-guess WM_CLASS hint from an Exec line: the sandboxed command for a
    Flatpak wrapper (``--command=X``), otherwise the first real binary's basename
    (skipping wrappers and field codes)."""
    tokens = (exec_cmd or "").split()
    for tok in tokens:
        if tok.startswith("--command="):
            return os.path.basename(tok.split("=", 1)[1])
    for tok in tokens:
        if tok.startswith(("-", "%")) or "=" in tok:
            continue
        base = os.path.basename(tok)
        if base and base not in _EXEC_WRAPPERS:
            return base
    return ""


def app_dirs() -> list[Path]:
    """Application directories, user-first so user entries win de-duplication.

    Public so the menu can watch these paths for live install/remove updates.
    """
    dirs: list[Path] = [Path(xdg_data_home) / "applications"]
    dirs += [Path(d) / "applications" for d in xdg_data_dirs]
    dirs += [
        Path(xdg_data_home) / "flatpak/exports/share/applications",
        Path("/var/lib/flatpak/exports/share/applications"),
    ]
    seen: set[Path] = set()
    ordered: list[Path] = []
    for d in dirs:
        if d not in seen:
            seen.add(d)
            ordered.append(d)
    return ordered


def _parse(path: Path) -> AppEntry | None:
    try:
        de = DesktopEntry(str(path))
    except Exception:
        return None
    if de.getType() != "Application":
        return None
    if de.getNoDisplay() or de.getHidden():
        return None
    name = de.getName()
    if not name:
        return None
    return AppEntry(
        app_id=path.stem,
        name=name,
        comment=de.getComment() or "",
        categories=tuple(de.getCategories()),
        exec_cmd=de.getExec() or "",
        icon=de.getIcon() or "",
        startup_wm_class=de.getStartupWMClass() or "",
        terminal=bool(de.getTerminal()),
        path=str(path),
    )


def list_apps() -> list[AppEntry]:
    """All visible applications, de-duplicated by id (user > system), by name."""
    by_id: dict[str, AppEntry] = {}
    for directory in app_dirs():
        if not directory.is_dir():
            continue
        for root, _, files in os.walk(directory):
            for fname in files:
                if not fname.endswith(".desktop"):
                    continue
                app_id = os.path.relpath(os.path.join(root, fname),
                                         directory)[:-len(".desktop")]
                app_id = app_id.replace("/", "-")
                if app_id in by_id:
                    continue  # earlier (higher-priority) dir already supplied it
                entry = _parse(Path(root, fname))
                if entry is not None:
                    object.__setattr__(entry, "app_id", app_id)
                    by_id[app_id] = entry
    return sorted(by_id.values(), key=lambda a: a.name.lower())


def index_by_wm_class(apps: list[AppEntry] | None = None) -> dict[str, AppEntry]:
    """Map lowercased WM_CLASS candidates -> AppEntry for dock matching."""
    apps = apps if apps is not None else list_apps()
    index: dict[str, AppEntry] = {}
    for app in apps:
        for key in app.wm_class_keys:
            index.setdefault(key, app)
    return index


def match_wm_class(wm_class: str,
                   index: dict[str, AppEntry]) -> AppEntry | None:
    """Resolve a running window's WM_CLASS to an app, '' -> None."""
    return index.get((wm_class or "").lower()) if wm_class else None
