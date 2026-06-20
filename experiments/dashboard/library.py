"""
Widget Library Modal — JioPC Discover Desktop
===============================================
Pixel-perfect replication of the JioPC Widget Library design (Screenshot 1).

Layout:
  ┌─────────────────────────────────────────────────────────────────┐
  │  Widget Library                             [⊞ Arrange Layout]  │
  │─────────────────────────────────────────────────────────────────│
  │  ┌──────────────┐  ┌────────────────────────────────────────┐   │
  │  │ 🔍 Search    │  │  ┌────────┐  ┌────────┐  ┌────────┐   │   │
  │  │──────────────│  │  │Preview │  │Preview │  │Preview │   │   │
  │  │ ★ For You   ◀│  │  │  Card  │  │  Card  │  │  Card  │  ↕│   │
  │  │ All          │  │  └────────┘  └────────┘  └────────┘   │   │
  │  │ Information  │  │  ┌────────┐  ┌────────┐  ┌────────┐   │   │
  │  │ Productivity │  │  │        │  │        │  │        │   │   │
  │  │ Entertainment│  │  └────────┘  └────────┘  └────────┘   │   │
  │  │ Finance      │  └────────────────────────────────────────┘   │
  │  └──────────────┘                                               │
  └─────────────────────────────────────────────────────────────────┘

Static QPainter preview renderers → zero live widget instances → zero idle CPU.
"""
from __future__ import annotations

import math
import os
from typing import Dict, List, Optional, Tuple, Set, TYPE_CHECKING

from core.qt_compat import QtCore, QtGui, QtWidgets

if TYPE_CHECKING:
    from grid_manager import SnapGridManager

from grid_manager import SlotSize, TOTAL_SLOTS

# Asset directory for widget thumbnails
_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")

# Map widget ID → thumbnail image filename
_THUMB_MAP: Dict[str, str] = {
    "focus":    "thumb_focus.png",
    "headlines":"thumb_headlines.png",
    "weather":  "thumb_weather.png",
    "assistant":"thumb_assistant.png",
    "calendar": "thumb_calendar.png",
    "hero":     "thumb_hero.png",
    "music":    "thumb_music.png",
    "activity": "thumb_activity.png",
    "sys":      "thumb_sys.png",
    "finance":  "thumb_finance.png",
    "social":   "thumb_social.png",
    "explore":  "thumb_explore.png",
}

# ══════════════════════════════════════════════════════════════════════════════
# Design Tokens
# ══════════════════════════════════════════════════════════════════════════════
_MOD_DARK    = QtGui.QColor(12,  12,  16,  235)   # full-screen overlay
_SIDEBAR_BG  = "#14141A"
_CARD_BG     = "#1C1C1E"
_CARD_HOV    = "#232328"
_SEL_BG      = "#FFFFFF"
_SEL_FG      = "#0C0C10"
_PILL_FG     = "#8E8E93"
_TXT_W       = "#F2F2F7"
_TXT_G       = "#8E8E93"
_TXT_D       = "#48484A"
_GREEN       = "#22C55E"
_INDIGO      = "#6366F1"

_R           = 16          # card outer radius
_PILL_R      = 19          # category pill radius
_CARD_W      = 300         # widget preview card width
_CARD_H      = 340         # widget preview card total height
_PREV_H      = 190         # painted preview area height
_COLS        = 2           # grid columns

# ══════════════════════════════════════════════════════════════════════════════
# Categories
# ══════════════════════════════════════════════════════════════════════════════
CATEGORIES: List[Tuple[str, Optional[Set[str]]]] = [
    ("★ For You",     None),
    ("All",           None),
    ("Productivity",  {"focus", "activity", "sys", "assistant"}),
    ("Information",   {"headlines", "weather", "finance"}),
    ("Entertainment", {"music", "hero", "social", "explore"}),
    ("Finance",       {"finance"}),
    ("Education",     {"hero", "explore"}),
    ("Shopping",      set()),
    ("Sports",        set()),
    ("A.I.",          {"assistant"}),
    ("Utilities",     {"sys", "calendar", "activity"}),
]

# ══════════════════════════════════════════════════════════════════════════════
# Catalog
# ══════════════════════════════════════════════════════════════════════════════
CATALOG: List[Tuple] = [
    # (w_id,  display_name,      description (2-line max),             size,           accent)
    ("focus",    "Focus Timer",
     "Pomodoro & countdown sessions",               SlotSize.WIDE,  "#6366F1"),
    ("headlines","Top Headlines",
     "These are the quick actions\nfor your most used apps",
                                                    SlotSize.TALL,  "#3B82F6"),
    ("weather",  "Weather",
     "Sunny, today",                                SlotSize.SMALL, "#0EA5E9"),
    ("assistant","JioPC Assistant",
     "Just ask to get started",                     SlotSize.WIDE,  "#8B5CF6"),
    ("calendar", "Calendar",
     "Upcoming events & date grid",                 SlotSize.SMALL, "#10B981"),
    ("hero",     "Discover JioPC",
     "A full computer on your\nTV. Browse, create...",
                                                    SlotSize.LARGE, "#F59E0B"),
    ("music",    "Music Player",
     "Play controls & progress",                    SlotSize.SMALL, "#EC4899"),
    ("explore",  "Start Exploring",
     "Quick actions for your\nmost used apps",      SlotSize.LARGE, "#8B5CF6"),
    ("activity", "Activity Graph",
     "Animated pulse spline graph",                 SlotSize.WIDE,  "#F59E0B"),
    ("sys",      "System Health",
     "CPU · RAM · Storage bars",                    SlotSize.SMALL, "#EF4444"),
    ("finance",  "Finance",
     "Market prices & % changes",                   SlotSize.SMALL, "#22C55E"),
    ("social",   "Social Updates",
     "Messages & notifications",                    SlotSize.SMALL, "#EC4899"),
]


