import datetime
from core.qt_compat import QtCore

class DashboardState(QtCore.QObject):
    """Global Observer state manager for the dashboard."""
    # Signals for various state changes
    time_updated = QtCore.pyqtSignal(str, str, str) # greeting, time_str, date_str
    focus_updated = QtCore.pyqtSignal(int, int)     # left, total
    focus_toggled = QtCore.pyqtSignal(bool)         # is_running
    system_health_updated = QtCore.pyqtSignal(int, int, int) # cpu, ram, storage
    music_updated = QtCore.pyqtSignal(int, str, str) # progress, song, artist
    music_toggled = QtCore.pyqtSignal(bool)         # is_running
    
    def __init__(self):
        super().__init__()
        
        # internal states
        self.focus_total = 25 * 60
        self.focus_left = self.focus_total
        self.focus_running = False
        
        self.music_progress = 30
        self.music_running = False
        self.song = "Focus Beats"
        self.artist = "Artist"
        
        self.last_cpu_idle = 0
        self.last_cpu_total = 0
        
        # 1-second global timer
        self.global_timer = QtCore.QTimer(self)
        self.global_timer.setInterval(1000)
        self.global_timer.timeout.connect(self.on_tick)
        self.global_timer.start()
        
        self.tick_count = 0
        self.on_tick() # Initial tick

    def on_tick(self):
        self.tick_count += 1
        self.update_time()
        
        if self.focus_running and self.focus_left > 0:
            self.focus_left -= 1
            self.focus_updated.emit(self.focus_left, self.focus_total)
            
        if self.music_running:
            self.music_progress += 1
            if self.music_progress > 100:
                self.music_progress = 0
                self.next_track()
            self.music_updated.emit(self.music_progress, self.song, self.artist)
            
        if self.tick_count % 2 == 0:
            self.update_system_health()

    def update_time(self):
        now = datetime.datetime.now()
        h = now.hour
        if h < 12: greeting = "Good morning"
        elif h < 17: greeting = "Good afternoon"
        else: greeting = "Good evening"
        
        time_str = now.strftime("%I:%M %p").lstrip("0")
        date_str = now.strftime("%d %B %Y")
        self.time_updated.emit(greeting, time_str, date_str)

    def toggle_focus(self):
        self.focus_running = not self.focus_running
        self.focus_toggled.emit(self.focus_running)

    def toggle_music(self):
        self.music_running = not self.music_running
        self.music_toggled.emit(self.music_running)
        
    def next_track(self):
        self.song = "Deep Work Beats"
        self.music_progress = 0
        self.music_updated.emit(self.music_progress, self.song, self.artist)
        
    def prev_track(self):
        self.song = "Lo-Fi Chill"
        self.music_progress = 0
        self.music_updated.emit(self.music_progress, self.song, self.artist)

    def update_system_health(self):
        cpu_usage = 10
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
                        cpu_usage = int(100.0 * (1.0 - idle_delta / total_delta))
                    self.last_cpu_idle = idle
                    self.last_cpu_total = total
        except: pass
        
        ram_usage = 50
        try:
            with open('/proc/meminfo', 'r') as f:
                mem_total = 0
                mem_avail = 0
                for line in f:
                    if line.startswith("MemTotal:"): mem_total = int(line.split()[1])
                    elif line.startswith("MemAvailable:"): mem_avail = int(line.split()[1]); break
                if mem_total > 0:
                    used = mem_total - mem_avail
                    ram_usage = int((used / mem_total) * 100.0)
        except: pass
        
        storage_usage = 35 # Mocked for now, statvfs can be heavy
        
        self.system_health_updated.emit(cpu_usage, ram_usage, storage_usage)
