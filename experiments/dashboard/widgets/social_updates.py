from design_system import card_qss
from core.qt_compat import QtCore, QtGui, QtWidgets
from grid_manager import BaseWidgetCard, SlotSize

class SocialUpdatesWidget(BaseWidgetCard):
    SUPPORTED_SIZES = [SlotSize.SMALL, SlotSize.TALL]

    def __init__(self, state, size=SlotSize.SMALL):
        super().__init__("social", size)
        self.setStyleSheet(f"SocialUpdatesWidget, QFrame#wcard {{ {card_qss('#221A20')} }}")
        self.state = state

        l_main = QtWidgets.QVBoxLayout(self)
        l_main.setContentsMargins(16, 36, 16, 16)

        lbl_title = QtWidgets.QLabel("Social Updates")
        lbl_title.setStyleSheet("color:#FFFFFF; font-size:15px; font-weight:600; background:transparent;")
        l_main.addWidget(lbl_title)
        l_main.addSpacing(14)

        for name, msg, color in [
            ("Mikeart", "messages for you for your liiat!", "#3b82f6"),
            ("Jahana Masar", "Will amsdranize the headers of our project", "#a855f7"),
        ]:
            row = QtWidgets.QHBoxLayout()
            avatar = QtWidgets.QLabel()
            avatar.setFixedSize(32, 32)
            avatar.setStyleSheet(f"background:{color}; border-radius:16px;")

            vbox = QtWidgets.QVBoxLayout()
            vbox.setSpacing(1)
            lbl_n = QtWidgets.QLabel(name)
            lbl_n.setStyleSheet("color:#FFFFFF; font-size:12px; font-weight:600; background:transparent;")
            lbl_m = QtWidgets.QLabel(msg)
            lbl_m.setStyleSheet("color:#71717A; font-size:11px; background:transparent;")
            lbl_m.setWordWrap(True)
            vbox.addWidget(lbl_n)
            vbox.addWidget(lbl_m)

            row.addWidget(avatar)
            row.addSpacing(10)
            row.addLayout(vbox)
            l_main.addLayout(row)
            l_main.addSpacing(12)

        l_main.addStretch()