# ══════════════════════════════════════════════════════════════════════════════
# Preview Painter Utilities
# ══════════════════════════════════════════════════════════════════════════════
def _rr(p: QtGui.QPainter, rect, r: float, color):
    p.setBrush(QtGui.QColor(color))
    p.setPen(QtCore.Qt.NoPen)
    if isinstance(rect, QtCore.QRect):
        rect = QtCore.QRectF(rect)
    p.drawRoundedRect(rect, r, r)

def _txt(p: QtGui.QPainter, rect, text: str, size: float = 10,
         color: str = "#F2F2F7", bold: bool = False,
         align=None, family: str = ""):
    f = QtGui.QFont(family if family else "Century Gothic", int(size))
    f.setBold(bold)
    p.setFont(f)
    p.setPen(QtGui.QColor(color))
    if align is None:
        align = QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
    if isinstance(rect, QtCore.QRectF):
        rect = rect.toRect()
    p.drawText(rect, align, text)

def _line(p: QtGui.QPainter, x1, y1, x2, y2, color, width=1.0):
    p.setPen(QtGui.QPen(QtGui.QColor(color), width,
                        QtCore.Qt.SolidLine, QtCore.Qt.RoundCap))
    p.drawLine(x1, y1, x2, y2)

def _progress_bar(p, x, y, w, h, frac, fg, bg="#2C2C2E"):
    _rr(p, QtCore.QRect(x, y, w, h), h/2, bg)
    if frac > 0:
        _rr(p, QtCore.QRect(x, y, max(h, int(w * frac)), h), h/2, fg)


# ══════════════════════════════════════════════════════════════════════════════
# Static Widget Preview Renderers
# Each fn(p, rect, accent) — called ONCE during paintEvent, no live timers.
# ══════════════════════════════════════════════════════════════════════════════

def _prev_focus(p, r: QtCore.QRect, _a):
    _rr(p, r, 10, "#4A3B69")

    # Focus | Break | Rest tabs row
    focus_pill = QtCore.QRect(r.x() + 10, r.y() + 10, 52, 19)
    _rr(p, focus_pill, 9, "#6366F1")
    _txt(p, focus_pill, "Focus", 7.5, "#FFF", True, QtCore.Qt.AlignCenter)
    _txt(p, QtCore.QRect(r.x() + 66, r.y() + 10, 34, 19), "Break", 7.5,
         "rgba(255,255,255,0.45)", False, QtCore.Qt.AlignCenter)
    _txt(p, QtCore.QRect(r.x() + 103, r.y() + 10, 28, 19), "Rest", 7.5,
         "rgba(255,255,255,0.45)", False, QtCore.Qt.AlignCenter)
    # Gear icon
    _txt(p, QtCore.QRect(r.right() - 26, r.y() + 10, 20, 19), "⚙", 9,
         "rgba(255,255,255,0.35)", False, QtCore.Qt.AlignCenter)

    # Big time
    _txt(p, QtCore.QRect(r.x(), r.y() + 36, r.width(), 54),
         "30:00", 30, "#FFFFFF", True, QtCore.Qt.AlignCenter)

    # Start button
    bw, bh = 86, 28
    bx = r.x() + (r.width() - bw) // 2
    by = r.y() + 96
    _rr(p, QtCore.QRect(bx, by, bw, bh), 14, "#FFFFFF")
    _txt(p, QtCore.QRect(bx, by, bw, bh), "● Start", 9, "#1A0A3A", True, QtCore.Qt.AlignCenter)


def _prev_headlines(p, r: QtCore.QRect, _a):
    _rr(p, r, 10, "#1C1C1E")
    items = [
        "ISRO launches new satellite",
        "Sensex crosses 95,000 mark",
        "Exclusive: CMF Phone 3 Pro Specs",
        "IPL 2026: Mumbai Indians beat CSK",
    ]
    for i, line in enumerate(items):
        iy = r.y() + 12 + i * 22
        _txt(p, QtCore.QRect(r.x() + 10, iy, r.width() - 20, 16),
             line, 8, "#D0D0D0", False, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        if i < len(items) - 1:
            p.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 14), 1))
            p.drawLine(r.x() + 10, iy + 19, r.right() - 10, iy + 19)


