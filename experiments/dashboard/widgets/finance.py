from design_system import card_qss
from core.qt_compat import QtCore, QtGui, QtWidgets
from grid_manager import BaseWidgetCard, SlotSize

class FinanceWidget(BaseWidgetCard):
    SUPPORTED_SIZES = [SlotSize.SMALL, SlotSize.WIDE]

    def __init__(self, state, size=SlotSize.SMALL):
        super().__init__("finance", size)
        self.setStyleSheet(f"FinanceWidget, QFrame#wcard {{ {card_qss('#1B221C')} }}")
        self.state = state

        l_main = QtWidgets.QVBoxLayout(self)
        l_main.setContentsMargins(16, 36, 16, 16)

        lbl_title = QtWidgets.QLabel("Finance")
        lbl_title.setStyleSheet("color:#FFFFFF; font-size:15px; font-weight:600; background:transparent;")
        l_main.addWidget(lbl_title)
        l_main.addSpacing(14)

        for name, val, up in [("Bank", "17,325", True), ("Stock", "6.98%", True), ("EMF Market", "12.99%", True)]:
            row = QtWidgets.QHBoxLayout()
            lbl_n = QtWidgets.QLabel(name)
            lbl_n.setStyleSheet("color:#D4D4D8; font-size:13px; background:transparent;")
            col = "#22c55e" if up else "#ef4444"
            arr = "▲" if up else "▼"
            lbl_v = QtWidgets.QLabel(f"<span style='color:{col}'>{arr} {val}</span>")
            lbl_v.setStyleSheet("font-size:13px; font-weight:600; background:transparent;")
            row.addWidget(lbl_n)
            row.addStretch()
            row.addWidget(lbl_v)
            l_main.addLayout(row)
            l_main.addSpacing(8)

        l_main.addStretch()
