from core.qt_compat import QtCore, QtGui, QtWidgets

class LayoutEngine(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.grid = QtWidgets.QGridLayout(self)
        self.grid.setSpacing(24)
        self.grid.setContentsMargins(0, 0, 0, 0)
        
        self.active_widgets = []
        self.current_template = "Classic"

    def clear_grid(self):
        for w in self.active_widgets:
            self.grid.removeWidget(w)
            w.hide()
            w.setParent(None)
        self.active_widgets.clear()
        
        # Reset stretch factors
        for i in range(10):
            self.grid.setColumnStretch(i, 0)
            self.grid.setRowStretch(i, 0)

    def apply_classic_template(self, widget_instances):
        """Standard 4 column grid layout"""
        self.clear_grid()
        self.current_template = "Classic"
        
        for i in range(4):
            self.grid.setColumnStretch(i, 2)
            
        # Example hardcoded classic positions
        positions = [
            (0, 0, 1, 2), # Focus Timer
            (0, 2, 1, 1), # Weather
            (0, 3, 1, 1), # Music
            (1, 0, 1, 1), # Calendar
            (1, 1, 1, 2), # Activity Graph
            (1, 3, 1, 1)  # System Health
        ]
        
        for i, (row, col, rs, cs) in enumerate(positions):
            if i < len(widget_instances):
                w = widget_instances[i]
                self.grid.addWidget(w, row, col, rs, cs)
                w.show()
                self.active_widgets.append(w)

    def apply_content_first_template(self, hero_widget, right_widgets):
        """Large left hero widget, right vertical stack"""
        self.clear_grid()
        self.current_template = "Content-First"
        
        # 3 columns for hero, 1 for right stack
        self.grid.setColumnStretch(0, 3)
        self.grid.setColumnStretch(1, 1)
        
        self.grid.addWidget(hero_widget, 0, 0, 3, 1)
        hero_widget.show()
        self.active_widgets.append(hero_widget)
        
        for i, w in enumerate(right_widgets):
            if i < 3:
                self.grid.addWidget(w, i, 1, 1, 1)
                w.show()
                self.active_widgets.append(w)