def _prev_weather(p, r: QtCore.QRect, _a):
    _rr(p, r, 10, "#1C1C2E")
    _txt(p, QtCore.QRect(r.x() + 12, r.y() + 10, 100, 18), "Sunny", 10, "#F2F2F7", True)
    _txt(p, QtCore.QRect(r.x() + 8, r.y() + 32, 44, 44), "☀", 26, "#FBBF24", False, QtCore.Qt.AlignCenter)
    _txt(p, QtCore.QRect(r.x() + 54, r.y() + 36, 80, 36),
         "22°C", 22, "#F2F2F7", True, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
    _txt(p, QtCore.QRect(r.x() + 10, r.y() + 100, r.width() - 20, 14),
         "📍 Location, Mumbai", 7, "#8E8E93", False,
         QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)


def _prev_assistant(p, r: QtCore.QRect, _a):
    grad = QtGui.QLinearGradient(r.topLeft(), r.bottomRight())
    grad.setColorAt(0, QtGui.QColor("#1E1040"))
    grad.setColorAt(1, QtGui.QColor("#2D1B4E"))
    p.setBrush(grad)
    p.setPen(QtCore.Qt.NoPen)
    p.drawRoundedRect(QtCore.QRectF(r), 10, 10)

    # Jio badge
    badge = QtCore.QRect(r.x() + 10, r.y() + 10, 34, 18)
    _rr(p, badge, 9, "#1565C0")
    _txt(p, badge, "Jio", 7.5, "#FFFFFF", True, QtCore.Qt.AlignCenter)
    _txt(p, QtCore.QRect(badge.right() + 5, r.y() + 10, 100, 18),
         "JioPC Assistant", 7.5, "#D0D0F0", True)

    # Mic circle
    cx, cy, mr = r.x() + r.width() // 2, r.y() + 72, 22
    p.setBrush(QtGui.QColor(50, 40, 80, 200))
    p.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 30), 1))
    p.drawEllipse(cx - mr, cy - mr, mr * 2, mr * 2)
    _txt(p, QtCore.QRect(cx - mr, cy - mr, mr * 2, mr * 2),
         "🎤", 16, "#FFF", False, QtCore.Qt.AlignCenter)

    _txt(p, QtCore.QRect(r.x(), r.y() + 108, r.width(), 18),
         "Just ask to get started", 8, "#8080A0", False, QtCore.Qt.AlignCenter)


def _prev_calendar(p, r: QtCore.QRect, _a):
    _rr(p, r, 10, "#1C1C1E")
    # Header
    _txt(p, QtCore.QRect(r.x() + 10, r.y() + 8, r.width() - 60, 16),
         "Calendar", 9, "#F2F2F7", True)
    _txt(p, QtCore.QRect(r.right() - 36, r.y() + 8, 14, 16), "‹", 12, "#8E8E93",
         False, QtCore.Qt.AlignCenter)
    _txt(p, QtCore.QRect(r.right() - 20, r.y() + 8, 14, 16), "›", 12, "#8E8E93",
         False, QtCore.Qt.AlignCenter)
    # Day names
    days = ["S", "M", "T", "W", "T", "F", "S"]
    cw = (r.width() - 16) // 7
    for i, d in enumerate(days):
        _txt(p, QtCore.QRect(r.x() + 8 + i * cw, r.y() + 28, cw, 13),
             d, 7, "#8E8E93", False, QtCore.Qt.AlignCenter)
    # Dates
    weeks = [
        [None, None, None, 1, 2, 3, 4],
        [5, 6, 7, 8, 9, 10, 11],
        [12, 13, 14, 15, 16, 17, 18],
        [19, 20, 21, 22, 23, 24, 25],
        [26, 27, 28, 29, 30, 31, None],
    ]
    for row, week in enumerate(weeks):
        for col, date in enumerate(week):
            if not date:
                continue
            dx = r.x() + 8 + col * cw
            dy = r.y() + 44 + row * 16
            if date == 12:
                _rr(p, QtCore.QRect(dx + 1, dy - 1, cw - 2, 14), 7, "#22C55E")
                _txt(p, QtCore.QRect(dx, dy, cw, 13), str(date), 7, "#FFF", True, QtCore.Qt.AlignCenter)
            elif date == 19:
                _rr(p, QtCore.QRect(dx + 1, dy - 1, cw - 2, 14), 7, "#6366F1")
                _txt(p, QtCore.QRect(dx, dy, cw, 13), str(date), 7, "#FFF", True, QtCore.Qt.AlignCenter)
            else:
                _txt(p, QtCore.QRect(dx, dy, cw, 13), str(date), 7, "#B0B0B0", False, QtCore.Qt.AlignCenter)


def _prev_hero(p, r: QtCore.QRect, _a):
    grad = QtGui.QLinearGradient(r.x(), 0, r.right(), 0)
    grad.setColorAt(0, QtGui.QColor("#180E30"))
    grad.setColorAt(1, QtGui.QColor("#2E1A50"))
    p.setBrush(grad)
    p.setPen(QtCore.Qt.NoPen)
    p.drawRoundedRect(QtCore.QRectF(r), 10, 10)

    # TV mockup (right half)
    tv_x = r.x() + r.width() * 55 // 100
    tv_r = QtCore.QRect(tv_x, r.y() + 12, r.width() - (tv_x - r.x()) - 10, r.height() - 24)
    _rr(p, tv_r, 8, "#2A1E44")
    inner = QtCore.QRect(tv_r.x() + 5, tv_r.y() + 5, tv_r.width() - 10, tv_r.height() - 10)
    _rr(p, inner, 4, "#1A1032")
    _txt(p, tv_r, "📺", 20, "#9060E0", False, QtCore.Qt.AlignCenter)

    # Text
    _txt(p, QtCore.QRect(r.x() + 10, r.y() + 18, tv_x - r.x() - 15, 20),
         "Discover JioPC", 9, "#FFFFFF", True)
    _txt(p, QtCore.QRect(r.x() + 10, r.y() + 42, tv_x - r.x() - 15, 60),
         "A full computer\non your TV.\nBrowse, create...", 7, "#A090C0", False,
         QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)

    # CTA button
    btn_r = QtCore.QRect(r.x() + 10, r.y() + r.height() - 28, 70, 18)
    _rr(p, btn_r, 9, "#6340B0")
    _txt(p, btn_r, "Explore", 7, "#FFF", True, QtCore.Qt.AlignCenter)


