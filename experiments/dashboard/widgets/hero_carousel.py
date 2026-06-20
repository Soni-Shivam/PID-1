"""
Widget 4: Hero Carousel — 2×2 Large Banner
===========================================
Spec-accurate optimisations:
  • QImageReader.setScaledSize() downscales the hero image DURING decode,
    so the full-resolution buffer is never allocated in RAM.
  • Gradient overlay is a QWidget on top of the image QLabel, positioned
    via absolute geometry — no QML, no hardware compositing.
  • Gradient has exactly 2 color stops (spec: "keep gradient simple").
  • Auto-advance carousel uses QTimer at 1/5 Hz (5s interval) — negligible CPU.
"""
import os
from core.qt_compat import QtCore, QtGui, QtWidgets
from grid_manager import BaseWidgetCard, SlotSize
from design_system import (
    load_pixmap_scaled, pill_btn_qss, ghost_btn_qss,
    RADIUS, TEXT_PRIMARY, TEXT_SECONDARY,
)

_SLIDES = [
    {
        "title":    "Master your future.",
        "subtitle": "Interactive learning for CBSE, JEE, NEET, and UPSC.\nYour living room is the new classroom.",
        "cta":      "Start Learning",
        "bg":       "#1A1035",
        "accent":   "#818CF8",
        "image":    os.path.join(os.path.dirname(__file__), "..", "assets", "hero_1_education.png"),
    },
    {
        "title":    "Play games on the big screen.",
        "subtitle": "Cloud and casual games.\nNo expensive console required.",
        "cta":      "Browse Games",
        "bg":       "#0C1F12",
        "accent":   "#4ADE80",
        "image":    os.path.join(os.path.dirname(__file__), "..", "assets", "hero_2_gaming.png"),
    },
    {
        "title":    "Desktop productivity, unleashed.",
        "subtitle": "Browse, create, code, and manage\ninvestments seamlessly on your TV.",
        "cta":      "Open Workspace",
        "bg":       "#1F0C0C",
        "accent":   "#F87171",
        "image":    os.path.join(os.path.dirname(__file__), "..", "assets", "hero_3_productivity.png"),
    },
    {
        "title":    "Ask me anything.",
        "subtitle": "Meet your JioPC Assistant. Draft emails,\nsolve math problems, or just chat.",
        "cta":      "Try AI Assistant",
        "bg":       "#0A0F1A",
        "accent":   "#60A5FA",
        "image":    os.path.join(os.path.dirname(__file__), "..", "assets", "hero_4_ai.png"),
    },
    {
        "title":    "Watch, stream, relax.",
        "subtitle": "Your favorite shows, live sports, and\nmovies, just one click away.",
        "cta":      "Start Watching",
        "bg":       "#2B0C1A",
        "accent":   "#EC4899",
        "image":    os.path.join(os.path.dirname(__file__), "..", "assets", "hero_5_media.png"),
    },
]


