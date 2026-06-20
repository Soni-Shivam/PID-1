import sys, os
sys.path.append(os.path.abspath('../../src'))
from core.qt_compat import QtCore, QtGui, QtWidgets
from state import DashboardState
from main import DesktopDashboard

app = QtWidgets.QApplication(sys.argv)
out_file = sys.argv[1]

state = DashboardState()
dash = DesktopDashboard(state)

dash.resize(1920, 1080)
dash.show()

# Wait for 500ms to allow paint
QtCore.QTimer.singleShot(500, app.quit)
app.exec_()

px = dash.grab()
px.save(out_file)
print(f"Saved {out_file}")