def _prev_music(p, r: QtCore.QRect, _a):
    _rr(p, r, 10, "#1C1C1E")
    # Album art
    art = QtCore.QRect(r.x() + 10, r.y() + 10, 46, 46)
    _rr(p, art, 8, "#EC4899")
    _txt(p, art, "♪", 18, "#FFF", False, QtCore.Qt.AlignCenter)
    # Song info
    _txt(p, QtCore.QRect(r.x() + 62, r.y() + 16, r.width() - 72, 16),
         "Blinding Lights", 9, "#F2F2F7", True)
    _txt(p, QtCore.QRect(r.x() + 62, r.y() + 34, r.width() - 72, 14),
         "The Weeknd", 8, "#8E8E93", False)
    # Progress bar
    _progress_bar(p, r.x() + 10, r.y() + 64, r.width() - 20, 4, 0.38, "#EC4899")
    _txt(p, QtCore.QRect(r.x() + 10, r.y() + 70, 24, 12), "1:12", 6.5, "#8E8E93")
    _txt(p, QtCore.QRect(r.right() - 34, r.y() + 70, 30, 12), "3:11", 6.5, "#8E8E93",
         False, QtCore.Qt.AlignRight)
    # Controls
    for glyph, cx in [("⏮", 0.22), ("⏸", 0.5), ("⏭", 0.78)]:
        cx_px = r.x() + int(r.width() * cx)
        _txt(p, QtCore.QRect(cx_px - 16, r.y() + 92, 32, 28), glyph,
             14 if glyph == "⏸" else 12,
             "#F2F2F7" if glyph == "⏸" else "#8E8E93", False, QtCore.Qt.AlignCenter)


def _prev_explore(p, r: QtCore.QRect, _a):
    _rr(p, r, 10, "#2A2438")
    _txt(p, QtCore.QRect(r.x() + 10, r.y() + 8, r.width() - 20, 18),
         "Start exploring", 9, "#FFFFFF", True)
    tiles = [
        ("#1E1B4B", "📚", "Study",   "#818CF8"),
        ("#052E16", "🎮", "Games",   "#4ADE80"),
        ("#450A0A", "🏃", "Fitness", "#F87171"),
        ("#431407", "📈", "Invest",  "#FCD34D"),
    ]
    tw = (r.width() - 24) // 2
    th = (r.height() - 38) // 2
    for idx, (bg, icon, name, ac) in enumerate(tiles):
        tx = r.x() + 8 + (idx % 2) * (tw + 8)
        ty = r.y() + 30 + (idx // 2) * (th + 8)
        tile_r = QtCore.QRect(tx, ty, tw, th)
        _rr(p, tile_r, 6, bg)
        _txt(p, QtCore.QRect(tx + 5, ty + 5, 28, 24), icon, 14, "#FFF", False, QtCore.Qt.AlignCenter)
        _txt(p, QtCore.QRect(tx + 4, ty + th - 16, tw - 8, 14), name, 7, ac, False)


def _prev_activity(p, r: QtCore.QRect, _a):
    _rr(p, r, 10, "#1C1C1E")
    pts_n = [(0,.75),(0.1,.62),(0.2,.48),(0.3,.56),(0.4,.30),
              (0.5,.38),(0.6,.18),(0.7,.30),(0.85,.08),(1.0,.38)]
    aw, ah = r.width() - 20, r.height() - 20
    ax, ay = r.x() + 10, r.y() + 10

    # Faint grid
    p.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 12), 1))
    for i in range(3):
        gy = ay + ah * i // 2
        p.drawLine(ax, gy, ax + aw, gy)

    # Filled path
    fill_path = QtGui.QPainterPath()
    fill_path.moveTo(ax, ay + ah)
    for fx, fy in pts_n:
        fill_path.lineTo(ax + int(fx * aw), ay + int(fy * ah))
    fill_path.lineTo(ax + aw, ay + ah)
    fill_path.closeSubpath()

    grad = QtGui.QLinearGradient(0, ay, 0, ay + ah)
    grad.setColorAt(0, QtGui.QColor(243, 158, 11, 100))
    grad.setColorAt(1, QtGui.QColor(243, 158, 11, 0))
    p.setBrush(grad)
    p.setPen(QtCore.Qt.NoPen)
    p.drawPath(fill_path)

    # Stroke
    stroke = QtGui.QPainterPath()
    first = True
    for fx, fy in pts_n:
        px, py = ax + int(fx * aw), ay + int(fy * ah)
        if first:
            stroke.moveTo(px, py)
            first = False
        else:
            stroke.lineTo(px, py)
    p.setPen(QtGui.QPen(QtGui.QColor("#F59E0B"), 2, QtCore.Qt.SolidLine,
                        QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))
    p.setBrush(QtCore.Qt.NoBrush)
    p.drawPath(stroke)

    # Pulse dot
    lx = ax + aw
    ly = ay + int(pts_n[-1][1] * ah)
    p.setBrush(QtGui.QColor("#F59E0B"))
    p.setPen(QtCore.Qt.NoPen)
    p.drawEllipse(lx - 4, ly - 4, 8, 8)


