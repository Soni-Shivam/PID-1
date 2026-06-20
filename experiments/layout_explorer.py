import sys
import os
import time

# Setup import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from core.qt_compat import QtCore, QtGui, QtWidgets

MODERN_FONT_STACK = "'Outfit', 'Nunito', 'Quicksand', 'Inter', 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"

class FocusTimerWidget(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("WidgetBase")
        
        layout = QtWidgets.QVBoxLayout(self)
        
        lbl_title = QtWidgets.QLabel("Focus Session")
        lbl_title.setStyleSheet("color: #A1A1AA; font-size: 13px; font-weight: 500;")
        layout.addWidget(lbl_title, alignment=QtCore.Qt.AlignHCenter)
        
        self.lbl_time = QtWidgets.QLabel("30:00")
        self.lbl_time.setStyleSheet("color: #F2F2F7; font-size: 48px; font-weight: 700;")
        layout.addWidget(self.lbl_time, alignment=QtCore.Qt.AlignCenter)
        
        self.btn_toggle = QtWidgets.QPushButton("▶ Start")
        self.btn_toggle.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.btn_toggle.setFixedHeight(36)
        self.btn_toggle.setStyleSheet("""
            QPushButton {
                background: #F2F2F7;
                color: #111111;
                border-radius: 18px;
                font-weight: 600;
                font-size: 14px;
            }
            QPushButton:hover { background: #FFFFFF; }
        """)
        layout.addWidget(self.btn_toggle)
        
        self.is_running = False
        self.seconds_left = 1800
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(1000) # strictly 1s interval
        self.timer.timeout.connect(self.tick)
        self.btn_toggle.clicked.connect(self.toggle)
        
    def toggle(self):
        self.is_running = not self.is_running
        if self.is_running:
            self.btn_toggle.setText("⏸ Pause")
            self.timer.start()
        else:
            self.btn_toggle.setText("▶ Start")
            self.timer.stop()
            
    def tick(self):
        if self.seconds_left > 0:
            self.seconds_left -= 1
            m, s = divmod(self.seconds_left, 60)
            self.lbl_time.setText(f"{m:02d}:{s:02d}")


class TopHeadlinesWidget(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("WidgetBase")
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(12)
        
        header_layout = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("Top Headlines")
        title.setStyleSheet("color: #F2F2F7; font-size: 15px; font-weight: 600;")
        view_all = QtWidgets.QLabel("<a href='#' style='color: #3b82f6; text-decoration: none;'>View all</a>")
        view_all.setStyleSheet("font-size: 12px;")
        view_all.setTextFormat(QtCore.Qt.RichText)
        view_all.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(view_all)
        layout.addLayout(header_layout)
        
        headlines = [
            "ISRO launches new advanced satellite",
            "Sensex crosses 85,000 mark in early trade",
            "Exclusive: CMF Phone 3 Pro Spec leaks online",
            "IPL 2026: Mumbai Indians beat CSK by 10 runs"
        ]
        
        for text in headlines:
            lbl = QtWidgets.QLabel(text)
            lbl.setStyleSheet("color: #D4D4D8; font-size: 13px;")
            # No word wrap to save calculations; elide right
            lbl.setWordWrap(False)
            metrics = QtGui.QFontMetrics(lbl.font())
            # We'll rely on layout stretching or fixed size if needed, but normally
            # QLabel doesn't automatically elide without custom paintEvent or setting text carefully.
            # For efficiency in a static shell, we just let it clip or use simple CSS.
            layout.addWidget(lbl)
            
        layout.addStretch()


class StartExploringWidget(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("WidgetBase")
        
        layout = QtWidgets.QVBoxLayout(self)
        
        title = QtWidgets.QLabel("Start Exploring")
        title.setStyleSheet("color: #F2F2F7; font-size: 15px; font-weight: 600;")
        layout.addWidget(title)
        
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(8)
        
        actions = [
            ("📝", "Take Notes", "#3b82f6"),
            ("📚", "Study", "#10b981"),
            ("🎮", "Play Games", "#8b5cf6"),
            ("🎨", "Draw", "#f59e0b")
        ]
        
        for i, (icon, text, color) in enumerate(actions):
            btn = QtWidgets.QToolButton()
            btn.setText(f"{icon} {text}")
            btn.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
            btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
            # Flat colors, strictly no C++ animations
            btn.setStyleSheet(f"""
                QToolButton {{
                    background: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 12px;
                    color: {color};
                    font-size: 13px;
                    font-weight: 500;
                }}
                QToolButton:hover {{
                    background: rgba(255, 255, 255, 0.1);
                }}
                QToolButton:pressed {{
                    background: rgba(255, 255, 255, 0.02);
                }}
            """)
            r, c = divmod(i, 2)
            grid.addWidget(btn, r, c)
            
        layout.addLayout(grid, 1)


class PerformanceMonitorWidget(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("WidgetBase")
        
        layout = QtWidgets.QVBoxLayout(self)
        
        title = QtWidgets.QLabel("System Health")
        title.setStyleSheet("color: #F2F2F7; font-size: 15px; font-weight: 600;")
        layout.addWidget(title)
        
        self.cpu_lbl = QtWidgets.QLabel("CPU: 0%")
        self.cpu_lbl.setStyleSheet("color: #D4D4D8; font-size: 12px;")
        self.cpu_bar = QtWidgets.QProgressBar()
        self.cpu_bar.setTextVisible(False)
        self.cpu_bar.setFixedHeight(6)
        
        self.ram_lbl = QtWidgets.QLabel("RAM: 0%")
        self.ram_lbl.setStyleSheet("color: #D4D4D8; font-size: 12px;")
        self.ram_bar = QtWidgets.QProgressBar()
        self.ram_bar.setTextVisible(False)
        self.ram_bar.setFixedHeight(6)
        
        layout.addWidget(self.cpu_lbl)
        layout.addWidget(self.cpu_bar)
        layout.addSpacing(8)
        layout.addWidget(self.ram_lbl)
        layout.addWidget(self.ram_bar)
        layout.addStretch()
        
        # Read from procfs every 2 seconds
        self.last_idle = 0
        self.last_total = 0
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self.update_stats)
        self.timer.start()
        
        self.update_stats()
        
    def update_stats(self):
        # CPU
        try:
            with open('/proc/stat', 'r') as f:
                lines = f.readlines()
                cpu_line = lines[0].split()
                if cpu_line[0] == 'cpu':
                    idle = float(cpu_line[4]) + float(cpu_line[5])
                    total = sum(float(x) for x in cpu_line[1:8])
                    
                    idle_delta = idle - self.last_idle
                    total_delta = total - self.last_total
                    
                    if total_delta > 0:
                        usage = 100.0 * (1.0 - idle_delta / total_delta)
                        self.cpu_lbl.setText(f"CPU: {int(usage)}%")
                        self.cpu_bar.setValue(int(usage))
                        
                    self.last_idle = idle
                    self.last_total = total
        except Exception:
            pass # Ignore if running on non-Linux
            
        # RAM
        try:
            with open('/proc/meminfo', 'r') as f:
                mem_total = 0
                mem_avail = 0
                for line in f:
                    if line.startswith("MemTotal:"):
                        mem_total = int(line.split()[1])
                    elif line.startswith("MemAvailable:"):
                        mem_avail = int(line.split()[1])
                        break
                if mem_total > 0:
                    used = mem_total - mem_avail
                    usage = (used / mem_total) * 100.0
                    self.ram_lbl.setText(f"RAM: {int(usage)}%")
                    self.ram_bar.setValue(int(usage))
        except Exception:
            pass


class LayoutExplorer(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Layout Parameter Explorer")
        self.resize(1100, 700)
        self.setStyleSheet(f"* {{ font-family: {MODERN_FONT_STACK}; }}")
        
        # Default metrics
        self.g_padding = 20
        self.g_radius = 20
        self.g_spacing = 20
        
        self.init_ui()
        self.apply_metrics()
        
    def init_ui(self):
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Left Panel: Explorer Controls
        control_panel = QtWidgets.QFrame()
        control_panel.setFixedWidth(300)
        control_panel.setStyleSheet("background: #111111; border-right: 1px solid rgba(255,255,255,0.1);")
        cp_layout = QtWidgets.QVBoxLayout(control_panel)
        cp_layout.setContentsMargins(24, 32, 24, 32)
        cp_layout.setSpacing(24)
        
        lbl_title = QtWidgets.QLabel("Parameter Explorer")
        lbl_title.setStyleSheet("color: white; font-size: 20px; font-weight: 700;")
        cp_layout.addWidget(lbl_title)
        
        # Padding Slider
        self.lbl_pad = QtWidgets.QLabel("Padding: 20px")
        self.lbl_pad.setStyleSheet("color: #D4D4D8; font-size: 13px;")
        self.slider_pad = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_pad.setRange(0, 48)
        self.slider_pad.setValue(self.g_padding)
        self.slider_pad.valueChanged.connect(self.on_metrics_changed)
        cp_layout.addWidget(self.lbl_pad)
        cp_layout.addWidget(self.slider_pad)
        
        # Radius Slider
        self.lbl_rad = QtWidgets.QLabel("Corner Radius: 20px")
        self.lbl_rad.setStyleSheet("color: #D4D4D8; font-size: 13px;")
        self.slider_rad = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_rad.setRange(0, 48)
        self.slider_rad.setValue(self.g_radius)
        self.slider_rad.valueChanged.connect(self.on_metrics_changed)
        cp_layout.addWidget(self.lbl_rad)
        cp_layout.addWidget(self.slider_rad)
        
        # Spacing Slider
        self.lbl_space = QtWidgets.QLabel("Grid Spacing: 20px")
        self.lbl_space.setStyleSheet("color: #D4D4D8; font-size: 13px;")
        self.slider_space = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_space.setRange(0, 64)
        self.slider_space.setValue(self.g_spacing)
        self.slider_space.valueChanged.connect(self.on_metrics_changed)
        cp_layout.addWidget(self.lbl_space)
        cp_layout.addWidget(self.slider_space)
        
        cp_layout.addStretch()
        
        # Right Panel: Canvas
        self.canvas_panel = QtWidgets.QFrame()
        self.canvas_panel.setStyleSheet("background: #0a0a14;")
        self.canvas_layout = QtWidgets.QGridLayout(self.canvas_panel)
        
        self.w_timer = FocusTimerWidget()
        self.w_news = TopHeadlinesWidget()
        self.w_explore = StartExploringWidget()
        self.w_perf = PerformanceMonitorWidget()
        
        self.canvas_layout.addWidget(self.w_timer, 0, 0)
        self.canvas_layout.addWidget(self.w_news, 0, 1)
        self.canvas_layout.addWidget(self.w_explore, 1, 0)
        self.canvas_layout.addWidget(self.w_perf, 1, 1)
        
        self.canvas_layout.setColumnStretch(0, 1)
        self.canvas_layout.setColumnStretch(1, 1)
        self.canvas_layout.setRowStretch(0, 1)
        self.canvas_layout.setRowStretch(1, 1)
        
        main_layout.addWidget(control_panel)
        main_layout.addWidget(self.canvas_panel, 1)
        
    def on_metrics_changed(self):
        self.g_padding = self.slider_pad.value()
        self.g_radius = self.slider_rad.value()
        self.g_spacing = self.slider_space.value()
        
        self.lbl_pad.setText(f"Padding: {self.g_padding}px")
        self.lbl_rad.setText(f"Corner Radius: {self.g_radius}px")
        self.lbl_space.setText(f"Grid Spacing: {self.g_spacing}px")
        
        self.apply_metrics()
        
    def apply_metrics(self):
        # Apply layout spacing and margins dynamically
        self.canvas_layout.setSpacing(self.g_spacing)
        self.canvas_layout.setContentsMargins(self.g_padding * 2, self.g_padding * 2, self.g_padding * 2, self.g_padding * 2)
        
        # Apply dynamic QSS to all WidgetBase frames
        global_qss = f"""
            QFrame#WidgetBase {{
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: {self.g_radius}px;
            }}
            QProgressBar {{
                background: rgba(255, 255, 255, 0.1);
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background: #3b82f6;
                border-radius: 3px;
            }}
        """
        self.w_timer.setStyleSheet(global_qss)
        self.w_news.setStyleSheet(global_qss)
        self.w_explore.setStyleSheet(global_qss)
        self.w_perf.setStyleSheet(global_qss)
        
        # Apply internal padding dynamically by updating layout margins
        for w in [self.w_timer, self.w_news, self.w_explore, self.w_perf]:
            w.layout().setContentsMargins(self.g_padding, self.g_padding, self.g_padding, self.g_padding)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    
    font = QtGui.QFont("Inter", 10)
    font.setStyleHint(QtGui.QFont.SansSerif)
    app.setFont(font)

    window = LayoutExplorer()
    window.show()
    sys.exit(app.exec_())
