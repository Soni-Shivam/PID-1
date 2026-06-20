"""
Widget 5: JioPC Assistant — 2×1 Wide Search / AI Bar
=====================================================
Spec-accurate optimisations:
  • 2-stop linear gradient for background (minimal calculation).
  • Fake search bar is actually a QPushButton (no QLineEdit caret blinking,
    no input method hooks, zero idle CPU overhead).
"""
from core.qt_compat import QtCore, QtGui, QtWidgets
from grid_manager import BaseWidgetCard, SlotSize
from design_system import (
    RADIUS, TEXT_PRIMARY,
    card_qss
)

class JiopcAssistantWidget(BaseWidgetCard):
    """2×1 Wide Assistant/Search widget."""
    SUPPORTED_SIZES = [SlotSize.WIDE]

    def __init__(self, state=None, size: SlotSize = SlotSize.WIDE):
        super().__init__("assistant", size)
        self.setStyleSheet(f"JiopcAssistantWidget, QFrame#wcard {{ {card_qss('#1E1A22')} }}")

        # 2-stop simple linear gradient (blue to purple) + faux depth
        self.setStyleSheet(f"""
            JiopcAssistantWidget {{
                border-radius: {RADIUS}px;
                border-top:  1px solid rgba(255,255,255,0.18);
                border-left: 1px solid rgba(255,255,255,0.18);
                border-bottom: 1px solid rgba(0,0,0,0.40);
                border-right:  1px solid rgba(0,0,0,0.40);
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #3B82F6,
                    stop:1 #8B5CF6
                );
            }}
        """)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)
        root.setAlignment(QtCore.Qt.AlignVCenter)

        # Greeting
        self._lbl_greeting = QtWidgets.QLabel("Hi Rakesh, how can I help you today?")
        self._lbl_greeting.setStyleSheet(
            "color:#FFFFFF; font-size:18px; font-weight:700;"
            " background:transparent; letter-spacing:0.5px;")
        
        # Fake search bar (QPushButton)
        self._btn_search = QtWidgets.QPushButton("   Ask me anything...")
        self._btn_search.setFixedHeight(48)
        self._btn_search.setCursor(QtCore.Qt.PointingHandCursor)
        self._btn_search.setStyleSheet(f"""
            QPushButton {{
                background: #FFFFFF;
                color: #6B7280;
                border: none;
                border-radius: 24px;
                font-size: 15px;
                font-weight: 500;
                text-align: left;
                padding-left: 16px;
            }}
            QPushButton:hover {{
                background: #F9FAFB;
                color: #374151;
            }}
            QPushButton:pressed {{
                background: #E5E7EB;
            }}
        """)
        self._btn_search.clicked.connect(self._on_search_clicked)

        root.addWidget(self._lbl_greeting)
        root.addWidget(self._btn_search)

    def _on_search_clicked(self):
        print("[Assistant] Search bar clicked")