def _prev_sys(p, r: QtCore.QRect, _a):
    _rr(p, r, 10, "#1C1C1E")
    _txt(p, QtCore.QRect(r.x() + 10, r.y() + 8, r.width() - 20, 16),
         "System Health", 9, "#F2F2F7", True)
    metrics = [("CPU", 0.42, "#EF4444"), ("RAM", 0.67, "#F59E0B"), ("SSD", 0.31, "#22C55E")]
    for i, (label, frac, color) in enumerate(metrics):
        my = r.y() + 30 + i * 34
        _txt(p, QtCore.QRect(r.x() + 10, my, 38, 12), label, 7.5, "#8E8E93", True)
        pct_lbl = f"{int(frac*100)}%"
        _txt(p, QtCore.QRect(r.right() - 36, my, 32, 12), pct_lbl, 7.5, "#F2F2F7", True,
             QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        _progress_bar(p, r.x() + 10, my + 15, r.width() - 20, 5, frac, color)


def _prev_finance(p, r: QtCore.QRect, _a):
    _rr(p, r, 10, "#1C1C1E")
    _txt(p, QtCore.QRect(r.x() + 10, r.y() + 8, r.width() - 20, 16),
         "Finance", 9, "#F2F2F7", True)
    rows = [("NIFTY", "18,540", "+1.2%", True),
            ("SENSEX", "61,320", "-0.3%", False),
            ("USD", "83.22", "+0.1%", True)]
    for i, (sym, price, chg, up) in enumerate(rows):
        iy = r.y() + 30 + i * 34
        _txt(p, QtCore.QRect(r.x() + 10, iy, 50, 12), sym, 7, "#8E8E93", True)
        _txt(p, QtCore.QRect(r.x() + 10, iy + 14, 70, 14), price, 9, "#F2F2F7", True)
        clr = "#22C55E" if up else "#EF4444"
        _txt(p, QtCore.QRect(r.right() - 54, iy + 14, 50, 14),
             ("▲ " if up else "▼ ") + chg, 8, clr, True,
             QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)


def _prev_social(p, r: QtCore.QRect, _a):
    _rr(p, r, 10, "#1C1C1E")
    _txt(p, QtCore.QRect(r.x() + 10, r.y() + 8, r.width() - 20, 16),
         "Social Updates", 9, "#F2F2F7", True)
    items = [("👤", "Aisha commented on your post", "2m"),
             ("💬", "Team: 3 new messages", "8m"),
             ("❤️", "12 likes on your photo", "15m")]
    for i, (icon, text, ts) in enumerate(items):
        iy = r.y() + 30 + i * 32
        _txt(p, QtCore.QRect(r.x() + 8, iy + 4, 18, 20), icon, 10, "#FFF", False, QtCore.Qt.AlignCenter)
        _txt(p, QtCore.QRect(r.x() + 30, iy + 2, r.width() - 70, 14), text, 7, "#D0D0D0")
        _txt(p, QtCore.QRect(r.right() - 30, iy + 2, 26, 14), ts, 7, "#8E8E93", False,
             QtCore.Qt.AlignRight)
        if i < len(items) - 1:
            p.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 12), 1))
            p.drawLine(r.x() + 10, iy + 28, r.right() - 10, iy + 28)


_PREVIEW_FNS = {
    "focus":    _prev_focus,
    "headlines":_prev_headlines,
    "weather":  _prev_weather,
    "assistant":_prev_assistant,
    "calendar": _prev_calendar,
    "hero":     _prev_hero,
    "music":    _prev_music,
    "explore":  _prev_explore,
    "activity": _prev_activity,
    "sys":      _prev_sys,
    "finance":  _prev_finance,
    "social":   _prev_social,
}


