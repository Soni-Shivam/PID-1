import os
from design_system import card_qss, label_qss
from core.qt_compat import QtCore, QtGui, QtWidgets
from grid_manager import BaseWidgetCard, SlotSize
from utils import get_icon

def get_rounded_pixmap(image_path: str, size: int, radius: int) -> QtGui.QPixmap:
    reader = QtGui.QImageReader(image_path)
    sz = reader.size()
    if not sz.isValid():
        px = QtGui.QPixmap(size, size)
        px.fill(QtCore.Qt.gray)
        return px
        
    scale = max(size / sz.width(), size / sz.height())
    reader.setScaledSize(QtCore.QSize(int(sz.width() * scale), int(sz.height() * scale)))
    img = reader.read()
    
    px = QtGui.QPixmap(size, size)
    px.fill(QtCore.Qt.transparent)
    
    p = QtGui.QPainter(px)
    p.setRenderHint(QtGui.QPainter.Antialiasing)
    p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
    
    path = QtGui.QPainterPath()
    path.addRoundedRect(0, 0, size, size, radius, radius)
    p.setClipPath(path)
    
    src_px = QtGui.QPixmap.fromImage(img)
    sw, sh = src_px.width(), src_px.height()
    p.drawPixmap((size - sw) // 2, (size - sh) // 2, sw, sh, src_px)
    p.end()
    
    return px

class MusicPlayerWidget(BaseWidgetCard):
    SUPPORTED_SIZES = [SlotSize.SMALL, SlotSize.WIDE, SlotSize.LARGE]

    def __init__(self, state, size=SlotSize.SMALL):
        super().__init__("music", size)
        self.setStyleSheet(f"MusicPlayerWidget, QFrame#wcard {{ {card_qss('#151515')} }}")
        self.state = state

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────
        hdr = QtWidgets.QHBoxLayout()
        lbl_m_title = QtWidgets.QLabel("Music Player")
        lbl_m_title.setStyleSheet(label_qss(color="#FFFFFF", size=16, weight="bold"))
        lbl_more = QtWidgets.QLabel("•••")
        lbl_more.setStyleSheet("color:#A1A1AA; font-size:16px; font-weight:bold; letter-spacing: 2px; margin-top:-6px;")
        
        hdr.addWidget(lbl_m_title)
        hdr.addStretch()
        hdr.addWidget(lbl_more)
        
        root.addLayout(hdr)
        root.addStretch(1) # Allow spacing to breathe

        # ── Middle (Info + Art) ───────────────────────────────────────────
        mid = QtWidgets.QHBoxLayout()
        info = QtWidgets.QVBoxLayout()
        info.setSpacing(4)
        
        self.lbl_m_song = QtWidgets.QLabel("Focus Beats")
        self.lbl_m_song.setStyleSheet(label_qss(color="#FFFFFF", size=20, weight="bold"))
        self.lbl_m_artist = QtWidgets.QLabel("Artist")
        self.lbl_m_artist.setStyleSheet(label_qss(color="#A1A1AA", size=15))
        
        lbl_cloud = QtWidgets.QLabel("☁")
        lbl_cloud.setStyleSheet(label_qss(color="#A1A1AA", size=14))
        
        info.addWidget(self.lbl_m_song)
        info.addWidget(self.lbl_m_artist)
        info.addWidget(lbl_cloud)
        info.addStretch()
        
        # Album Art dynamically sizes but we give it a good default min
        self.lbl_album = QtWidgets.QLabel()
        self.lbl_album.setFixedSize(84, 84)
        art_path = os.path.join(os.path.dirname(__file__), "..", "assets", "hero_5_media.png")
        if os.path.exists(art_path):
            self.lbl_album.setPixmap(get_rounded_pixmap(art_path, 84, 12))
            
        mid.addLayout(info)
        mid.addStretch()
        mid.addWidget(self.lbl_album)
        
        root.addLayout(mid)
        root.addStretch(2) # Push controls down

        # ── Progress ──────────────────────────────────────────────────────
        self.m_prog = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.m_prog.setFixedHeight(16)
        self.m_prog.setCursor(QtCore.Qt.PointingHandCursor)
        self.m_prog.setValue(30)
        self.m_prog.setStyleSheet("""
            QSlider::groove:horizontal {
                background: rgba(255, 255, 255, 0.2);
                height: 4px;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #FFFFFF;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #FFFFFF;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
        """)
        root.addWidget(self.m_prog)
        root.addSpacing(16)

        # ── Controls ──────────────────────────────────────────────────────
        bot = QtWidgets.QHBoxLayout()
        bot.setSpacing(0)
        
        def _icon_btn(icon_name, size=22):
            btn = QtWidgets.QPushButton()
            btn.setIcon(get_icon(icon_name))
            btn.setIconSize(QtCore.QSize(size, size))
            btn.setFixedSize(36, 36)
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.setStyleSheet("QPushButton { background: transparent; border: none; }")
            return btn
            
        btn_shuffle = _icon_btn("shuffle")
        btn_prev = _icon_btn("skip-back")
        btn_next = _icon_btn("skip-forward")
        btn_repeat = _icon_btn("repeat")
        
        self.btn_m_play = QtWidgets.QPushButton("▶")
        self.btn_m_play.setFixedSize(52, 52)
        self.btn_m_play.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_m_play.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                color: #000000;
                border-radius: 26px;
                font-size: 22px;
                font-weight: bold;
                padding-left: 4px;
                border: none;
            }
            QPushButton:hover { background: #E5E5EA; }
        """)
        
        bot.addWidget(btn_shuffle)
        bot.addStretch()
        bot.addWidget(btn_prev)
        bot.addSpacing(24)
        bot.addWidget(self.btn_m_play)
        bot.addSpacing(24)
        bot.addWidget(btn_next)
        bot.addStretch()
        bot.addWidget(btn_repeat)
        
        root.addLayout(bot)
        
        # Connections
        self.btn_m_play.clicked.connect(self.state.toggle_music)
        self.state.music_updated.connect(self.on_music_updated)
        self.state.music_toggled.connect(self.on_music_toggled)

    def on_music_updated(self, progress, song, artist):
        self.m_prog.setValue(progress)
        self.lbl_m_song.setText(song)
        self.lbl_m_artist.setText(artist)

    def on_music_toggled(self, is_running):
        if is_running:
            self.btn_m_play.setText("⏸")
            self.btn_m_play.setStyleSheet(self.btn_m_play.styleSheet().replace("padding-left: 4px;", "padding-left: 0px;"))
        else:
            self.btn_m_play.setText("▶")
            if "padding-left: 0px;" in self.btn_m_play.styleSheet():
                self.btn_m_play.setStyleSheet(self.btn_m_play.styleSheet().replace("padding-left: 0px;", "padding-left: 4px;"))

