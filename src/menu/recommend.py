"""Recently-used, most-used, and recommended-app selection.

All functions are pure over the app catalogue plus usage.stats(); no usage-schema
change is needed because the user's category-preference vector is derived on the
fly from the categories of apps they have launched (weighted by launch count).

Recommended formula: among apps never launched (count == 0), score each by the
cosine-style overlap between its category set and the user's weighted category
vector, i.e. sum of the user's weight for each category the app declares,
normalised by sqrt(number of categories the app declares). Ties are broken by a
per-session random jitter so the row feels alive across opens. Falls back to a
random sample when there is no usage history yet.
"""
from __future__ import annotations

import math
import random
from collections import defaultdict

from apps import usage
from apps.desktop_entries import AppEntry

_SESSION = random.Random()  # seeded once per process for stable-within-session ties


def _launched(apps: list[AppEntry], stats: dict) -> list[tuple[AppEntry, dict]]:
    return [(a, stats[a.app_id]) for a in apps if a.app_id in stats]


def recently_used(apps: list[AppEntry], n: int = 8) -> list[AppEntry]:
    """Apps the user launched, newest first."""
    stats = usage.stats()
    launched = _launched(apps, stats)
    launched.sort(key=lambda pair: pair[1].get("last_ts", 0.0), reverse=True)
    return [a for a, _ in launched[:n]]


def most_used(apps: list[AppEntry], n: int = 8) -> list[AppEntry]:
    """Apps the user launched, highest count first."""
    stats = usage.stats()
    launched = _launched(apps, stats)
    launched.sort(key=lambda pair: pair[1].get("count", 0), reverse=True)
    return [a for a, _ in launched[:n]]


def _category_vector(apps: list[AppEntry], stats: dict) -> dict[str, float]:
    """Weighted category preferences from launch history."""
    vec: dict[str, float] = defaultdict(float)
    by_id = {a.app_id: a for a in apps}
    for app_id, rec in stats.items():
        app = by_id.get(app_id)
        if not app:
            continue
        weight = float(rec.get("count", 0)) or 1.0
        for cat in app.categories:
            vec[cat] += weight
    return vec


def recommended(apps: list[AppEntry], n: int = 8) -> list[AppEntry]:
    """Never-launched apps most relevant to the user's category history."""
    stats = usage.stats()
    candidates = [a for a in apps if a.app_id not in stats and a.categories]
    if not candidates:
        return []
    vec = _category_vector(apps, stats)
    if not vec:  # no history yet: surface a fresh random sample
        return _SESSION.sample(candidates, min(n, len(candidates)))

    def score(app: AppEntry) -> float:
        overlap = sum(vec.get(cat, 0.0) for cat in app.categories)
        norm = math.sqrt(len(app.categories))
        jitter = _SESSION.random() * 0.01
        return overlap / norm + jitter

    candidates.sort(key=score, reverse=True)
    return candidates[:n]
