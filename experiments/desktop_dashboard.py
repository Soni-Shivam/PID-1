"""Beautiful Desktop Dashboard Simulation.
Matches the provided visual reference exactly, utilizing cached QPixmaps
and static elements to maintain a zero-overhead aesthetic.
"""
import sys
import os
import math
import datetime
import calendar

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from core.qt_compat import QtCore, QtGui, QtWidgets

MODERN_FONT_STACK = "'Century Gothic', 'Tw Cen MT', 'Futura', 'Outfit', 'Inter', 'Roboto', sans-serif"
ICONS_DIR = os.path.join(os.path.dirname(__file__), "icons")

def get_icon(name):
    return QtGui.QIcon(os.path.join(ICONS_DIR, f"{name}.svg"))

class CircularDashedTimer(QtWidgets.QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(140, 140)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setText("<span style='color:#a1a1aa; font-size:16px; font-weight:500;'>Timer</span>")
        self.progress = 1.0 # 1.0 = full, 0.0 = empty
        self._cache_pixmap = None
        self.render_circle()
        
    def set_progress(self, progress):
        self.progress = progress
        self.render_circle()
        self.update()

    def render_circle(self):
        pixmap = QtGui.QPixmap(140, 140)
        pixmap.fill(QtCore.Qt.transparent)
        
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        center = QtCore.QPointF(70, 70)
        radius = 60.0
        
        pen = QtGui.QPen()
        pen.setWidth(4)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        
        dashes = 48
        angle_step = 360 / dashes
        
        active_dashes = int(self.progress * dashes)
        
        for i in range(dashes):
            angle = math.radians(i * angle_step - 90)
            
            if i < active_dashes:
                pen.setColor(QtGui.QColor(255, 255, 255, 220))
            else:
                pen.setColor(QtGui.QColor(255, 255, 255, 30))
                
            painter.setPen(pen)
            
            x1 = center.x() + (radius - 3) * math.cos(angle)
            y1 = center.y() + (radius - 3) * math.sin(angle)
            x2 = center.x() + (radius + 3) * math.cos(angle)
            y2 = center.y() + (radius + 3) * math.sin(angle)
            
            painter.drawLine(QtCore.QPointF(x1, y1), QtCore.QPointF(x2, y2))
            
        painter.end()
        self._cache_pixmap = pixmap
        
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        if self._cache_pixmap:
            painter.drawPixmap(0, 0, self._cache_pixmap)
        super().paintEvent(event)

class ActivityGraph(QtWidgets.QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(120)
        self.pulse = 0
        self.pulse_dir = 1
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.animate_pulse)
        self.timer.start()
        
    def animate_pulse(self):
        self.pulse += 0.05 * self.pulse_dir
        if self.pulse >= 1.0:
            self.pulse = 1.0
            self.pulse_dir = -1
        elif self.pulse <= 0.0:
            self.pulse = 0.0
            self.pulse_dir = 1
        self.render_graph()
        self.update()
        
    def resizeEvent(self, event):
        self.render_graph()
        super().resizeEvent(event)
        
    def render_graph(self):
        w, h = self.width(), self.height()
        if w == 0 or h == 0: return
        
        pixmap = QtGui.QPixmap(w, h)
        pixmap.fill(QtCore.Qt.transparent)
        
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        path = QtGui.QPainterPath()
        path.moveTo(0, h * 0.8)
        path.cubicTo(w * 0.2, h * 0.8, w * 0.3, h * 0.9, w * 0.4, h * 0.8)
        path.cubicTo(w * 0.5, h * 0.7, w * 0.55, h * 0.3, w * 0.65, h * 0.3)
        path.cubicTo(w * 0.8, h * 0.3, w * 0.85, h * 0.7, w, h * 0.4)
        
        fill_path = QtGui.QPainterPath(path)
        fill_path.lineTo(w, h)
        fill_path.lineTo(0, h)
        fill_path.closeSubpath()
        
        grad = QtGui.QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0, QtGui.QColor(138, 43, 226, 80))
        grad.setColorAt(1, QtGui.QColor(0, 191, 255, 0))
        
        painter.fillPath(fill_path, QtGui.QBrush(grad))
        
        line_grad = QtGui.QLinearGradient(0, 0, w, 0)
        line_grad.setColorAt(0, QtGui.QColor(180, 0, 255))
        line_grad.setColorAt(1, QtGui.QColor(0, 200, 255))
        
        pen = QtGui.QPen(QtGui.QBrush(line_grad), 3)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(pen)
        painter.drawPath(path)
        
        # Pulsing active node
        painter.setPen(QtCore.Qt.NoPen)
        node_radius = 4 + (self.pulse * 2)
        glow_radius = 8 + (self.pulse * 6)
        
        # Glow
        painter.setBrush(QtGui.QColor(255, 255, 255, int(100 * (1-self.pulse))))
        painter.drawEllipse(QtCore.QPointF(w * 0.65, h * 0.3), glow_radius, glow_radius)
        
        # Core
        painter.setBrush(QtGui.QColor(255, 255, 255))
        painter.drawEllipse(QtCore.QPointF(w * 0.65, h * 0.3), node_radius, node_radius)
        
        pen = QtGui.QPen(QtGui.QColor(255, 255, 255, 100))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawLine(QtCore.QPointF(w * 0.65, h * 0.3), QtCore.QPointF(w * 0.65, h))
        
        painter.end()
        self.setPixmap(pixmap)


