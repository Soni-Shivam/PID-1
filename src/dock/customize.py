"""Dock customisation dialog — pick which apps live in the dock.

A searchable, scrollable checklist of installed apps; ticking an app pins it to
the dock and unticking removes it, applied live so the dock updates as you go.
Only apps with a real icon are offered (same rule as the app drawer), so the
dock stays tidy. Chrome is themed by the app-wide stylesheet.
"""
from __future__ import annotations

from typing import Callable

from core.qt_compat import Qt, QtCore, QtGui, QtWidgets
from apps.desktop_entries import AppEntry
from dock.model import DockModel
from menu.app_model import _has_real_icon


class _AppRow(QtWidgets.QFrame):
    """One pickable row: icon + name + a pin checkbox."""

    toggled = QtCore.pyqtSignal(str, bool)   # (app_id, pinned)

    def __init__(self, app: AppEntry, pinned: bool) -> None:
        super().__init__()
        self.app = app
        self.setObjectName("dockPickRow")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)
        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(10, 6, 12, 6)
        row.setSpacing(12)

        icon = QtWidgets.QLabel()
        icon.setPixmap(QtGui.QIcon.fromTheme(app.icon).pixmap(28, 28))
        icon.setFixedSize(28, 28)
        row.addWidget(icon)

        name = QtWidgets.QLabel(app.name)
        name.setStyleSheet("background:transparent;font-size:13px;")
        row.addWidget(name, 1)

        self._check = QtWidgets.QCheckBox()
        self._check.setChecked(pinned)
        self._check.setCursor(Qt.PointingHandCursor)
        self._check.toggled.connect(lambda on: self.toggled.emit(self.app.app_id, on))
        row.addWidget(self._check, 0)

    def mousePressEvent(self, e) -> None:  # noqa: N802 - row click toggles
        if e.button() == Qt.LeftButton:
            self._check.toggle()
        super().mousePressEvent(e)


class DockCustomizeDialog(QtWidgets.QDialog):
    """Live dock-app picker driven by the DockModel."""

    def __init__(self, model: DockModel, theme, on_change: Callable[[], None],
                 parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._model = model
        self._theme = theme
        self._on_change = on_change
        self._rows: list[_AppRow] = []

        self.setWindowTitle("Choose dock apps")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setModal(True)
        self.resize(420, 560)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(14)

        title = QtWidgets.QLabel("Choose dock apps")
        title.setStyleSheet(
            f"color:{theme.tokens['text']};font-size:18px;font-weight:800;"
            f"background:transparent;")
        sub = QtWidgets.QLabel("Tick the apps you want pinned to the dock.")
        sub.setStyleSheet(
            f"color:{theme.tokens['muted']};font-size:12px;background:transparent;")
        root.addWidget(title)
        root.addWidget(sub)

        self._search = QtWidgets.QLineEdit()
        self._search.setPlaceholderText("Search apps")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._filter)
        root.addWidget(self._search)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background:transparent;")
        body = QtWidgets.QWidget()
        body.setStyleSheet("background:transparent;")
        self._list = QtWidgets.QVBoxLayout(body)
        self._list.setContentsMargins(0, 0, 0, 0)
        self._list.setSpacing(2)
        self._list.setAlignment(Qt.AlignTop)
        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        done = QtWidgets.QPushButton("Done")
        done.setDefault(True)
        done.setCursor(Qt.PointingHandCursor)
        done.clicked.connect(self.accept)
        root.addWidget(done, 0, Qt.AlignRight)

        self.setStyleSheet(
            "#dockPickRow{background:transparent;border-radius:10px;}"
            f"#dockPickRow:hover{{background:{theme.tokens['hover']};}}")
        self._populate()

    def _populate(self) -> None:
        pins = set(self._model.pins)
        for app in self._model.all_apps():
            if not _has_real_icon(app):
                continue
            row = _AppRow(app, app.app_id in pins)
            row.toggled.connect(self._on_toggle)
            self._rows.append(row)
            self._list.addWidget(row)

    def _on_toggle(self, app_id: str, pinned: bool) -> None:
        self._model.set_pinned(app_id, pinned)
        self._on_change()

    def _filter(self, text: str) -> None:
        q = text.strip().lower()
        for row in self._rows:
            row.setVisible(q in row.app.name.lower() or q in row.app.app_id.lower())
