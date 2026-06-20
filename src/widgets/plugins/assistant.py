"""JioPC Assistant widget — an ask box that opens ChatGPT.

A self-styled accent card (card_chrome False) with a search field; submitting a
query opens ChatGPT prefilled with it via the shared run_action ("url:" handler),
i.e. https://chatgpt.com/?q=<query>. Colours come from theme tokens and restyle
on theme_changed.
"""
from __future__ import annotations

from urllib.parse import quote_plus

from core.qt_compat import Qt, QtCore, QtWidgets
from widgets.engine import WidgetContext, WidgetPlugin

_CHATGPT = "https://chatgpt.com/?q="


class _Assistant(QtWidgets.QFrame):
    def __init__(self, ctx: WidgetContext) -> None:
        super().__init__()
        self._ctx = ctx
        self.setObjectName("AssistantCard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(8)

        self._title = QtWidgets.QLabel("JioPC Assistant")
        self._sub = QtWidgets.QLabel("Ask anything — answered by ChatGPT")
        lay.addWidget(self._title)
        lay.addWidget(self._sub)
        lay.addStretch(1)

        row = QtWidgets.QHBoxLayout()
        row.setSpacing(8)
        self._input = QtWidgets.QLineEdit()
        self._input.setObjectName("AssistantInput")
        self._input.setPlaceholderText("Ask me anything…")
        self._input.setClearButtonEnabled(True)
        self._input.returnPressed.connect(self._ask)
        self._send = QtWidgets.QToolButton()
        self._send.setObjectName("AssistantSend")
        self._send.setText("➤")
        self._send.setCursor(Qt.PointingHandCursor)
        self._send.setFixedSize(38, 38)
        self._send.clicked.connect(self._ask)
        row.addWidget(self._input, 1)
        row.addWidget(self._send)
        lay.addLayout(row)

        self._apply_theme()
        ctx.theme.theme_changed.connect(self._apply_theme)

    def _ask(self) -> None:
        q = self._input.text().strip()
        if q:
            self._ctx.run_action(f"url:{_CHATGPT}{quote_plus(q)}")
            self._input.clear()

    def _apply_theme(self) -> None:
        t = self._ctx.theme.tokens
        self.setStyleSheet(
            f"#AssistantCard{{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            f"stop:0 {t['accent_soft']},stop:1 {t['surface']});"
            f"border:1px solid {t['accent']};border-radius:18px;}}"
            f"#AssistantInput{{background:{t['surface']};color:{t['text']};"
            f"border:1px solid {t['border']};border-radius:19px;"
            f"padding:8px 16px;font-size:13px;}}"
            f"#AssistantInput:focus{{border:1px solid {t['accent']};}}"
            f"#AssistantSend{{background:{t['accent']};color:{t['on_accent']};"
            f"border:none;border-radius:19px;font-size:15px;font-weight:700;}}"
            f"#AssistantSend:hover{{background:{t['indicator']};}}")
        self._title.setStyleSheet(
            f"color:{t['text']};font-size:15px;font-weight:800;background:transparent;")
        self._sub.setStyleSheet(
            f"color:{t['muted']};font-size:12px;background:transparent;")


class AssistantPlugin(WidgetPlugin):
    id = "assistant"
    name = "JioPC Assistant"
    description = "Ask anything and open ChatGPT with your question prefilled."
    icon = "help-browser"
    default_size = (1, 1)
    sizes = [(1, 1), (2, 1)]
    category = "Productivity"
    card_chrome = False

    def create_view(self, ctx: WidgetContext) -> QtWidgets.QWidget:
        return _Assistant(ctx)
