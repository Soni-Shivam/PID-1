"""Widget plugin contract, auto-discovery, action handling, layout persistence.

Adding a widget = dropping one file in widgets/plugins/ that defines a
WidgetPlugin subclass. The engine discovers them, the desktop layer lays their
views out on a grid persisted to layout.json. CMS-fed widgets read their content
from the shared CmsService in the WidgetContext and refresh on its signal.
"""
from __future__ import annotations

import importlib
import pkgutil
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable

from core import store
from core.paths import config_file
from core.qt_compat import QtCore, QtGui, QtWidgets
from apps import launcher
from apps.desktop_entries import AppEntry

_LAYOUT = "layout.json"


@dataclass
class WidgetContext:
    """Everything a widget view needs at construction time."""
    cms: "object | None"            # CmsService (or None for non-CMS widgets)
    run_action: Callable[[str], None]
    username: str


class WidgetPlugin(ABC):
    """One widget type. Subclasses live in widgets/plugins/, one per file."""

    id: str = ""
    name: str = ""
    default_size: tuple[int, int] = (1, 1)   # (cols, rows) in grid units
    needs_cms: bool = False

    @abstractmethod
    def create_view(self, ctx: WidgetContext) -> QtWidgets.QWidget:
        """Build and return the widget's view."""


def discover_plugins() -> dict[str, WidgetPlugin]:
    """Instantiate every WidgetPlugin found under widgets/plugins/."""
    import widgets.plugins as pkg

    found: dict[str, WidgetPlugin] = {}
    for info in pkgutil.iter_modules(pkg.__path__):
        module = importlib.import_module(f"widgets.plugins.{info.name}")
        for attr in vars(module).values():
            if (isinstance(attr, type) and issubclass(attr, WidgetPlugin)
                    and attr is not WidgetPlugin):
                inst = attr()
                if inst.id:
                    found[inst.id] = inst
    return found


def execute_action(action: str, apps_by_id: dict[str, AppEntry]) -> None:
    """Run a namespaced CMS/tile action: 'app:<id>' or 'url:<url>'."""
    kind, _, payload = (action or "").partition(":")
    if kind == "app":
        app_id = payload[:-len(".desktop")] if payload.endswith(".desktop") else payload
        app = apps_by_id.get(app_id)
        if app:
            launcher.launch(app)
    elif kind == "url" and payload:
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(payload))


def default_layout() -> list[dict]:
    """First-run arrangement of the four built-in widgets (col,row,w,h)."""
    return [
        {"plugin_id": "greeting_clock", "col": 0, "row": 0, "w": 1, "h": 1},
        {"plugin_id": "quick_tiles", "col": 0, "row": 1, "w": 1, "h": 1},
        {"plugin_id": "carousel", "col": 1, "row": 0, "w": 1, "h": 2},
        {"plugin_id": "news", "col": 2, "row": 0, "w": 1, "h": 2},
    ]


def load_layout() -> list[dict]:
    saved = store.read_json(config_file(_LAYOUT), default=None)
    if isinstance(saved, list) and saved:
        return saved
    layout = default_layout()
    save_layout(layout)
    return layout


def save_layout(layout: list[dict]) -> None:
    store.write_json(config_file(_LAYOUT), layout)