# ══════════════════════════════════════════════════════════════════════════════
# Preview Canvas — shows AI-generated thumbnail image (zoom-crop), no stretch
# ══════════════════════════════════════════════════════════════════════════════
class _PreviewCanvas(QtWidgets.QWidget):
    """Shows the AI-generated widget thumbnail, cropped to fill without stretching.
    Falls back to a gradient swatch if no image is available."""

    # Cache pixmaps across instances to avoid redundant disk reads
    _cache: Dict[str, QtGui.QPixmap] = {}

    def __init__(self, w_id: str, accent: str, parent=None):
        super().__init__(parent)
        self._w_id   = w_id
        self._accent = accent
        self.setFixedHeight(_PREV_H)
        self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent, False)
        self.setStyleSheet("background: transparent;")

        # Preload image into the cache
        if w_id not in _PreviewCanvas._cache:
            fname = _THUMB_MAP.get(w_id, "")
            path  = os.path.join(_ASSETS_DIR, fname) if fname else ""
            px    = QtGui.QPixmap(path) if path and os.path.exists(path) else QtGui.QPixmap()
            _PreviewCanvas._cache[w_id] = px

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        w, h  = self.width(), self.height()
        rect  = QtCore.QRect(0, 0, w, h)
        px    = _PreviewCanvas._cache.get(self._w_id, QtGui.QPixmap())

        if not px.isNull():
            # Zoom-crop: scale so image COVERS the rect, then center-crop
            pw, ph = px.width(), px.height()
            scale  = max(w / pw, h / ph)
            sw, sh = int(pw * scale), int(ph * scale)

            # Draw scaled pixmap centred inside our rect
            sx = (w - sw) // 2
            sy = (h - sh) // 2
            p.setClipRect(rect)
            p.drawPixmap(sx, sy, sw, sh, px)

            # Subtle dark vignette at top + bottom for polish
            top_grad = QtGui.QLinearGradient(0, 0, 0, h * 0.35)
            top_grad.setColorAt(0, QtGui.QColor(0, 0, 0, 90))
            top_grad.setColorAt(1, QtGui.QColor(0, 0, 0, 0))
            p.fillRect(rect, top_grad)

            bot_grad = QtGui.QLinearGradient(0, h * 0.65, 0, h)
            bot_grad.setColorAt(0, QtGui.QColor(0, 0, 0, 0))
            bot_grad.setColorAt(1, QtGui.QColor(0, 0, 0, 160))
            p.fillRect(rect, bot_grad)
        else:
            # Fallback: draw a gradient swatch using the widget's accent colour
            accent_c = QtGui.QColor(self._accent)
            r2, g2, b2 = accent_c.red(), accent_c.green(), accent_c.blue()
            dark_c   = QtGui.QColor(max(0, r2 - 60), max(0, g2 - 60), max(0, b2 - 60))
            grad = QtGui.QLinearGradient(0, 0, w, h)
            grad.setColorAt(0, dark_c)
            grad.setColorAt(1, accent_c)
            p.fillRect(rect, grad)

            # Widget name label in center
            fn_data = _PREVIEW_FNS.get(self._w_id)
            if fn_data:
                fn_data(p, rect, self._accent)
            else:
                _txt(p, rect, self._w_id, 12, "rgba(255,255,255,0.7)",
                     False, QtCore.Qt.AlignCenter)

        p.end()


# ══════════════════════════════════════════════════════════════════════════════
# Widget Preview Card
# ══════════════════════════════════════════════════════════════════════════════
class WidgetPreviewCard(QtWidgets.QFrame):
    add_clicked = QtCore.pyqtSignal(str, object)

    def __init__(self, w_id: str, name: str, desc: str,
                 size: SlotSize, accent: str, parent=None):
        super().__init__(parent)
        self._id     = w_id
        self._size   = size
        self._added  = False
        self._accent = accent
        self._orig_btn_qss = ""

        self.setFixedSize(_CARD_W, _CARD_H)
        self._apply_card_style(False)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Preview
        canvas = _PreviewCanvas(w_id, accent)
        root.addWidget(canvas)

        # Divider
        div = QtWidgets.QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background: rgba(255,255,255,0.06); border:none;")
        root.addWidget(div)

        # Info
        info = QtWidgets.QWidget()
        info.setStyleSheet("background: transparent;")
        info_lay = QtWidgets.QVBoxLayout(info)
        info_lay.setContentsMargins(14, 10, 14, 12)
        info_lay.setSpacing(3)

        lbl_name = QtWidgets.QLabel(name)
        lbl_name.setStyleSheet(f"color:{_TXT_W}; font-size:13px; font-weight:600; background:transparent;")

        lbl_desc = QtWidgets.QLabel(desc)
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet(f"color:{_TXT_G}; font-size:11px; background:transparent; line-height:1.4;")
        lbl_desc.setMaximumHeight(34)

        self._btn = QtWidgets.QPushButton("＋  Add to home")
        self._btn.setFixedHeight(34)
        self._btn.setCursor(QtCore.Qt.PointingHandCursor)
        self._orig_btn_qss = f"""
            QPushButton {{
                background: rgba(255,255,255,0.07);
                color: {_TXT_W};
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 10px;
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton:hover   {{ background: {accent}; border-color: {accent}; color: #FFF; }}
            QPushButton:pressed {{ background: {accent}99; }}
        """
        self._btn.setStyleSheet(self._orig_btn_qss)
        self._btn.clicked.connect(lambda: self.add_clicked.emit(self._id, self._size))

        info_lay.addWidget(lbl_name)
        info_lay.addWidget(lbl_desc)
        info_lay.addStretch()
        info_lay.addWidget(self._btn)

        root.addWidget(info)

    def _apply_card_style(self, hovered: bool):
        bg = _CARD_HOV if hovered else _CARD_BG
        self.setStyleSheet(f"""
            WidgetPreviewCard {{
                background: {bg};
                border-radius: {_R}px;
                border-top:  1px solid rgba(255,255,255,0.10);
                border-left: 1px solid rgba(255,255,255,0.10);
                border-bottom: 1px solid rgba(0,0,0,0.40);
                border-right:  1px solid rgba(0,0,0,0.40);
            }}
        """)

    def enterEvent(self, e):
        self._apply_card_style(True)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._apply_card_style(False)
        super().leaveEvent(e)

    # ── state ─────────────────────────────────────────────────────────────────
    def mark_added(self):
        self._added = True
        self._btn.setText("✓  Added")
        self._btn.setEnabled(False)
        self._btn.setStyleSheet(f"""
            QPushButton {{
                background: {_GREEN};
                color: #FFF;
                border: none;
                border-radius: 10px;
                font-size: 12px;
                font-weight: 600;
            }}
        """)

    def mark_removed(self):
        self._added = False
        self._btn.setText("＋  Add to home")
        self._btn.setEnabled(True)
        self._btn.setStyleSheet(self._orig_btn_qss)

    def mark_full(self):
        if not self._added:
            self._btn.setText("Grid full")
            self._btn.setEnabled(False)

    def reset_btn(self):
        if not self._added:
            self._btn.setText("＋  Add to home")
            self._btn.setEnabled(True)
            self._btn.setStyleSheet(self._orig_btn_qss)


