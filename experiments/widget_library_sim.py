"""Premium Widget Library Simulation - Sidebar Layout.
Matches the provided Stitch mockup with a vertical category sidebar,
vibrant aurora background, and updated widget cards.
"""
import sys
import os
import json

# Setup import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from core.qt_compat import QtCore, QtGui, QtWidgets

# Updated Mock data matching the new image
WIDGETS_DATA = [
    {
        "id": "focus_timer",
        "category": "Productivity",
        "title": "Focus Timer",
        "desc": "Pomodoro & countdown sessions",
        "top_bg": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #333333, stop:1 #222222)",
        "top_content": "<div style='text-align:center;'><span style='font-size:12px; font-weight:400; background: rgba(255,255,255,0.08); padding: 4px 12px; border-radius: 10px;'>Focus &nbsp;&nbsp; Break &nbsp;&nbsp; Rest</span><br><br><b style='font-size:32px; font-weight:600; color:#F2F2F7;'>30:00</b><br><br><span style='font-size:13px; font-weight:500; background: #F2F2F7; color: #111111; padding: 6px 16px; border-radius: 12px;'>▶ Start</span></div>"
    },
    {
        "id": "top_headlines",
        "category": "Information",
        "title": "Top Headlines",
        "desc": "These are the quick actions for your most used apps",
        "top_bg": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #222222, stop:1 #111111)",
        "top_content": "<div align='left'><span style='font-size:12px; font-weight:400; color:#A1A1AA;'>ISRO launches new satellite...<hr>Sensex crosses 85,000 mark<hr>Exclusive: CMF Phone 3 Pro Specs<hr>IPL 2026: Mumbai Indians beat CSK</span></div>",
        "added": True
    },
    {
        "id": "weather",
        "category": "Information",
        "title": "Weather",
        "desc": "Sunny, today",
        "top_bg": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1a1a1a, stop:1 #000000)",
        "top_content": "<div align='left'><b style='font-size:15px; font-weight:500; color:#F2F2F7;'>Sunny</b><br><br><span style='font-size:36px; font-weight:500; color:#F2F2F7;'>☀️ 22°C</span><br><span style='font-size:12px; color:#A1A1AA;'>📍 Location, M</span></div>"
    },
    {
        "id": "jiopc_assistant",
        "category": "A.I.",
        "title": "Assistant",
        "desc": "",
        "top_bg": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2b2b2b, stop:1 #111111)",
        "top_content": "<div align='center'><b style='font-size:16px; font-weight:600; color:#F2F2F7;'><span style='color:#3b82f6'>Jio</span>PC Assistant</b><br><span style='font-size:12px; font-weight:400; color:#A1A1AA;'>Just ask to get started</span><br><br><span style='font-size:28px; background: rgba(255,255,255,0.08); padding: 10px; border-radius: 25px;'>🎤</span></div>"
    },
    {
        "id": "calendar",
        "category": "Productivity",
        "title": "",
        "desc": "",
        "top_bg": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2a2a2a, stop:1 #1a1a1a)",
        "top_content": "<div align='left'><b style='font-size:15px; font-weight:500; color:#F2F2F7;'>Calendar <span style='float:right'> < > </span></b><br><span style='font-size:11px; font-family: monospace; color:#D4D4D8;'>S  M  T  W  T  F  S<br>      1  2  3  4  5<br>6  7  8  9 10 11 <span style='background:#F2F2F7;color:#111111;border-radius:4px;'>12</span><br>13 14 15 16 17 18 <span style='color:#3b82f6'>19</span><br>20 21 22 23 24 25 26<br>27 28 29 30 31</span></div>"
    },
    {
        "id": "discover_jiopc",
        "category": "Information",
        "title": "Discover JioPC",
        "desc": "A full computer on your TV. Browse, create...",
        "top_bg": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #111111, stop:1 #000000)",
        "top_content": "<div align='center'><span style='font-size:48px;'>📺</span><br></div>"
    }
]

CATEGORIES = [("⭐ For You", "For You"), ("All", "All"), ("Information", "Information"), 
              ("Productivity", "Productivity"), ("Entertainment", "Entertainment"), 
              ("Finance", "Finance"), ("Education", "Education"), ("Shopping", "Shopping"), 
              ("Sports", "Sports"), ("A.I.", "A.I."), ("Utilities", "Utilities")]

