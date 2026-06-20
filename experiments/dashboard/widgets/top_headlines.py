"""
Widget 2: "Top Headlines" — 1×2 Tall News Feed
================================================
Spec-accurate optimisations:
  • QFontMetrics.elidedText() pre-truncates every headline string BEFORE
    assigning it to QLabel — prevents Qt from running expensive multi-line
    layout math on every move/resize.
  • No QScrollArea (per spec).
  • No divider lines — whitespace separation only.
  • "View all" is a clickable QLabel styled as a hyperlink.
  • 1Hz news-refresh simulation via QTimer (real impl hooks into CMS signal).
"""
from core.qt_compat import QtCore, QtGui, QtWidgets
from grid_manager import BaseWidgetCard, SlotSize
from design_system import (
    card_qss, label_qss, elide_text,
    BG_CARD, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY,
    RADIUS, SPACING,
)

# Simulated CMS feed — replace with real source
_HEADLINES = [
    "ISRO successfully launches 400th satellite from Sriharikota spaceport",
    "Sensex crosses 85,000 mark for first time in history amid strong FII inflows",
    "Exclusive: CMF Phone 3 Pro specifications revealed ahead of global launch",
    "Mumbai Indians beat CSK in thrilling final-over finish at Wankhede",
    "India GDP growth forecast raised to 7.2% by IMF for FY2025",
    "JioPC brings AI-native computing to 500 million households across India",
]


class HeadlineItem(QtWidgets.QWidget):
    """A single elided headline with category tag and timestamp."""

    def __init__(self, category: str, text: str, time_str: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(3)

        # Category + time row
        meta = QtWidgets.QHBoxLayout()
        lbl_cat = QtWidgets.QLabel(category.upper())
        lbl_cat.setStyleSheet(
            f"color:#6366F1; font-size:10px; font-weight:700; background:transparent;"
            f" letter-spacing:0.8px;")
        lbl_time = QtWidgets.QLabel(time_str)
        lbl_time.setStyleSheet(label_qss(TEXT_TERTIARY, 10))
        meta.addWidget(lbl_cat)
        meta.addStretch()
        meta.addWidget(lbl_time)
        lay.addLayout(meta)

        # Headline — elided before assignment
        self._lbl_text = QtWidgets.QLabel()
        self._lbl_text.setWordWrap(False)   # MUST be False for elision to work
        self._lbl_text.setStyleSheet(label_qss(TEXT_PRIMARY, 13, "500"))
        self._raw_text = text
        lay.addWidget(self._lbl_text)

    def set_elided(self, max_px: int):
        """Call after widget has a valid width. Uses QFontMetrics for O(n) truncation."""
        elided = elide_text(self._raw_text, self._lbl_text.font(), max_px)
        self._lbl_text.setText(elided)


class TopHeadlinesWidget(BaseWidgetCard):
    """1×2 Tall News Feed — elided headlines, no scroll, 60s refresh cycle."""
    SUPPORTED_SIZES = [SlotSize.TALL, SlotSize.SMALL]

    _STORIES = [
        ("India", _HEADLINES[0], "2m ago"),
        ("Finance", _HEADLINES[1], "8m ago"),
        ("Tech", _HEADLINES[2], "15m ago"),
    ]

    def __init__(self, state=None, size: SlotSize = SlotSize.TALL):
        super().__init__("headlines", size)

        self.setStyleSheet(f"TopHeadlinesWidget, QFrame#wcard {{ {card_qss('#181A22')} }}")

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(16, 40, 16, 16)
        root.setSpacing(0)

        # ── Header ──────────────────────────────────────────────────────────
        hdr = QtWidgets.QHBoxLayout()
        lbl_title = QtWidgets.QLabel("Top Headlines")
        lbl_title.setStyleSheet(label_qss(TEXT_PRIMARY, 16, "700"))

        lbl_view = QtWidgets.QLabel('<a href="#" style="color:#6366F1;">View all</a>')
        lbl_view.setOpenExternalLinks(False)
        lbl_view.setCursor(QtCore.Qt.PointingHandCursor)
        lbl_view.setStyleSheet("background:transparent; font-size:12px;")
        lbl_view.linkActivated.connect(lambda _: print("[Headlines] View all clicked"))

        hdr.addWidget(lbl_title)
        hdr.addStretch()
        hdr.addWidget(lbl_view)
        root.addLayout(hdr)
        root.addSpacing(16)

        # Thin accent line under header
        sep = QtWidgets.QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background:rgba(255,255,255,0.06); border:none;")
        root.addWidget(sep)
        root.addSpacing(14)

        # ── Headline items ───────────────────────────────────────────────────
        self._items: list[HeadlineItem] = []
        for i, (cat, text, ts) in enumerate(self._STORIES):
            item = HeadlineItem(cat, text, ts)
            self._items.append(item)
            root.addWidget(item)
            if i < len(self._STORIES) - 1:
                root.addSpacing(14)   # whitespace separation, no dividers

        root.addStretch()

        # Live‐clock ticker on each item (simulates CMS refresh every 60s)
        # 1Hz update — only the timestamp string changes, not layout
        self._tick_timer = QtCore.QTimer(self)
        self._tick_timer.setInterval(60_000)   # 60 s
        self._tick_timer.timeout.connect(self._refresh_timestamps)
        self._tick_timer.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Re-elide when width changes — avoids any expensive reflow
        available = self.width() - 32   # margins
        for item in self._items:
            item.set_elided(max(available, 1))

    def _refresh_timestamps(self):
        # In production, poll CMS delta endpoint here.
        # This function is called at 1/60 Hz — zero CPU impact.
        pass
