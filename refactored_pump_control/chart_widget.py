from PyQt5 import QtWidgets, QtCore, QtGui

class ProfileChartWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(150)
        self.setBackgroundRole(QtGui.QPalette.Base)
        self.setAutoFillBackground(True)
        
        self.ideal_points = [] # List of (time, rate)
        self.actual_points = [] # List of (time, rate)
        self.total_duration = 1.0
        self.max_rate = 1.0
        self.current_time = 0.0

    def reset(self, profile):
        self.total_duration = max(0.1, profile.total_duration())
        self.ideal_points = []
        self.actual_points = []
        self.current_time = 0.0
        
        # Pre-calculate ideal trace
        steps = 200
        max_r = 0.1
        for i in range(steps + 1):
            t = (i / steps) * self.total_duration
            r = profile.get_ideal_rate_at(t)
            self.ideal_points.append((t, r))
            if r > max_r: max_r = r
        
        self.max_rate = max_r * 1.2 # padding
        self.update()

    def update_cursor(self, current_time):
        self.current_time = current_time
        self.update()

    def append_actual_rate(self, current_time, actual_rate):
        self.actual_points.append((current_time, actual_rate))
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        w = self.width()
        h = self.height()
        padding = 30

        # Scale helpers
        def scale_x(t): return padding + (t / self.total_duration) * (w - 2 * padding)
        def scale_y(r): return h - padding - (r / self.max_rate) * (h - 2 * padding)

        # Draw Grid/Axes
        painter.setPen(QtGui.QPen(QtCore.Qt.lightGray, 1, QtCore.Qt.DashLine))
        painter.drawLine(padding, h - padding, w - padding, h - padding) # X axis
        painter.drawLine(padding, padding, padding, h - padding) # Y axis

        # Draw Ideal Trace (Blue line)
        if len(self.ideal_points) > 1:
            path = QtGui.QPainterPath()
            path.moveTo(scale_x(self.ideal_points[0][0]), scale_y(self.ideal_points[0][1]))
            for t, r in self.ideal_points[1:]:
                path.lineTo(scale_x(t), scale_y(r))
            painter.setPen(QtGui.QPen(QtCore.Qt.blue, 2))
            painter.drawPath(path)

        # Draw Actual Trace (Red staircase)
        if self.actual_points:
            painter.setPen(QtGui.QPen(QtCore.Qt.red, 2))
            # Step drawing: horizontal then vertical
            last_x, last_y = scale_x(self.actual_points[0][0]), scale_y(self.actual_points[0][1])
            for t, r in self.actual_points[1:]:
                curr_x, curr_y = scale_x(t), scale_y(r)
                painter.drawLine(int(last_x), int(last_y), int(curr_x), int(last_y)) # horizontal
                painter.drawLine(int(curr_x), int(last_y), int(curr_x), int(curr_y)) # vertical
                last_x, last_y = curr_x, curr_y

        # Draw Current Time Cursor
        cursor_x = scale_x(self.current_time)
        painter.setPen(QtGui.QPen(QtCore.Qt.darkGreen, 1))
        painter.drawLine(int(cursor_x), padding, int(cursor_x), h - padding)
