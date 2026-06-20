from core.qt_compat import QtCore, QtGui, QtWidgets
from grid_manager import BaseWidgetCard, SlotSize

class HeroLearningWidget(BaseWidgetCard):
    SUPPORTED_SIZES = [SlotSize.WIDE, SlotSize.LARGE]

    def __init__(self, state, size=SlotSize.LARGE):
        super().__init__("hero", size)
        self.state = state
        self.setStyleSheet("""
            HeroLearningWidget {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #1a1a24,stop:1 #2d2d3b);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 12px;
            }
        """)

        l_main = QtWidgets.QVBoxLayout(self)
        l_main.setContentsMargins(32, 48, 32, 32)
        l_main.addStretch()

        lbl_title = QtWidgets.QLabel("Start learning")
        lbl_title.setStyleSheet("color:#FFFFFF; font-size:32px; font-weight:700; background:transparent;")

        lbl_sub = QtWidgets.QLabel("Got a doubt? We've got you.")
        lbl_sub.setStyleSheet("color:#D4D4D8; font-size:16px; background:transparent;")

        l_main.addWidget(lbl_title)
        l_main.addWidget(lbl_sub)
        l_main.addSpacing(20)

        btns = QtWidgets.QHBoxLayout()
        btn_start = QtWidgets.QPushButton("Start learning")
        btn_start.setFixedSize(140, 42)
        btn_start.setStyleSheet("QPushButton{background:#FFFFFF;color:#000;border-radius:21px;font-size:14px;font-weight:600;}")

        btn_info = QtWidgets.QPushButton("More info")
        btn_info.setFixedSize(110, 42)
        btn_info.setStyleSheet("QPushButton{background:transparent;color:#FFFFFF;border:1px solid rgba(255,255,255,0.3);border-radius:21px;font-size:14px;font-weight:600;}")

        btns.addWidget(btn_start)
        btns.addWidget(btn_info)
        btns.addStretch()

        l_main.addLayout(btns)
        l_main.addStretch()
