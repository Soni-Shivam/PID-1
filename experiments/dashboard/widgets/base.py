from core.qt_compat import QtCore, QtGui, QtWidgets

class BaseCard(QtWidgets.QFrame):
    """Base class for all widgets. Supports dragging to swap via layout manager."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            BaseCard {
                background-color: rgba(26, 26, 32, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 20px;
            }
        """)
        self._drag_start_pos = None

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not self._drag_start_pos:
            return
            
        if (event.pos() - self._drag_start_pos).manhattanLength() > QtWidgets.QApplication.startDragDistance():
            # Find the TilingGridWidget parent
            p = self.parent()
            while p and not hasattr(p, 'start_drag'):
                p = p.parent()
                
            if p and hasattr(p, 'start_drag'):
                p.start_drag(self)
                self._drag_start_pos = None
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_start_pos = None
        super().mouseReleaseEvent(event)
