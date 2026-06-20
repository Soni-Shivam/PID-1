import sys, os
sys.path.append(os.path.abspath('../../src'))
from core.qt_compat import QtCore, QtGui, QtWidgets
from state import DashboardState
from main import DesktopDashboard

app = QtWidgets.QApplication(sys.argv)
state = DashboardState()
dash = DesktopDashboard(state)
dash.resize(1920, 1080)
# Force layout
dash.show()
# Wait for 500ms
QtCore.QTimer.singleShot(500, app.quit)
app.exec_()
px = dash.grab()
px.save('screenshot_test.png')
print("Saved screenshot_test.png")
