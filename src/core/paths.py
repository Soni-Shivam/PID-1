"""XDG base paths for jiopc-home. All persistent state lives under these.

Config : ~/.config/jiopc/home/        (user choices: dock pins, theme, settings)
Data   : ~/.local/share/jiopc/home/   (usage log, custom themes)
Cache  : ~/.cache/jiopc/home/         (CMS feed + images; safe to delete)

Honours XDG_*_HOME env vars; never writes anywhere else (CLAUDE.md rule).
"""
from __future__ import annotations

import os
from pathlib import Path

_APP = ("jiopc", "home")


def _base(env_var: str, default: str) -> Path:
    root = os.environ.get(env_var) or str(Path.home() / default)
    return Path(root, *_APP)


CONFIG_DIR = _base("XDG_CONFIG_HOME", ".config")
DATA_DIR = _base("XDG_DATA_HOME", ".local/share")
CACHE_DIR = _base("XDG_CACHE_HOME", ".cache")


def ensure_dirs() -> None:
    """Create the three state directories if missing (idempotent)."""
    for d in (CONFIG_DIR, DATA_DIR, CACHE_DIR):
        d.mkdir(parents=True, exist_ok=True)


def config_file(name: str) -> Path:
    return CONFIG_DIR / name


def data_file(name: str) -> Path:
    return DATA_DIR / name


def cache_file(name: str) -> Path:
    return CACHE_DIR / name
