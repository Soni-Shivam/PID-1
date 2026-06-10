"""Single import boundary for the Qt binding.

All application code imports Qt symbols from here and never from ``PyQt5``
(or ``PyQt6``) directly. This keeps a future binding switch a one-file change,
as mandated by CLAUDE.md.

Usage:
    from core.qt_compat import QtCore, QtGui, QtWidgets, Qt, exec_app
"""
from __future__ import annotations

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt

QT_BINDING = "PyQt5"

__all__ = ["QtCore", "QtGui", "QtWidgets", "Qt", "QT_BINDING", "exec_app"]


def exec_app(app: QtWidgets.QApplication) -> int:
    """Run the Qt event loop, hiding the PyQt5/PyQt6 ``exec_``/``exec`` split."""
    runner = getattr(app, "exec", None) or app.exec_
    return int(runner())
