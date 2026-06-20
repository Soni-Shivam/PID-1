import os
import sys

# We add core to sys.path in main.py, but utils can assume qt_compat is available
from core.qt_compat import QtGui

MODERN_FONT_STACK = "'Century Gothic', 'Tw Cen MT', 'Futura', 'Outfit', 'Inter', 'Roboto', sans-serif"

# Assume icons are located in experiments/icons
ICONS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "icons"))

def get_icon(name):
    return QtGui.QIcon(os.path.join(ICONS_DIR, f"{name}.svg"))

def get_icon_path(name):
    return os.path.join(ICONS_DIR, f"{name}.svg")
