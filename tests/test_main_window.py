import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5 import QtWidgets

from refactored_pump_control.main_window import MainWindow


class DummyPanel:
    def __init__(self, session_id, connected, has_profile):
        self.session = mock.Mock()
        self.session.session_id = session_id
        self.session.is_connected = connected
        self.start_manual_control = mock.Mock()
        self.start_loaded_profile = mock.Mock()
        self.has_loaded_profile = mock.Mock(return_value=has_profile)


class MainWindowGlobalStartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.window = MainWindow()
        self.window.close()

    def test_start_all_pumps_only_starts_connected_panels(self):
        connected_panel = DummyPanel(session_id=1, connected=True, has_profile=True)
        disconnected_panel = DummyPanel(session_id=2, connected=False, has_profile=True)

        self.window.session_panels = {
            connected_panel.session: connected_panel,
            disconnected_panel.session: disconnected_panel,
        }
        self.window.sessions = [connected_panel.session, disconnected_panel.session]

        self.window.handle_start_all_pumps()

        connected_panel.start_manual_control.assert_called_once_with()
        disconnected_panel.start_manual_control.assert_not_called()

    def test_start_all_profiles_uses_profile_when_available(self):
        profile_panel = DummyPanel(session_id=1, connected=True, has_profile=True)
        manual_panel = DummyPanel(session_id=2, connected=True, has_profile=False)

        self.window.session_panels = {
            profile_panel.session: profile_panel,
            manual_panel.session: manual_panel,
        }
        self.window.sessions = [profile_panel.session, manual_panel.session]

        with mock.patch("refactored_pump_control.main_window.QtWidgets.QMessageBox.information"):
            self.window.handle_start_all_profiles()

        profile_panel.start_loaded_profile.assert_called_once_with()
        manual_panel.start_manual_control.assert_called_once_with()

    def test_start_all_profiles_reports_manual_fallback_sessions(self):
        profile_panel = DummyPanel(session_id=1, connected=True, has_profile=True)
        manual_panel = DummyPanel(session_id=3, connected=True, has_profile=False)

        self.window.session_panels = {
            profile_panel.session: profile_panel,
            manual_panel.session: manual_panel,
        }
        self.window.sessions = [profile_panel.session, manual_panel.session]

        with mock.patch("refactored_pump_control.main_window.QtWidgets.QMessageBox.information") as info_box:
            self.window.handle_start_all_profiles()

        info_box.assert_called_once()
        message_text = info_box.call_args[0][2]
        self.assertIn("Pump Session 3", message_text)
        self.assertIn("manual control", message_text)

    def test_panel_helpers_drive_existing_session_paths(self):
        session = mock.Mock()
        session.session_id = 7
        session.is_connected = True
        session.connection_changed = mock.Mock()
        session.status_updated = mock.Mock()
        session.syringe_synced = mock.Mock()
        session.error_occurred = mock.Mock()
        session.profile_progress = mock.Mock()
        session.rate_acknowledged = mock.Mock()
        session.profile_status = mock.Mock()
        session.profile_finished = mock.Mock()

        for signal_name in [
            "connection_changed",
            "status_updated",
            "syringe_synced",
            "error_occurred",
            "profile_progress",
            "rate_acknowledged",
            "profile_status",
            "profile_finished",
        ]:
            getattr(session, signal_name).connect = mock.Mock()

        with mock.patch(
            "refactored_pump_control.pump_panel_widget.SerialTransport.list_available_ports",
            return_value=[],
        ):
            from refactored_pump_control.pump_panel_widget import PumpPanelWidget

            panel = PumpPanelWidget(session)

        panel.rate_spin.setValue(12.5)
        panel.unit_combo.setCurrentText("ml/h")
        panel.dir_combo.setCurrentText("withdraw")

        panel.start_manual_control()

        session.set_rate.assert_called_once_with(12.5, "ml/h", "withdraw")
        session.run.assert_called_once_with("withdraw")
        self.assertFalse(panel.has_loaded_profile())


if __name__ == "__main__":
    unittest.main()