# ══════════════════════════════════════════════════════════════════════════════
# Category Sidebar
# ══════════════════════════════════════════════════════════════════════════════
class _CategorySidebar(QtWidgets.QWidget):
    selected = QtCore.pyqtSignal(str, object)   # name, filter_set | None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(258)
        self.setStyleSheet(f"""
            _CategorySidebar {{
                background: {_SIDEBAR_BG};
                border-radius: 18px;
                border: 1px solid rgba(255,255,255,0.07);
            }}
        """)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 16, 12, 20)
        root.setSpacing(0)

        # ── Search bar ────────────────────────────────────────────────────────
        search_wrap = QtWidgets.QWidget()
        search_wrap.setFixedHeight(40)
        search_wrap.setStyleSheet("background: transparent;")
        sw_lay = QtWidgets.QHBoxLayout(search_wrap)
        sw_lay.setContentsMargins(0, 0, 0, 0)
        sw_lay.setSpacing(0)

        self._search = QtWidgets.QLineEdit()
        self._search.setPlaceholderText("Search widgets")
        self._search.setFixedHeight(40)
        self._search.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(255,255,255,0.07);
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 20px;
                color: {_TXT_W};
                font-size: 13px;
                padding: 0 40px 0 38px;
            }}
            QLineEdit::placeholder {{ color: {_TXT_G}; }}
            QLineEdit:focus {{
                border-color: rgba(255,255,255,0.22);
                background: rgba(255,255,255,0.10);
            }}
        """)

        # Search icon overlay
        lbl_mag = QtWidgets.QLabel("🔍")
        lbl_mag.setFixedSize(38, 40)
        lbl_mag.setStyleSheet("background:transparent; font-size:14px;")
        lbl_mag.setAlignment(QtCore.Qt.AlignCenter)

        lbl_mic = QtWidgets.QLabel("🎤")
        lbl_mic.setFixedSize(38, 40)
        lbl_mic.setStyleSheet("background:transparent; font-size:12px;")
        lbl_mic.setAlignment(QtCore.Qt.AlignCenter)
        lbl_mic.setCursor(QtCore.Qt.PointingHandCursor)

        # Stack them via a container with absolute positioning
        container = QtWidgets.QWidget()
        container.setFixedHeight(40)
        container.setStyleSheet("background:transparent;")
        c_lay = QtWidgets.QHBoxLayout(container)
        c_lay.setContentsMargins(0, 0, 0, 0)
        c_lay.setSpacing(0)
        c_lay.addWidget(self._search)

        # Place icons as overlays
        lbl_mag.setParent(container)
        lbl_mag.move(0, 0)
        lbl_mic.setParent(container)

        root.addWidget(container)
        root.addSpacing(14)

        # Position mic icon after resize
        self._lbl_mic = lbl_mic
        self._container = container

        # ── Category buttons ──────────────────────────────────────────────────
        self._btns: List[QtWidgets.QPushButton] = []
        for name, filt in CATEGORIES:
            btn = QtWidgets.QPushButton(name)
            btn.setFixedHeight(38)
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.setProperty("catname", name)
            btn.setProperty("catfilt", None)
            btn.clicked.connect(lambda _, n=name, f=filt: self._select(n, f))
            self._btns.append(btn)
            root.addWidget(btn)
            root.addSpacing(2)

        root.addStretch()

        # Default selection
        self._select(CATEGORIES[0][0], CATEGORIES[0][1])

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._lbl_mic.move(self._container.width() - 38, 0)

    def _select(self, name: str, filt):
        self._active = name
        for btn in self._btns:
            is_sel = btn.text() == name
            if is_sel:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {_SEL_BG};
                        color: {_SEL_FG};
                        border: none;
                        border-radius: {_PILL_R}px;
                        font-size: 14px;
                        font-weight: 700;
                        text-align: left;
                        padding-left: 18px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        color: {_PILL_FG};
                        border: none;
                        border-radius: {_PILL_R}px;
                        font-size: 14px;
                        font-weight: 400;
                        text-align: left;
                        padding-left: 18px;
                    }}
                    QPushButton:hover {{
                        background: rgba(255,255,255,0.07);
                        color: {_TXT_W};
                    }}
                """)
        self.selected.emit(name, filt)