# Prioritize softer, rounded modern fonts before falling back to system defaults.
MODERN_FONT_STACK = "'Outfit', 'Nunito', 'Quicksand', 'Inter', 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"

COMMON_SCROLLBAR_QSS = f"""
    * {{
        font-family: {MODERN_FONT_STACK};
    }}
    QScrollBar:vertical {{
        border: none;
        background: transparent;
        width: 6px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: rgba(255, 255, 255, 0.15);
        min-height: 20px;
        border-radius: 3px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: rgba(255, 255, 255, 0.3);
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        border: none;
        background: none;
    }}
    QScrollBar:horizontal {{
        height: 0px;
    }}
"""


class SearchBar(QtWidgets.QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Search widgets")
        self.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                color: #F2F2F7;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 20px;
                padding: 10px 40px;
                font-size: 14px;
                font-weight: 500;
            }
            QLineEdit:focus {
                border: 1px solid rgba(255, 255, 255, 0.4);
                background-color: rgba(0, 0, 0, 0.2);
            }
        """)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        search_icon = QtWidgets.QLabel("🔍")
        search_icon.setStyleSheet("color: #A1A1AA; background: transparent; font-size: 16px;")
        mic_icon = QtWidgets.QLabel("🎤")
        mic_icon.setStyleSheet("color: #A1A1AA; background: transparent; font-size: 16px;")
        layout.addWidget(search_icon, 0, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        layout.addStretch()
        layout.addWidget(mic_icon, 0, QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)


class WidgetCard(QtWidgets.QWidget):
    added = QtCore.pyqtSignal(str)

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self.data = data
        self._added = data.get("added", False)
        self.init_ui()

    def init_ui(self):
        self.setMinimumSize(250, 320)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        
        self.setStyleSheet("""
            WidgetCard > QWidget#CardRoot {
                background-color: rgba(20, 20, 20, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 20px;
            }
        """)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        card_root = QtWidgets.QWidget()
        card_root.setObjectName("CardRoot")
        card_layout = QtWidgets.QVBoxLayout(card_root)
        card_layout.setContentsMargins(1, 1, 1, 1)
        card_layout.setSpacing(0)

        # Top section (Preview)
        self.top_frame = QtWidgets.QFrame()
        self.top_frame.setMinimumHeight(180)
        self.top_frame.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.top_frame.setStyleSheet(f"""
            QFrame {{
                background: {self.data['top_bg']};
                border-top-left-radius: 19px;
                border-top-right-radius: 19px;
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }}
        """)
        top_layout = QtWidgets.QVBoxLayout(self.top_frame)
        top_layout.setContentsMargins(16, 16, 16, 16)
        preview_lbl = QtWidgets.QLabel(self.data['top_content'])
        preview_lbl.setStyleSheet(f"color: #F2F2F7; font-family: {MODERN_FONT_STACK};")
        preview_lbl.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignTop)
        preview_lbl.setWordWrap(True)
        top_layout.addWidget(preview_lbl)
        card_layout.addWidget(self.top_frame, 3)

        # Bottom section (Info + Action)
        self.bottom_frame = QtWidgets.QFrame()
        self.bottom_frame.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        self.bottom_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
            }
        """)
        bottom_layout = QtWidgets.QVBoxLayout(self.bottom_frame)
        bottom_layout.setContentsMargins(16, 12, 16, 16)
        bottom_layout.setSpacing(4)

        if self.data['title']:
            title_lbl = QtWidgets.QLabel(self.data['title'])
            title_lbl.setAlignment(QtCore.Qt.AlignCenter)
            # Softer white, slightly less thick weight
            title_lbl.setStyleSheet("color: #F2F2F7; font-weight: 600; font-size: 15px;")
            bottom_layout.addWidget(title_lbl)

        if self.data['desc']:
            desc_lbl = QtWidgets.QLabel(self.data['desc'])
            desc_lbl.setAlignment(QtCore.Qt.AlignCenter)
            # Softer gray text
            desc_lbl.setStyleSheet("color: #A1A1AA; font-weight: 400; font-size: 12px;")
            desc_lbl.setWordWrap(True)
            bottom_layout.addWidget(desc_lbl)

        bottom_layout.addStretch()

        self.add_btn = QtWidgets.QPushButton()
        self.add_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.add_btn.setFixedHeight(32)
        self.add_btn.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.update_btn_style()
        self.add_btn.clicked.connect(self.on_add_clicked)
        bottom_layout.addWidget(self.add_btn)

        card_layout.addWidget(self.bottom_frame, 2)
        layout.addWidget(card_root)

    def update_btn_style(self):
        if self._added:
            self.add_btn.setText("Added") # Removed the tick
            self.add_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(40, 100, 60, 0.4);
                    color: #4ade80;
                    border: 1px solid rgba(74, 222, 128, 0.3);
                    border-radius: 16px;
                    font-weight: 500;
                    font-size: 13px;
                }
            """)
        else:
            self.add_btn.setText("+ Add to home")
            self.add_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.08);
                    color: #F2F2F7;
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    border-radius: 16px;
                    font-weight: 500;
                    font-size: 13px;
                }
                QPushButton:hover { 
                    background-color: rgba(255, 255, 255, 0.15); 
                }
                QPushButton:pressed { 
                    background-color: rgba(255, 255, 255, 0.05); 
                }
            """)

    def on_add_clicked(self):
        if not self._added:
            self._added = True
            self.update_btn_style()
            self.added.emit(self.data["id"])

    def match_filter(self, category: str, query: str) -> bool:
        cat_match = (category == "All" or category == "For You" or self.data["category"] == category)
        q = query.lower().strip()
        text_match = (q in self.data["title"].lower() or q in self.data["desc"].lower() or q in self.data["category"].lower())
        return cat_match and text_match


