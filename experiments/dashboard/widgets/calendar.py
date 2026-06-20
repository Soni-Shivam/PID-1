from core.qt_compat import QtCore, QtGui, QtWidgets
from grid_manager import BaseWidgetCard, SlotSize
from design_system import card_qss, label_qss
import datetime
import calendar


class CalendarWidget(BaseWidgetCard):
    """Calendar widget showing a full month grid."""
    SUPPORTED_SIZES = [SlotSize.LARGE, SlotSize.TALL, SlotSize.WIDE, SlotSize.SMALL]

    def __init__(self, state=None, size: SlotSize = SlotSize.LARGE):
        super().__init__("calendar", size)
        
        # Use the dark theme color from the reference image
        self.setStyleSheet(f"CalendarWidget, QFrame#wcard {{ {card_qss('#1C1C1E')} }}")
        
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(24, 32, 24, 24)
        root.setSpacing(12)

        # ── Header ──────────────────────────────────────────────────────────
        hdr = QtWidgets.QHBoxLayout()
        lbl_title = QtWidgets.QLabel("Calendar")
        lbl_title.setStyleSheet(label_qss(color="#FFFFFF", size=20, weight="600"))
        
        btn_prev = QtWidgets.QPushButton("‹")
        btn_next = QtWidgets.QPushButton("›")
        for btn in (btn_prev, btn_next):
            btn.setFixedSize(28, 28)
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #8E8E93;
                    font-size: 22px;
                    border: none;
                }
                QPushButton:hover { color: #FFFFFF; }
            """)
        
        hdr.addWidget(lbl_title)
        hdr.addStretch()
        hdr.addWidget(btn_prev)
        hdr.addWidget(btn_next)
        root.addLayout(hdr)
        root.addSpacing(8)

        # ── Grid ────────────────────────────────────────────────────────────
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(8)
        
        # Days of week header
        days = ["S", "M", "T", "W", "T", "F", "S"]
        for i, d in enumerate(days):
            lbl = QtWidgets.QLabel(d)
            lbl.setAlignment(QtCore.Qt.AlignCenter)
            lbl.setStyleSheet(label_qss(color="#8E8E93", size=13, weight="600"))
            grid.addWidget(lbl, 0, i)
            
        # Draw calendar days
        now = datetime.datetime.now()
        cal = calendar.Calendar(firstweekday=6) # Sunday first
        month_days = cal.monthdatescalendar(now.year, now.month)
        
        today = now.date()
        event1 = today + datetime.timedelta(days=6)
        event2 = today + datetime.timedelta(days=7)
        
        for row_idx, week in enumerate(month_days):
            # Tell the grid to allow this row to expand vertically
            grid.setRowStretch(row_idx + 1, 1)
            for col_idx, date in enumerate(week):
                # Tell the grid to allow this column to expand horizontally
                grid.setColumnStretch(col_idx, 1)
                
                lbl = QtWidgets.QLabel(str(date.day))
                lbl.setAlignment(QtCore.Qt.AlignCenter)
                
                # Make labels expand instead of being fixed
                lbl.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
                lbl.setMinimumSize(32, 32)
                
                if date.month != now.month:
                    lbl.setStyleSheet(label_qss(color="#48484A", size=15, weight="bold"))
                elif date == today:
                    lbl.setStyleSheet("""
                        QLabel {
                            background: #F2F2F7;
                            color: #000000;
                            border-radius: 8px;
                            font-size: 15px;
                            font-weight: 700;
                        }
                    """)
                elif date == event1:
                    lbl.setStyleSheet("""
                        QLabel {
                            background: #3B5249;
                            color: #A7F3D0;
                            border-radius: 8px;
                            font-size: 15px;
                            font-weight: 700;
                        }
                    """)
                elif date == event2:
                    lbl.setStyleSheet("""
                        QLabel {
                            background: #1E40AF;
                            color: #93C5FD;
                            border-radius: 8px;
                            font-size: 15px;
                            font-weight: 700;
                        }
                    """)
                else:
                    lbl.setStyleSheet(label_qss(color="#E5E5EA", size=15, weight="bold"))
                    
                grid.addWidget(lbl, row_idx + 1, col_idx)

        # Center the grid and let it stretch
        root.addLayout(grid)
        root.addStretch(1)