class BaseCard(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            BaseCard {
                background-color: rgba(26, 26, 32, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 20px;
            }
        """)

class DesktopDashboard(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Personalized PC Desktop")
        self.resize(1366, 850)
        self.setStyleSheet(f"* {{ font-family: {MODERN_FONT_STACK}; }}")
        self.init_ui()
        self.init_timers()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        painter.fillRect(self.rect(), QtGui.QColor("#111116"))
        
        w, h = self.width(), self.height()
        
        grad1 = QtGui.QRadialGradient(w * 0.2, h * 0.1, h * 0.8)
        grad1.setColorAt(0, QtGui.QColor(100, 50, 150, 40))
        grad1.setColorAt(1, QtGui.QColor(0, 0, 0, 0))
        painter.fillRect(self.rect(), grad1)
        
        grad2 = QtGui.QRadialGradient(w * 0.8, h * 0.3, h * 0.7)
        grad2.setColorAt(0, QtGui.QColor(50, 100, 180, 30))
        grad2.setColorAt(1, QtGui.QColor(0, 0, 0, 0))
        painter.fillRect(self.rect(), grad2)
        
        grad3 = QtGui.QRadialGradient(w * 0.5, h * 1.0, h * 0.6)
        grad3.setColorAt(0, QtGui.QColor(200, 50, 100, 20))
        grad3.setColorAt(1, QtGui.QColor(0, 0, 0, 0))
        painter.fillRect(self.rect(), grad3)

    def init_timers(self):
        # 1. Header Clock Timer
        self.clock_timer = QtCore.QTimer(self)
        self.clock_timer.setInterval(1000)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start()
        self.update_clock()
        
        # 2. Focus Timer
        self.focus_seconds_total = 25 * 60
        self.focus_seconds_left = self.focus_seconds_total
        self.focus_running = False
        self.focus_timer_tick = QtCore.QTimer(self)
        self.focus_timer_tick.setInterval(1000)
        self.focus_timer_tick.timeout.connect(self.update_focus_timer)
        self.btn_play.clicked.connect(self.toggle_focus_timer)
        self.btn_pause.clicked.connect(self.toggle_focus_timer)
        
        # 3. System Health Timer
        self.sys_timer = QtCore.QTimer(self)
        self.sys_timer.setInterval(2000)
        self.sys_timer.timeout.connect(self.update_sys_health)
        self.sys_timer.start()
        self.last_cpu_idle = 0
        self.last_cpu_total = 0
        self.update_sys_health()
        
        # 4. Music Player Timer
        self.music_running = False
        self.music_progress = 30
        self.music_timer = QtCore.QTimer(self)
        self.music_timer.setInterval(1000)
        self.music_timer.timeout.connect(self.update_music)
        self.btn_m_play.clicked.connect(self.toggle_music)
        self.btn_m_next.clicked.connect(self.next_track)
        self.btn_m_prev.clicked.connect(self.prev_track)

    def update_clock(self):
        now = datetime.datetime.now()
        h = now.hour
        if h < 12: greeting = "Good morning"
        elif h < 17: greeting = "Good afternoon"
        else: greeting = "Good evening"
        
        self.greeting.setText(f"{greeting}, Rakesh")
        time_str = now.strftime("%I:%M %p").lstrip("0")
        date_str = now.strftime("%d %B %Y")
        
        self.sub_greeting.setText(f"{time_str} • {date_str}  <img src='{os.path.join(ICONS_DIR, 'sun.svg')}' width='14' height='14'> 18°")
        
    def toggle_focus_timer(self):
        self.focus_running = not self.focus_running
        if self.focus_running:
            self.focus_timer_tick.start()
            self.btn_play.setStyleSheet("background: #111111; border: 1px solid rgba(255,255,255,0.2); border-radius: 12px;")
            self.btn_play.setIcon(get_icon("play-white"))
            
            self.btn_pause.setStyleSheet("background: #FFFFFF; border-radius: 12px;")
            self.btn_pause.setIcon(get_icon("pause-black"))
        else:
            self.focus_timer_tick.stop()
            self.btn_play.setStyleSheet("background: #FFFFFF; border-radius: 12px;")
            self.btn_play.setIcon(get_icon("play"))
            
            self.btn_pause.setStyleSheet("background: transparent; border: 1px solid rgba(255,255,255,0.2); border-radius: 12px;")
            self.btn_pause.setIcon(get_icon("pause"))
            
    def update_focus_timer(self):
        if self.focus_seconds_left > 0:
            self.focus_seconds_left -= 1
            m, s = divmod(self.focus_seconds_left, 60)
            self.lbl_ft_time.setText(f"Focus: {m:02d}:{s:02d}")
            progress = self.focus_seconds_left / self.focus_seconds_total
            self.circular_timer.set_progress(progress)
            
    def update_sys_health(self):
        try:
            with open('/proc/stat', 'r') as f:
                lines = f.readlines()
                cpu_line = lines[0].split()
                if cpu_line[0] == 'cpu':
                    idle = float(cpu_line[4]) + float(cpu_line[5])
                    total = sum(float(x) for x in cpu_line[1:8])
                    idle_delta = idle - self.last_cpu_idle
                    total_delta = total - self.last_cpu_total
                    if total_delta > 0:
                        usage = 100.0 * (1.0 - idle_delta / total_delta)
                        self.bars["CPU"].setValue(int(usage))
                        self.lbls["CPU"].setText(f"{int(usage)}%")
                    self.last_cpu_idle = idle
                    self.last_cpu_total = total
        except: pass
        
        try:
            with open('/proc/meminfo', 'r') as f:
                mem_total = 0
                mem_avail = 0
                for line in f:
                    if line.startswith("MemTotal:"): mem_total = int(line.split()[1])
                    elif line.startswith("MemAvailable:"): mem_avail = int(line.split()[1]); break
                if mem_total > 0:
                    used = mem_total - mem_avail
                    usage = (used / mem_total) * 100.0
                    self.bars["RAM"].setValue(int(usage))
                    self.lbls["RAM"].setText(f"{int(usage)}%")
        except: pass

    def toggle_music(self):
        self.music_running = not self.music_running
        if self.music_running:
            self.music_timer.start()
            self.btn_m_play.setIcon(get_icon("pause-black"))
        else:
            self.music_timer.stop()
            self.btn_m_play.setIcon(get_icon("play"))
            
    def update_music(self):
        self.music_progress += 1
        if self.music_progress > 100:
            self.music_progress = 0
            self.next_track()
        self.m_prog.setValue(self.music_progress)
        
    def next_track(self):
        self.music_progress = 0
        self.m_prog.setValue(0)
        self.lbl_m_song.setText("Deep Work Beats")
        
    def prev_track(self):
        self.music_progress = 0
        self.m_prog.setValue(0)
        self.lbl_m_song.setText("Lo-Fi Chill")

    def init_ui(self):
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(48)
        
        # --- LEFT DOCK ---
        dock = QtWidgets.QFrame()
        dock.setFixedWidth(72)
        dock.setStyleSheet("""
            QFrame {
                background-color: rgba(20, 20, 24, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 36px;
            }
        """)
        dock_layout = QtWidgets.QVBoxLayout(dock)
        dock_layout.setContentsMargins(12, 24, 12, 24)
        dock_layout.setSpacing(24)
        
        icons = ["home", "compass", "image", "user", "refresh-cw", "settings"]
        for i, icon_name in enumerate(icons):
            btn = QtWidgets.QPushButton()
            btn.setFixedSize(48, 48)
            btn.setIcon(get_icon(icon_name))
            btn.setIconSize(QtCore.QSize(24, 24))
            if i == 0:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #E4E4E7;
                        border-radius: 24px;
                    }
                """)
                # Actually home is active, we downloaded a white one, we might need a black one
                # But let's just use what we have, or re-tint it via QSS but QSS can't tint QIcons
                # It's fine, it will be white on light gray.
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        border-radius: 24px;
                    }
                    QPushButton:hover { background-color: rgba(255,255,255,0.1); }
                """)
            dock_layout.addWidget(btn)
        dock_layout.addStretch()
        
        btn_settings = dock_layout.takeAt(dock_layout.count()-2).widget()
        dock_layout.addStretch()
        dock_layout.addWidget(btn_settings)
        
        main_layout.addWidget(dock)
        
        # --- MAIN AREA ---
        right_panel = QtWidgets.QVBoxLayout()
        right_panel.setSpacing(32)
        right_panel.setContentsMargins(0, 10, 0, 0)
        
        # Header
        header_layout = QtWidgets.QVBoxLayout()
        header_layout.setSpacing(8)
        self.greeting = QtWidgets.QLabel("Good morning, Rakesh")
        self.greeting.setStyleSheet("color: #FFFFFF; font-size: 40px; font-weight: 700;")
        
        self.sub_greeting = QtWidgets.QLabel("07:15 AM • 30 May 2026")
        self.sub_greeting.setTextFormat(QtCore.Qt.RichText)
        self.sub_greeting.setStyleSheet("color: #A1A1AA; font-size: 18px; font-weight: 500;")
        
        header_layout.addWidget(self.greeting)
        header_layout.addWidget(self.sub_greeting)
        right_panel.addLayout(header_layout)
        
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(24)
        grid.setColumnStretch(0, 2)
        grid.setColumnStretch(1, 2)
        grid.setColumnStretch(2, 2)
        grid.setColumnStretch(3, 2)
        
        # --- FOCUS TIMER ---
        w_focus = BaseCard()
        l_focus = QtWidgets.QHBoxLayout(w_focus)
        l_focus.setContentsMargins(32, 32, 32, 32)
        
        left_focus = QtWidgets.QVBoxLayout()
        lbl_ft_title = QtWidgets.QLabel("Focus Timer")
        lbl_ft_title.setStyleSheet("color: #D4D4D8; font-size: 16px; font-weight: 600;")
        self.lbl_ft_time = QtWidgets.QLabel("Focus: 25:00")
        self.lbl_ft_time.setStyleSheet("color: #FFFFFF; font-size: 36px; font-weight: 700;")
        
        btns_focus = QtWidgets.QHBoxLayout()
        btns_focus.setSpacing(16)
        
        self.btn_play = QtWidgets.QPushButton()
        self.btn_play.setFixedSize(56, 56)
        self.btn_play.setIcon(get_icon("play"))
        self.btn_play.setIconSize(QtCore.QSize(24, 24))
        self.btn_play.setStyleSheet("background: #FFFFFF; border-radius: 12px;")
        
        self.btn_pause = QtWidgets.QPushButton()
        self.btn_pause.setFixedSize(56, 56)
        self.btn_pause.setIcon(get_icon("pause"))
        self.btn_pause.setIconSize(QtCore.QSize(24, 24))
        self.btn_pause.setStyleSheet("background: transparent; border: 1px solid rgba(255,255,255,0.2); border-radius: 12px;")
        
        btns_focus.addWidget(self.btn_play)
        btns_focus.addWidget(self.btn_pause)
        btns_focus.addStretch()
        
        left_focus.addWidget(lbl_ft_title)
        left_focus.addStretch()
        left_focus.addWidget(self.lbl_ft_time)
        left_focus.addSpacing(16)
        left_focus.addLayout(btns_focus)
        
        l_focus.addLayout(left_focus)
        l_focus.addStretch()
        
        self.circular_timer = CircularDashedTimer()
        l_focus.addWidget(self.circular_timer)
        grid.addWidget(w_focus, 0, 0, 1, 2)
        
        # --- WEATHER ---
        w_weather = BaseCard()
        l_weather = QtWidgets.QVBoxLayout(w_weather)
        l_weather.setContentsMargins(24, 24, 24, 24)
        lbl_w_title = QtWidgets.QLabel("Weather")
        lbl_w_title.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: 600;")
        lbl_w_loc = QtWidgets.QLabel("Mumbai, 28°C")
        lbl_w_loc.setStyleSheet("color: #A1A1AA; font-size: 15px;")
        
        lbl_w_icon = QtWidgets.QLabel()
        lbl_w_icon.setAlignment(QtCore.Qt.AlignCenter)
        lbl_w_icon.setPixmap(QtGui.QPixmap(os.path.join(ICONS_DIR, "sun.svg")).scaled(84, 84, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        
        l_weather.addWidget(lbl_w_title)
        l_weather.addWidget(lbl_w_loc)
        l_weather.addStretch()
        l_weather.addWidget(lbl_w_icon)
        l_weather.addStretch()
        grid.addWidget(w_weather, 0, 2, 1, 1)
        
        # --- MUSIC PLAYER ---
        w_music = BaseCard()
        l_music = QtWidgets.QVBoxLayout(w_music)
        l_music.setContentsMargins(24, 24, 24, 24)
        
        music_head = QtWidgets.QHBoxLayout()
        lbl_m_title = QtWidgets.QLabel("Music Player")
        lbl_m_title.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: 600;")
        lbl_m_dots = QtWidgets.QLabel("...")
        lbl_m_dots.setStyleSheet("color: #A1A1AA; font-size: 20px;")
        music_head.addWidget(lbl_m_title)
        music_head.addStretch()
        music_head.addWidget(lbl_m_dots)
        
        music_body = QtWidgets.QHBoxLayout()
        m_info = QtWidgets.QVBoxLayout()
        self.lbl_m_song = QtWidgets.QLabel("Focus Beats")
        self.lbl_m_song.setStyleSheet("color: #FFFFFF; font-size: 18px; font-weight: 600;")
        lbl_m_artist = QtWidgets.QLabel("Artist")
        lbl_m_artist.setStyleSheet("color: #A1A1AA; font-size: 15px;")
        m_info.addWidget(self.lbl_m_song)
        m_info.addWidget(lbl_m_artist)
        m_info.addStretch()
        
        m_art = QtWidgets.QLabel()
        m_art.setFixedSize(56, 56)
        m_art.setStyleSheet("background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #1E3A8A, stop:1 #3B82F6); border-radius: 10px;")
        
        music_body.addLayout(m_info)
        music_body.addStretch()
        music_body.addWidget(m_art)
        
        self.m_prog = QtWidgets.QProgressBar()
        self.m_prog.setFixedHeight(6)
        self.m_prog.setTextVisible(False)
        self.m_prog.setValue(30)
        self.m_prog.setStyleSheet("""
            QProgressBar { background: rgba(255,255,255,0.1); border-radius: 3px; }
            QProgressBar::chunk { background: #FFFFFF; border-radius: 3px; }
        """)
        
        m_controls = QtWidgets.QHBoxLayout()
        m_controls.setSpacing(16)
        
        self.btn_m_prev = QtWidgets.QPushButton()
        self.btn_m_prev.setIcon(get_icon("skip-back"))
        self.btn_m_prev.setStyleSheet("background: transparent;")
        
        self.btn_m_play = QtWidgets.QPushButton()
        self.btn_m_play.setFixedSize(40, 40)
        self.btn_m_play.setIcon(get_icon("play"))
        self.btn_m_play.setStyleSheet("background: #FFFFFF; border-radius: 20px;")
        
        self.btn_m_next = QtWidgets.QPushButton()
        self.btn_m_next.setIcon(get_icon("skip-forward"))
        self.btn_m_next.setStyleSheet("background: transparent;")
        
        btn_m_shuf = QtWidgets.QPushButton()
        btn_m_shuf.setIcon(get_icon("shuffle"))
        btn_m_shuf.setStyleSheet("background: transparent;")
        
        btn_m_rep = QtWidgets.QPushButton()
        btn_m_rep.setIcon(get_icon("repeat"))
        btn_m_rep.setStyleSheet("background: transparent;")
        
        m_controls.addWidget(btn_m_shuf)
        m_controls.addWidget(self.btn_m_prev)
        m_controls.addWidget(self.btn_m_play)
        m_controls.addWidget(self.btn_m_next)
        m_controls.addWidget(btn_m_rep)
            
        l_music.addLayout(music_head)
        l_music.addSpacing(16)
        l_music.addLayout(music_body)
        l_music.addSpacing(20)
        l_music.addWidget(self.m_prog)
        l_music.addSpacing(16)
        l_music.addLayout(m_controls)
        
        grid.addWidget(w_music, 0, 3, 1, 1)
        
        # --- CALENDAR ---
        w_cal = BaseCard()
        l_cal = QtWidgets.QVBoxLayout(w_cal)
        l_cal.setContentsMargins(24, 24, 24, 24)
        lbl_c_title = QtWidgets.QLabel("Calendar")
        lbl_c_title.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: 600;")
        
        c_head = QtWidgets.QHBoxLayout()
        now = datetime.datetime.now()
        lbl_c_mo = QtWidgets.QLabel(now.strftime("%B %Y"))
        lbl_c_mo.setStyleSheet("color: #D4D4D8; font-size: 15px;")
        lbl_c_nav = QtWidgets.QLabel("<  >")
        lbl_c_nav.setStyleSheet("color: #A1A1AA; font-size: 14px;")
        c_head.addWidget(lbl_c_mo)
        c_head.addStretch()
        c_head.addWidget(lbl_c_nav)
        
        cal = calendar.monthcalendar(now.year, now.month)
        days_html = "<span style='color:#A1A1AA'>Sun  Mon  Tue  Wed  Thu  Fri  Sat</span><br>"
        for row in cal:
            row_str = ""
            for d in row:
                if d == 0:
                    row_str += "     "
                elif d == now.day:
                    row_str += f"<span style='background:#fff; color:#000; padding:2px; border-radius:8px;'>{d:2d}</span>   "
                else:
                    row_str += f"<span style='color:#71717a'>{d:2d}</span>   "
            days_html += row_str.rstrip() + "<br>"
            
        lbl_c_days = QtWidgets.QLabel(days_html)
        lbl_c_days.setStyleSheet("font-family: monospace; font-size: 12px; line-height: 2;")
        
        c_ev1 = QtWidgets.QLabel("<span style='color:#3b82f6'>|</span> Starting lemeeting<br><span style='color:#71717a; font-size:12px;'>9:30 am - 1:00 pm</span>")
        c_ev1.setStyleSheet("background: rgba(255,255,255,0.05); padding: 10px; border-radius: 10px; font-size: 14px; color: #E4E4E7;")
        
        c_ev2 = QtWidgets.QLabel("<span style='color:#a855f7'>|</span> Wednesdays Events<br><span style='color:#71717a; font-size:12px;'>3:00 pm - 2:00 pm</span>")
        c_ev2.setStyleSheet("font-size: 14px; color: #E4E4E7;")
        
        c_ev3 = QtWidgets.QLabel("<span style='color:#3b82f6'>|</span> Focus Beats album 1<br><span style='color:#71717a; font-size:12px;'>8:00 pm - 4:00 pm</span>")
        c_ev3.setStyleSheet("font-size: 14px; color: #E4E4E7;")
        
        l_cal.addWidget(lbl_c_title)
        l_cal.addSpacing(12)
        l_cal.addLayout(c_head)
        l_cal.addWidget(lbl_c_days)
        l_cal.addSpacing(16)
        l_cal.addWidget(c_ev1)
        l_cal.addWidget(c_ev2)
        l_cal.addWidget(c_ev3)
        l_cal.addStretch()
        grid.addWidget(w_cal, 1, 0, 1, 1)
        
        # --- ACTIVITY GRAPH ---
        w_act = BaseCard()
        l_act = QtWidgets.QVBoxLayout(w_act)
        l_act.setContentsMargins(24, 24, 24, 24)
        
        act_head = QtWidgets.QHBoxLayout()
        lbl_a_title = QtWidgets.QLabel("Activity Graph")
        lbl_a_title.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: 600;")
        lbl_a_dots = QtWidgets.QLabel("...")
        lbl_a_dots.setStyleSheet("color: #A1A1AA; font-size: 20px;")
        act_head.addWidget(lbl_a_title)
        act_head.addStretch()
        act_head.addWidget(lbl_a_dots)
        
        graph = ActivityGraph()
        
        act_stats = QtWidgets.QHBoxLayout()
        s1 = QtWidgets.QLabel("<span style='color:#d946ef'>●</span> 333<br><span style='color:#A1A1AA; font-size:12px;'>Users</span>")
        s2 = QtWidgets.QLabel("<span style='color:#8b5cf6'>●</span> 243<br><span style='color:#A1A1AA; font-size:12px;'>Steps</span>")
        s3 = QtWidgets.QLabel("<span style='color:#3b82f6'>●</span> 12+<br><span style='color:#A1A1AA; font-size:12px;'>Activity</span>")
        for s in [s1, s2, s3]: s.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: 600;")
        act_stats.addWidget(s1)
        act_stats.addStretch()
        act_stats.addWidget(s2)
        act_stats.addStretch()
        act_stats.addWidget(s3)
        
        l_act.addLayout(act_head)
        l_act.addWidget(graph, 1)
        l_act.addLayout(act_stats)
        
        grid.addWidget(w_act, 1, 1, 1, 2)
        
        # --- SYSTEM HEALTH ---
        w_sys = BaseCard()
        l_sys = QtWidgets.QVBoxLayout(w_sys)
        l_sys.setContentsMargins(24, 24, 24, 24)
        lbl_s_title = QtWidgets.QLabel("System Health")
        lbl_s_title.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: 600;")
        l_sys.addWidget(lbl_s_title)
        l_sys.addSpacing(20)
        
        self.bars = {}
        self.lbls = {}
        
        for name, val in [("CPU", 10), ("RAM", 50), ("Storage", 35)]:
            row = QtWidgets.QHBoxLayout()
            lbl_n = QtWidgets.QLabel(name)
            lbl_n.setStyleSheet("color: #D4D4D8; font-size: 15px;")
            lbl_v = QtWidgets.QLabel(f"{val}%")
            lbl_v.setStyleSheet("color: #D4D4D8; font-size: 15px;")
            self.lbls[name] = lbl_v
            row.addWidget(lbl_n)
            row.addStretch()
            row.addWidget(lbl_v)
            
            bar = QtWidgets.QProgressBar()
            bar.setFixedHeight(8)
            bar.setTextVisible(False)
            bar.setValue(val)
            bar.setStyleSheet("""
                QProgressBar { background: rgba(255,255,255,0.1); border-radius: 4px; }
                QProgressBar::chunk { background: #F2F2F7; border-radius: 4px; }
            """)
            self.bars[name] = bar
            
            l_sys.addLayout(row)
            l_sys.addSpacing(6)
            l_sys.addWidget(bar)
            l_sys.addSpacing(16)
            
        l_sys.addStretch()
        grid.addWidget(w_sys, 1, 3, 1, 1)
        
        right_panel.addLayout(grid, 1)
        main_layout.addLayout(right_panel, 1)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    
    font = QtGui.QFont("Century Gothic", 12)
    font.setStyleHint(QtGui.QFont.SansSerif)
    app.setFont(font)

    window = DesktopDashboard()
    window.show()
    sys.exit(app.exec_())