# ══════════════════════════════════════════════════════════════════════════════
# Widget Manager Modal
# ══════════════════════════════════════════════════════════════════════════════
class WidgetManagerPanel(QtWidgets.QWidget):
    def __init__(self, grid: "SnapGridManager", factory,
                 parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self._grid    = grid
        self._factory = factory
        self._cards:  Dict[str, WidgetPreviewCard] = {}
        self._cur_filt: Optional[Set[str]] = None
        self.main_window = parent

        self._build()
        self._refresh_grid(None)
        grid.capacity_changed.connect(self._on_capacity)

    # ── construction ──────────────────────────────────────────────────────────
    def _build(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(44, 36, 44, 36)
        root.setSpacing(24)

        # ── Header row ────────────────────────────────────────────────────────
        hdr = QtWidgets.QHBoxLayout()
        lbl_title = QtWidgets.QLabel("Widget Library")
        lbl_title.setStyleSheet(
            f"color:{_TXT_W}; font-size:34px; font-weight:800; background:transparent;")

        btn_arrange = QtWidgets.QPushButton("⊞   Arrange Layout")
        btn_arrange.setFixedHeight(42)
        btn_arrange.setCursor(QtCore.Qt.PointingHandCursor)
        btn_arrange.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255,255,255,0.09);
                color: {_TXT_W};
                border: 1px solid rgba(255,255,255,0.14);
                border-radius: 21px;
                font-size: 14px;
                font-weight: 500;
                padding: 0 22px;
            }}
            QPushButton:hover   {{ background: rgba(255,255,255,0.16); }}
            QPushButton:pressed {{ background: rgba(255,255,255,0.05); }}
        """)

        btn_close = QtWidgets.QPushButton("✕")
        btn_close.setFixedSize(40, 40)
        btn_close.setCursor(QtCore.Qt.PointingHandCursor)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255,255,255,0.08);
                color: {_TXT_G};
                border: none;
                border-radius: 20px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover   {{ background: rgba(220,38,38,0.65); color:#FFF; }}
            QPushButton:pressed {{ background: rgba(185,28,28,0.80); }}
        """)
        btn_close.clicked.connect(self._close_panel)

        hdr.addWidget(lbl_title)
        hdr.addStretch()
        hdr.addWidget(btn_arrange)
        hdr.addSpacing(12)
        hdr.addWidget(btn_close)
        root.addLayout(hdr)

        # ── Content (sidebar + grid) ──────────────────────────────────────────
        content = QtWidgets.QHBoxLayout()
        content.setSpacing(24)

        self._sidebar = _CategorySidebar()
        self._sidebar.selected.connect(self._on_category)
        content.addWidget(self._sidebar)

        # Scroll area
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: rgba(255,255,255,0.03);
                width: 5px;
                margin: 4px 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,0.18);
                border-radius: 2px;
                min-height: 24px;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical { height: 0; }
        """)

        self._grid_container = QtWidgets.QWidget()
        self._grid_container.setStyleSheet("background: transparent;")
        self._grid_lay = QtWidgets.QGridLayout(self._grid_container)
        self._grid_lay.setSpacing(16)
        self._grid_lay.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)

        scroll.setWidget(self._grid_container)
        content.addWidget(scroll, 1)
        root.addLayout(content, 1)

    def _close_panel(self):
        if hasattr(self.main_window, '_main_stack'):
            self.main_window._main_stack.setCurrentIndex(0)

    # ── population ────────────────────────────────────────────────────────────
    def _refresh_grid(self, filter_set: Optional[Set[str]], override_cols: int = None):
        self._cur_filt = filter_set
        cols_count = override_cols if override_cols is not None else getattr(self, '_last_cols', _COLS)

        # Hide all first
        for card in self._cards.values():
            self._grid_lay.removeWidget(card)
            card.hide()

        col, row = 0, 0
        for w_id, name, desc, size, accent in CATALOG:
            if filter_set is not None and w_id not in filter_set:
                continue

            if w_id not in self._cards:
                card = WidgetPreviewCard(w_id, name, desc, size, accent)
                card.add_clicked.connect(self._on_add)
                self._cards[w_id] = card

            card = self._cards[w_id]
            # Sync added/not-added state
            if w_id in self._grid._reg:
                card.mark_added()
            else:
                card.mark_removed()

            self._grid_lay.addWidget(card, row, col)
            card.show()
            col += 1
            if col >= cols_count:
                col = 0
                row += 1

    def _on_category(self, name: str, filt):
        self._refresh_grid(filt)

    def _on_add(self, w_id: str, size: SlotSize):
        if not self._grid.can_fit(size):
            return
        widget = self._factory(w_id, size)
        if widget and self._grid.add_widget(widget):
            if w_id in self._cards:
                self._cards[w_id].mark_added()

    def _on_capacity(self, used: int, total: int):
        full = used >= total
        for w_id, card in self._cards.items():
            if w_id in self._grid._reg:
                card.mark_added()
            elif full:
                card.mark_removed()
                card.mark_full()
            else:
                card.mark_removed()

    # ── painting ──────────────────────────────────────────────────────────────
    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        # Full dark backdrop
        p.fillRect(self.rect(), _MOD_DARK)

        # Purple atmosphere (top-right corner, matching desktop)
        w, h = self.width(), self.height()
        for cx, cy, rad, r, g, b, a in [
            (0.82, 0.08, 0.32, 130, 50, 220, 55),
            (0.70, 0.03, 0.20,  70, 30, 180, 38),
            (0.50, 0.80, 0.25,  80, 20, 140, 22),
        ]:
            gr = QtGui.QRadialGradient(w * cx, h * cy, w * rad)
            gr.setColorAt(0, QtGui.QColor(r, g, b, a))
            gr.setColorAt(1, QtGui.QColor(0, 0, 0, 0))
            p.fillRect(self.rect(), gr)

        p.end()

    def keyPressEvent(self, e):
        if e.key() == QtCore.Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(e)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        # Calculate available width for the grid:
        # window width - margins (88) - sidebar (258) - spacing (24)
        avail = self.width() - 88 - 258 - 24
        cols = max(1, avail // (_CARD_W + 16))
        if cols != getattr(self, '_last_cols', 0):
            self._last_cols = cols
            self._refresh_grid(self._cur_filt, cols)
