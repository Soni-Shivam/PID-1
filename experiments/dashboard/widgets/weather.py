import os
from core.qt_compat import QtCore, QtGui, QtWidgets
from grid_manager import BaseWidgetCard, SlotSize
from design_system import RADIUS, card_qss
from utils import get_icon_path

class WeatherWidget(BaseWidgetCard):
    SUPPORTED_SIZES = [SlotSize.SMALL, SlotSize.TALL]

    def __init__(self, state, size=SlotSize.SMALL):
        super().__init__("weather", size)
        self.setStyleSheet(f"WeatherWidget, QFrame#wcard {{ {card_qss('#1A202A')} }}")
        self.state = state

        # Load background image
        bg_path = os.path.join(os.path.dirname(__file__), "..", "assets", "weather_bg.png")
        self._bg_img = None
        if os.path.exists(bg_path):
            self._bg_img = QtGui.QPixmap(bg_path)

        l_weather = QtWidgets.QVBoxLayout(self)
        l_weather.setContentsMargins(16, 36, 16, 16)
        lbl_w_title = QtWidgets.QLabel("Weather")
        lbl_w_title.setStyleSheet("color:#FFFFFF; font-size:15px; font-weight:600; background:transparent;")
        lbl_w_loc = QtWidgets.QLabel("Mumbai, 28°C")
        lbl_w_loc.setStyleSheet("color:#A1A1AA; font-size:13px; background:transparent;")

        lbl_w_icon = QtWidgets.QLabel()
        lbl_w_icon.setAlignment(QtCore.Qt.AlignCenter)
        lbl_w_icon.setPixmap(
            QtGui.QPixmap(get_icon_path("sun")).scaled(
                72, 72, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
            )
        )

        l_weather.addWidget(lbl_w_title)
        l_weather.addWidget(lbl_w_loc)
        l_weather.addStretch()
        l_weather.addWidget(lbl_w_icon)
        l_weather.addStretch()

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        rect = self.rect()
        
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(rect), RADIUS, RADIUS)
        p.setClipPath(path)

        # Draw image
        if self._bg_img and not self._bg_img.isNull():
            # scale to fill
            scaled = self._bg_img.scaled(self.size(), QtCore.Qt.KeepAspectRatioByExpanding, QtCore.Qt.SmoothTransformation)
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            p.drawPixmap(x, y, scaled)
        else:
            p.fillRect(rect, QtGui.QColor("#1C1C2E"))

        # Gradient overlay
        grad = QtGui.QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0, QtGui.QColor(10, 15, 30, 180))
        grad.setColorAt(1, QtGui.QColor(10, 15, 30, 80))
        p.fillRect(rect, grad)
        
        # Border
        p.setClipping(False)
        p.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 20), 1))
        p.setBrush(QtCore.Qt.NoBrush)
        p.drawRoundedRect(rect.adjusted(0, 0, -1, -1), RADIUS, RADIUS)
