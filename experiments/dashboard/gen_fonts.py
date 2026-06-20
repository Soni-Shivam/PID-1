import sys, os
sys.path.append(os.path.abspath('../../src'))
from core.qt_compat import QtCore, QtGui, QtWidgets
from state import DashboardState

# App must be created before fonts
app = QtWidgets.QApplication(sys.argv)

font_name = sys.argv[1]
out_file = sys.argv[2]

# Force the font on the entire application!
font = QtGui.QFont(font_name)
font.setStyleStrategy(QtGui.QFont.PreferAntialias)
app.setFont(font)

# Now import and instantiate dashboard
from main import DesktopDashboard
state = DashboardState()
dash = DesktopDashboard(state)

# Wipe out the explicit stylesheet font in DesktopDashboard so it inherits the app font
dash.setStyleSheet("DesktopDashboard { background: #121212; }")

dash.resize(1920, 1080)
dash.show()

QtCore.QTimer.singleShot(500, app.quit)
app.exec_()

px = dash.grab()
px.save(out_file)
print(f"Saved {out_file} with actual global font {font_name}")