class HeroCarouselWidget(BaseWidgetCard):
    """2×2 Hero image banner with auto-advancing carousel slides."""
    SUPPORTED_SIZES = [SlotSize.LARGE]

    def __init__(self, state=None, size: SlotSize = SlotSize.LARGE):
        super().__init__("hero", size)
        self.setStyleSheet(f"""
            HeroCarouselWidget {{
                border-radius: {RADIUS}px;
                border-top:  1px solid rgba(255,255,255,0.08);
                border-left: 1px solid rgba(255,255,255,0.08);
                border-bottom: 1px solid rgba(0,0,0,0.50);
                border-right:  1px solid rgba(0,0,0,0.50);
                background: {_SLIDES[0]['bg']};
            }}
        """)
        self._current = 0
        self._build()
        self._show_slide(0)

        # Auto-advance at 5s — 0.2 Hz, barely measurable CPU
        self._adv_timer = QtCore.QTimer(self)
        self._adv_timer.setInterval(5000)
        self._adv_timer.timeout.connect(self._next_slide)
        self._adv_timer.start()

    # ── build shell ──────────────────────────────────────────────────────────
    def _build(self):
        # Image layer (bottom-most)
        self._img_lbl = QtWidgets.QLabel(self)
        self._img_lbl.setScaledContents(False)
        self._img_lbl.setAlignment(QtCore.Qt.AlignCenter)
        self._img_lbl.lower()

        # Gradient overlay (transparent QWidget sitting on top of image)
        # Two stops only (spec requirement) — keeps paint cost minimal
        self._overlay = QtWidgets.QWidget(self)
        self._overlay.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(0,0,0,0.82),
                    stop:1 rgba(0,0,0,0.00)
                );
                border-radius: 0px;
            }
        """)
        self._overlay.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

        # Content layer
        self._content = QtWidgets.QWidget(self)
        self._content.setStyleSheet("background:transparent;")
        self._content.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, False)

        cl = QtWidgets.QVBoxLayout(self._content)
        cl.setContentsMargins(28, 40, 28, 24)
        cl.setSpacing(0)
        cl.addStretch()

        # Accent tag
        self._lbl_tag = QtWidgets.QLabel("✦  FEATURED")
        self._lbl_tag.setStyleSheet(
            "color:rgba(255,255,255,0.45); font-size:10px; font-weight:700;"
            " letter-spacing:2px; background:transparent;")

        # Title
        self._lbl_title = QtWidgets.QLabel()
        self._lbl_title.setWordWrap(True)
        self._lbl_title.setStyleSheet(
            "color:#FFFFFF; font-size:28px; font-weight:800;"
            " background:transparent; line-height:1.2;")

        # Subtitle
        self._lbl_sub = QtWidgets.QLabel()
        self._lbl_sub.setWordWrap(True)
        self._lbl_sub.setStyleSheet(
            "color:rgba(255,255,255,0.60); font-size:13px; font-weight:400;"
            " background:transparent;")

        # Buttons row
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setSpacing(12)
        self._btn_cta = QtWidgets.QPushButton()
        self._btn_cta.setFixedHeight(44)
        self._btn_cta.setCursor(QtCore.Qt.PointingHandCursor)
        self._btn_cta.setStyleSheet(pill_btn_qss(radius=22))

        btn_more = QtWidgets.QPushButton("Learn more")
        btn_more.setFixedHeight(44)
        btn_more.setCursor(QtCore.Qt.PointingHandCursor)
        btn_more.setStyleSheet(ghost_btn_qss(radius=22))
        btn_row.addWidget(self._btn_cta)
        btn_row.addWidget(btn_more)
        btn_row.addStretch()

        # Dot indicators
        self._dot_row = QtWidgets.QHBoxLayout()
        self._dot_row.setSpacing(6)
        self._dots: list[QtWidgets.QLabel] = []
        for i in range(len(_SLIDES)):
            dot = QtWidgets.QLabel()
            dot.setFixedSize(6, 6)
            dot.setStyleSheet("background:rgba(255,255,255,0.3); border-radius:3px;")
            self._dots.append(dot)
            self._dot_row.addWidget(dot)
        self._dot_row.addStretch()

        cl.addWidget(self._lbl_tag)
        cl.addSpacing(8)
        cl.addWidget(self._lbl_title)
        cl.addSpacing(8)
        cl.addWidget(self._lbl_sub)
        cl.addSpacing(20)
        cl.addLayout(btn_row)
        cl.addSpacing(16)
        cl.addLayout(self._dot_row)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()
        self._img_lbl.setGeometry(0, 0, w, h)
        # Overlay covers only the left 60% — gradient fades to transparent right
        self._overlay.setGeometry(0, 0, int(w * 0.65), h)
        self._content.setGeometry(0, 0, int(w * 0.65), h)

    def _show_slide(self, idx: int):
        slide = _SLIDES[idx]

        # Background colour (solid fallback when no image)
        self.setStyleSheet(self.styleSheet().split("background:")[0]
                           + f"background: {slide['bg']}; }}")

        # Image: load via QImageReader with pre-scale (RAM-safe)
        if slide["image"] and os.path.exists(slide["image"]):
            target_w = max(self.width(), 500)
            target_h = max(self.height(), 300)
            px = load_pixmap_scaled(slide["image"], target_w, target_h)
            self._img_lbl.setPixmap(px)
            # Ensure the label does NOT stretch the image, instead cropping the overflow
            self._img_lbl.setScaledContents(False)
            self._img_lbl.setAlignment(QtCore.Qt.AlignCenter)
        else:
            self._img_lbl.clear()

        # Text
        self._lbl_title.setText(slide["title"])
        self._lbl_sub.setText(slide["subtitle"])
        self._btn_cta.setText(slide["cta"])

        # Dots
        for i, dot in enumerate(self._dots):
            if i == idx:
                dot.setStyleSheet(
                    f"background:{slide['accent']}; border-radius:4px;")
                dot.setFixedSize(18, 6)
            else:
                dot.setStyleSheet("background:rgba(255,255,255,0.25); border-radius:3px;")
                dot.setFixedSize(6, 6)

    def _next_slide(self):
        self._current = (self._current + 1) % len(_SLIDES)
        self._show_slide(self._current)
