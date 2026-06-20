from design_system import card_qss
from core.qt_compat import QtCore, QtGui, QtWidgets
from grid_manager import BaseWidgetCard, SlotSize


class SystemHealthWidget(BaseWidgetCard):
    SUPPORTED_SIZES = [SlotSize.SMALL, SlotSize.TALL]

    def __init__(self, state, size=SlotSize.SMALL):
        super().__init__("sys", size)
        self.setStyleSheet(f"SystemHealthWidget, QFrame#wcard {{ {card_qss('#241B1B')} }}")
        self.state = state

        l_sys = QtWidgets.QVBoxLayout(self)
        l_sys.setContentsMargins(16, 36, 16, 16)
        lbl_s_title = QtWidgets.QLabel("System Health")
        lbl_s_title.setStyleSheet("color:#FFFFFF; font-size:15px; font-weight:600; background:transparent;")
        l_sys.addWidget(lbl_s_title)
        l_sys.addSpacing(16)

        self.bars = {}
        self.lbls = {}
        for name, val in [("CPU", 10), ("RAM", 50), ("Storage", 35)]:
            row = QtWidgets.QHBoxLayout()
            lbl_n = QtWidgets.QLabel(name)
            lbl_n.setStyleSheet("color:#D4D4D8; font-size:13px; background:transparent;")
            lbl_v = QtWidgets.QLabel(f"{val}%")
            lbl_v.setStyleSheet("color:#D4D4D8; font-size:13px; background:transparent;")
            self.lbls[name] = lbl_v
            row.addWidget(lbl_n); row.addStretch(); row.addWidget(lbl_v)
            bar = QtWidgets.QProgressBar()
            bar.setFixedHeight(6); bar.setTextVisible(False); bar.setValue(val)
            bar.setStyleSheet("""
                QProgressBar{background:rgba(255,255,255,0.08);border-radius:3px;}
                QProgressBar::chunk{background:#F2F2F7;border-radius:3px;}
            """)
            self.bars[name] = bar
            l_sys.addLayout(row); l_sys.addSpacing(4); l_sys.addWidget(bar); l_sys.addSpacing(12)
        l_sys.addStretch()

        self.state.system_health_updated.connect(self.on_health_updated)

    def on_health_updated(self, cpu, ram, storage):
        for name, val in [("CPU", cpu), ("RAM", ram), ("Storage", storage)]:
            self.bars[name].setValue(val)
            self.lbls[name].setText(f"{val}%")
