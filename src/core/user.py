"""Shared user-identity and time-of-day helpers.

A single source for the user's display name (passwd GECOS field, falling back to
the login name) and the time-of-day salutation, so the greeting widget, the menu
header and the wizard all read the same person and phrasing. No Qt dependency,
no global state.
"""
from __future__ import annotations

import os
import pwd
import time


def full_name() -> str:
    """The user's real name (GECOS), else the login name, else empty."""
    try:
        info = pwd.getpwuid(os.getuid())
        return (info.pw_gecos or "").split(",")[0] or info.pw_name
    except KeyError:
        return ""


def first_name(fallback: str = "there") -> str:
    """Just the first token of the display name, for a friendly greeting."""
    name = full_name()
    return name.split()[0] if name else fallback


def salutation(hour: int | None = None) -> str:
    """Time-of-day greeting; uses the current local hour when none is given."""
    if hour is None:
        hour = time.localtime().tm_hour
    if hour < 12:
        return "Good morning"
    if hour < 17:
        return "Good afternoon"
    return "Good evening"
