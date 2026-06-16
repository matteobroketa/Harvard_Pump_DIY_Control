import logging
from PyQt5 import QtWidgets, QtCore, QtGui
from .pump_session import PumpSession
from .pump_panel_widget import PumpPanelWidget

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Harvard Ultra Multi-Pump Control")
        self.resize(1000, 800)
        
        self.sessions = []
        self.session_panels = {}
        self.session_counter = 0
        self.logger = logging.getLogger(__name__)

        self.init_ui()

    def init_ui(self):
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QtWidgets.QVBoxLayout(central_widget)

        # --- Top Toolbar ---
        toolbar_layout = QtWidgets.QHBoxLayout()
        
        self.add_pump_btn = QtWidgets.QPushButton("Add Pump Panel")
        self.add_pump_btn.clicked.connect(self.add_pump_panel)
        toolbar_layout.addWidget(self.add_pump_btn)

        self.start_all_btn = QtWidgets.QPushButton("START ALL PUMPS")
        self.start_all_btn.clicked.connect(self.handle_start_all_pumps)
        toolbar_layout.addWidget(self.start_all_btn)

        self.start_all_profiles_btn = QtWidgets.QPushButton("START ALL PROFILES")
        self.start_all_profiles_btn.clicked.connect(self.handle_start_all_profiles)
        toolbar_layout.addWidget(self.start_all_profiles_btn)
        
        self.stop_all_btn = QtWidgets.QPushButton("STOP ALL PUMPS")
        self.stop_all_btn.setStyleSheet("background-color: red; color: white; font-weight: bold; font-size: 14px;")
        self.stop_all_btn.clicked.connect(self.handle_stop_all)
        toolbar_layout.addWidget(self.stop_all_btn)
        
        toolbar_layout.addStretch()
        main_layout.addLayout(toolbar_layout)

        # --- Dashboard Scroll Area ---
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QtWidgets.QWidget()
        self.panels_layout = QtWidgets.QVBoxLayout(self.scroll_content)
        self.panels_layout.addStretch()
        
        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area)

        # Start with one pump panel
        self.add_pump_panel()

    def add_pump_panel(self):
        self.session_counter += 1
        session = PumpSession(self.session_counter)
        self.sessions.append(session)
        
        panel = PumpPanelWidget(session)
        panel.remove_requested.connect(self.remove_pump_panel)
        self.session_panels[session] = panel
        
        # Insert before the stretch
        self.panels_layout.insertWidget(self.panels_layout.count() - 1, panel)

    def remove_pump_panel(self, panel_widget):
        session = panel_widget.session
        if session.is_connected:
            session.disconnect_pump()
        
        self.sessions.remove(session)
        self.session_panels.pop(session, None)
        self.panels_layout.removeWidget(panel_widget)
        panel_widget.deleteLater()

    def handle_start_all_pumps(self):
        for session in self.sessions:
            if not session.is_connected:
                continue

            panel = self.session_panels.get(session)
            if panel is not None:
                panel.start_manual_control()

    def handle_start_all_profiles(self):
        fallback_sessions = []

        for session in self.sessions:
            if not session.is_connected:
                continue

            panel = self.session_panels.get(session)
            if panel is None:
                continue

            if panel.has_loaded_profile():
                panel.start_loaded_profile()
            else:
                panel.start_manual_control()
                fallback_sessions.append(session.session_id)

        if fallback_sessions:
            session_list = ", ".join(f"Pump Session {session_id}" for session_id in fallback_sessions)
            QtWidgets.QMessageBox.information(
                self,
                "Profiles Not Loaded",
                f"{session_list} started using manual control because no profile was loaded.",
            )

    def handle_stop_all(self):
        self.logger.warning("GLOBAL STOP ISSUED")
        for session in self.sessions:
            if session.is_connected:
                session.stop_profile()
                session.stop()
