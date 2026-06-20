"""Runtime secrets (API keys) read from outside version control.

Resolves a key in this order: the process environment, then a ``.env`` file at
the project root (next to ``src/``), then ``~/.config/jiopc/home/secrets.json``.
Returns '' when absent so callers degrade gracefully. The ``.env`` file is
gitignored (the repo is public); deploy.sh copies it to the VM so the key is
available at runtime without being committed.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from core import store
from core.paths import config_file

# src/core/secrets.py -> parents[2] is the repo root (and ~/jiopc-home on the VM).
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


@lru_cache(maxsize=1)
def _dotenv() -> dict[str, str]:
    data: dict[str, str] = {}
    try:
        for raw in _ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            data[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return data


def get(key: str, default: str = "") -> str:
    """Return the secret for *key*, or *default* if it cannot be found."""
    val = os.environ.get(key)
    if val:
        return val
    val = _dotenv().get(key)
    if val:
        return val
    secrets = store.read_json(config_file("secrets.json"), default={}) or {}
    return secrets.get(key, default) or default