class WidgetLibrarySim(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.cards = []
        self.current_category = "For You"
        self.next_row = 0
        self.next_col = 0
        self.init_ui()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        painter.fillRect(self.rect(), QtGui.QColor("#0a0a14"))
        
        w, h = self.width(), self.height()
        
        grad1 = QtGui.QRadialGradient(w * 0.2, h * 0.8, h * 0.6)
        grad1.setColorAt(0, QtGui.QColor(150, 50, 255, 80))
        grad1.setColorAt(1, QtGui.QColor(0, 0, 0, 0))
        painter.fillRect(self.rect(), grad1)
        
        grad2 = QtGui.QRadialGradient(w * 0.8, h * 0.2, h * 0.5)
        grad2.setColorAt(0, QtGui.QColor(50, 150, 255, 60))
        grad2.setColorAt(1, QtGui.QColor(0, 0, 0, 0))
        painter.fillRect(self.rect(), grad2)

    def init_ui(self):
        self.resize(1200, 800)
        self.setWindowTitle("Widget Library")
        self.setStyleSheet(COMMON_SCROLLBAR_QSS)
        
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(40)

        # === LEFT PANEL ===
        left_panel = QtWidgets.QVBoxLayout()
        left_panel.setSpacing(20)
        
        title = QtWidgets.QLabel("Widget Library")
        title.setStyleSheet("color: #F2F2F7; font-size: 26px; font-weight: 700;")
        left_panel.addWidget(title)

        self.search_input = SearchBar()
        self.search_input.setFixedHeight(40)
        self.search_input.textChanged.connect(self.apply_filters)
        left_panel.addWidget(self.search_input)

        # Categories list
        ribbon_scroll = QtWidgets.QScrollArea()
        ribbon_scroll.setWidgetResizable(True)
        ribbon_scroll.setFixedWidth(240)
        ribbon_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        ribbon_scroll.setStyleSheet("background: transparent; border: none;")
        
        ribbon_content = QtWidgets.QWidget()
        ribbon_content.setStyleSheet("background: transparent;")
        ribbon_layout = QtWidgets.QVBoxLayout(ribbon_content)
        ribbon_layout.setContentsMargins(0, 10, 20, 0)
        ribbon_layout.setSpacing(8)

        self.category_group = QtWidgets.QButtonGroup(self)
        for i, (label, val) in enumerate(CATEGORIES):
            btn = QtWidgets.QPushButton(label)
            btn.setCheckable(True)
            if i == 0:
                btn.setChecked(True)
            
            btn.setFixedHeight(36)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.05);
                    color: #D4D4D8;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 18px;
                    text-align: left;
                    padding-left: 16px;
                    font-size: 14px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.12);
                    color: #F2F2F7;
                }
                QPushButton:checked {
                    background-color: #F2F2F7;
                    color: #111111;
                    border: none;
                    font-weight: 600;
                }
            """)
            btn.setProperty("cat_val", val)
            self.category_group.addButton(btn, i)
            ribbon_layout.addWidget(btn)
        
        ribbon_layout.addStretch()
        ribbon_scroll.setWidget(ribbon_content)
        left_panel.addWidget(ribbon_scroll)
        self.category_group.buttonClicked.connect(self.on_category_changed)
        
        main_layout.addLayout(left_panel, 0) 

        # === RIGHT PANEL ===
        right_panel = QtWidgets.QVBoxLayout()
        right_panel.setSpacing(20)
        
        top_right_layout = QtWidgets.QHBoxLayout()
        top_right_layout.addStretch()
        
        arrange_btn = QtWidgets.QPushButton("☷ Arrange Layout")
        arrange_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        arrange_btn.setFixedHeight(36)
        arrange_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.12);
                color: #F2F2F7;
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 18px;
                padding: 0 20px;
                font-weight: 500;
                font-size: 13px;
            }
            QPushButton:hover { 
                background-color: rgba(255, 255, 255, 0.22);
            }
        """)
        top_right_layout.addWidget(arrange_btn)
        right_panel.addLayout(top_right_layout)

        # Widget Grid
        grid_scroll = QtWidgets.QScrollArea()
        grid_scroll.setWidgetResizable(True)
        grid_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        grid_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        grid_scroll.setStyleSheet("background: transparent; border: none;")
        
        grid_content = QtWidgets.QWidget()
        grid_content.setStyleSheet("background: transparent;")
        self.grid_layout = QtWidgets.QGridLayout()
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(20)

        self.grid_layout.setColumnStretch(0, 1)
        self.grid_layout.setColumnStretch(1, 1)
        self.grid_layout.setColumnStretch(2, 1)

        for data in WIDGETS_DATA:
            card = WidgetCard(data)
            card.added.connect(self.on_widget_added)
            self.cards.append(card)
            
        grid_layout_stretch = QtWidgets.QVBoxLayout(grid_content)
        grid_layout_stretch.addLayout(self.grid_layout)
        grid_layout_stretch.addStretch()

        grid_scroll.setWidget(grid_content)
        right_panel.addWidget(grid_scroll, 1)

        self.feed_log = QtWidgets.QTextEdit()
        self.feed_log.setReadOnly(True)
        self.feed_log.setFixedHeight(60)
        self.feed_log.setStyleSheet("""
            QTextEdit {
                background-color: rgba(0, 0, 0, 0.25);
                color: #4ADE80;
                font-family: monospace;
                font-size: 12px;
                font-weight: 500;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                padding: 8px;
            }
        """)
        self.feed_log.setPlaceholderText("State Management Feed (add a widget to see logs)")
        right_panel.addWidget(self.feed_log)

        main_layout.addLayout(right_panel, 1)

        self.apply_filters()

    def on_category_changed(self, button):
        self.current_category = button.property("cat_val")
        self.apply_filters()

    def apply_filters(self):
        query = self.search_input.text()
        visible_cards = []
        for card in self.cards:
            if card.match_filter(self.current_category, query):
                card.setVisible(True)
                visible_cards.append(card)
            else:
                card.setVisible(False)
        
        for i in reversed(range(self.grid_layout.count())):
            item = self.grid_layout.itemAt(i)
            if item.widget():
                self.grid_layout.removeWidget(item.widget())
        
        cols = 3
        for i, card in enumerate(visible_cards):
            r = i // cols
            c = i % cols
            self.grid_layout.addWidget(card, r, c)

    def on_widget_added(self, widget_id: str):
        payload = {
            "action": "add_widget",
            "id": widget_id,
            "target": {"row": self.next_row, "col": self.next_col, "rowSpan": 1, "colSpan": 1}
        }
        log_line = json.dumps(payload)
        self.feed_log.append(f"> {log_line}")
        
        self.next_col += 1
        if self.next_col > 2:
            self.next_col = 0
            self.next_row += 1


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    
    font = QtGui.QFont("Inter", 10)
    font.setStyleHint(QtGui.QFont.SansSerif)
    app.setFont(font)

    window = WidgetLibrarySim()
    window.show()
    sys.exit(app.exec_())
