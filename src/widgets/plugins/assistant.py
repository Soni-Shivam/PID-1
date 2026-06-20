"""JioPC Assistant prompt widget — a self-styled accent card.

A small call-to-action card. card_chrome is False: it paints its own
accent-tinted background instead of the standard sidebar card chrome. Colours
come from theme tokens and restyle on theme_changed.
"""
from __future__ import annotations

from core.qt_compat import Qt, QtWidgets
from widgets.engine import WidgetContext, WidgetPlugin


class _Assistant(QtWidgets.QFrame):
    def __init__(self, ctx: WidgetContext) -> None:
        super().__init__()
        self._ctx = ctx
        self.setObjectName("AssistantCard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(3)
        self._title = QtWidgets.QLabel("JioPC Assistant")
        self._sub = QtWidgets.QLabel("Ask me to get started")
        lay.addWidget(self._title)
        lay.addWidget(self._sub)
        self._apply_theme()
        ctx.theme.theme_changed.connect(self._apply_theme)

    def _apply_theme(self) -> None:
        t = self._ctx.theme.tokens
        self.setStyleSheet(
            f"#AssistantCard{{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            f"stop:0 {t['accent_soft']},stop:1 {t['surface']});"
            f"border:1px solid {t['accent']};border-radius:16px;}}")
        self._title.setStyleSheet(
            f"color:{t['text']};font-size:13px;font-weight:700;background:transparent;")
        self._sub.setStyleSheet(
            f"color:{t['muted']};font-size:12px;background:transparent;")


class AssistantPlugin(WidgetPlugin):
    id = "assistant"
    name = "JioPC Assistant"
    description = "A quick prompt to get help and start tasks."
    icon = "help-browser"
    category = "Productivity"
    card_chrome = False

    def create_view(self, ctx: WidgetContext) -> QtWidgets.QWidget:
        return _Assistant(ctx)
