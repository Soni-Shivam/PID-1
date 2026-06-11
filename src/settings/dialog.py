"""Appearance settings dialog (Phase D).

Theme picker, accent colour, and font family/size - every control applies live
through the ThemeManager (no OK-to-see-it), and the choice persists in
settings.json. "Save as custom" snapshots the current look as a named theme.
Prettification of this dialog is a Day 7-8 polish-sprint item; today it proves
the engine end to end.
"""
from __future__ import annotations

from core.qt_compat import QtGui, QtWidgets
from core.theme import ThemeManager


class SettingsDialog(QtWidgets.QDialog):
    """Live appearance editor backed by a ThemeManager."""

    def __init__(self, theme: ThemeManager,
                 parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = theme
        self.setWindowTitle("Appearance")
        self.setMinimumWidth(360)

        form = QtWidgets.QFormLayout(self)

        self._themes = QtWidgets.QComboBox()
        self._reload_themes()
        self._themes.currentTextChanged.connect(self._on_theme)
        form.addRow("Theme", self._themes)

        self._accent_btn = QtWidgets.QPushButton("Choose accent...")
        self._accent_btn.clicked.connect(self._on_accent)
        form.addRow("Accent", self._accent_btn)

        self._font = QtWidgets.QFontComboBox()
        self._font.setCurrentFont(QtGui.QFont(theme.tokens.get("font_family", "")))
        self._font.currentFontChanged.connect(self._on_font)
        form.addRow("Font", self._font)

        self._size = QtWidgets.QSpinBox()
        self._size.setRange(8, 18)
        self._size.setValue(int(theme.tokens.get("font_size_base", 10)))
        self._size.valueChanged.connect(self._on_font)
        form.addRow("Font size", self._size)

        save = QtWidgets.QPushButton("Save as custom...")
        save.clicked.connect(self._on_save_custom)
        close = QtWidgets.QPushButton("Close")
        close.clicked.connect(self.accept)
        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(save)
        buttons.addStretch(1)
        buttons.addWidget(close)
        form.addRow(buttons)

    # --- handlers ---------------------------------------------------------
    def _reload_themes(self) -> None:
        self._themes.blockSignals(True)
        self._themes.clear()
        self._themes.addItems(self._theme.available_themes())
        self._themes.setCurrentText(self._theme.name)
        self._themes.blockSignals(False)

    def _on_theme(self, name: str) -> None:
        if name:
            self._theme.set_theme(name)

    def _on_accent(self) -> None:
        current = QtGui.QColor(self._theme.tokens.get("accent", ""))
        color = QtWidgets.QColorDialog.getColor(current, self, "Accent colour")
        if color.isValid():
            self._theme.set_accent(color.name())

    def _on_font(self) -> None:
        self._theme.set_font(self._font.currentFont().family(), self._size.value())

    def _on_save_custom(self) -> None:
        name, ok = QtWidgets.QInputDialog.getText(
            self, "Save theme", "Name for this theme:")
        if ok and name.strip():
            saved = self._theme.save_custom(name)
            self._reload_themes()
            self._themes.setCurrentText(saved)
