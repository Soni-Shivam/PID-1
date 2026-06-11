"""Theme engine: token JSON -> QSS template -> live app-wide restyle (Phase D).

A theme is a flat dict of tokens (colours + font) stored as JSON. Bundled themes
live in src/themes/; user-saved custom themes in DATA_DIR/themes/. The shell
chrome stylesheet (themes/base.qss.tmpl) is rendered with string.Template and
applied via QApplication.setStyleSheet; the chosen font is applied via
QApplication.setFont. Any change emits ``theme_changed`` so custom-painted bits
(dock indicator dot, carousel page dots) and per-widget plugin styles repaint.

User accent/font tweaks are kept as ``theme_overrides`` in settings.json and
layered on top of whichever base theme is active, so they persist across switches.
No module-level state: the single instance is threaded through constructors.
"""
from __future__ import annotations

from pathlib import Path
from string import Template
from typing import Any

from core import store
from core.paths import DATA_DIR, config_file
from core.qt_compat import QtCore, QtGui, QtWidgets

_BUNDLED_DIR = Path(__file__).resolve().parent.parent / "themes"
_USER_DIR = DATA_DIR / "themes"
_TEMPLATE = _BUNDLED_DIR / "base.qss.tmpl"
_SETTINGS = "settings.json"
DEFAULT_THEME = "dark"
_OVERRIDE_KEYS = ("accent", "font_family", "font_size_base")


class ThemeManager(QtCore.QObject):
    """Loads themes, renders the QSS template, applies it live to the app."""

    theme_changed = QtCore.pyqtSignal()

    def __init__(self, app: QtWidgets.QApplication,
                 parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._app = app
        settings = self._settings()
        self._name = settings.get("theme", DEFAULT_THEME)
        self._overrides: dict[str, Any] = settings.get("theme_overrides", {}) or {}
        self._tokens: dict[str, Any] = {}
        self._load_tokens(self._name)

    # --- public state -----------------------------------------------------
    @property
    def tokens(self) -> dict[str, Any]:
        """Current merged tokens (read by QPainter code that can't use QSS)."""
        return self._tokens

    @property
    def name(self) -> str:
        return self._name

    def available_themes(self) -> list[str]:
        names = {p.stem for p in _BUNDLED_DIR.glob("*.json")}
        if _USER_DIR.is_dir():
            names |= {p.stem for p in _USER_DIR.glob("*.json")}
        return sorted(names)

    # --- apply ------------------------------------------------------------
    def apply(self) -> None:
        """Render the template and push it (+ font) to the whole application."""
        qss = Template(_TEMPLATE.read_text(encoding="utf-8")).safe_substitute(
            self._tokens)
        self._app.setStyleSheet(qss)
        family = self._tokens.get("font_family", "")
        size = int(self._tokens.get("font_size_base", 10))
        if family:
            self._app.setFont(QtGui.QFont(family, size))
        self.theme_changed.emit()

    # --- mutators (persist + re-apply) ------------------------------------
    def set_theme(self, name: str) -> None:
        if name == self._name:
            return
        self._name = name
        self._load_tokens(name)
        self._persist()
        self.apply()

    def set_accent(self, hex_color: str) -> None:
        self._overrides["accent"] = hex_color
        self._tokens["accent"] = hex_color
        self._tokens["indicator"] = hex_color
        self._persist()
        self.apply()

    def set_font(self, family: str, size: int) -> None:
        self._overrides["font_family"] = family
        self._overrides["font_size_base"] = int(size)
        self._tokens["font_family"] = family
        self._tokens["font_size_base"] = int(size)
        self._persist()
        self.apply()

    def save_custom(self, name: str) -> str:
        """Snapshot current tokens to a self-contained user theme and switch to it."""
        name = name.strip().replace("/", "-") or "custom"
        _USER_DIR.mkdir(parents=True, exist_ok=True)
        tokens = dict(self._tokens)
        tokens["name"] = name
        store.write_json(_USER_DIR / f"{name}.json", tokens)
        self._name = name
        self._overrides = {}
        self._tokens = tokens
        self._persist()
        self.apply()
        return name

    # --- internals --------------------------------------------------------
    def _load_tokens(self, name: str) -> None:
        # Floor with the bundled default so a partial custom theme can't crash.
        tokens = dict(self._read(_BUNDLED_DIR / f"{DEFAULT_THEME}.json"))
        tokens.update(self._read(_BUNDLED_DIR / f"{name}.json"))
        tokens.update(self._read(_USER_DIR / f"{name}.json"))
        for key in _OVERRIDE_KEYS:
            if key in self._overrides:
                tokens[key] = self._overrides[key]
        if "accent" in self._overrides:
            tokens["indicator"] = self._overrides["accent"]
        self._tokens = tokens

    @staticmethod
    def _read(path: Path) -> dict[str, Any]:
        data = store.read_json(path, default={})
        return data if isinstance(data, dict) else {}

    def _settings(self) -> dict[str, Any]:
        return store.read_json(config_file(_SETTINGS), default={}) or {}

    def _persist(self) -> None:
        settings = self._settings()
        settings["theme"] = self._name
        settings["theme_overrides"] = self._overrides
        store.write_json(config_file(_SETTINGS), settings)
