import logging
import time
from PyQt5 import QtCore
from .harvard_ultra_driver import HarvardUltraDriver
from .transport_manager import TransportManager
from .profile_runner import ProfileRunner

class PumpSession(QtCore.QObject):
    connection_changed = QtCore.pyqtSignal(bool)
    status_updated = QtCore.pyqtSignal(str, float, str) # status, rate, units
    rate_acknowledged = QtCore.pyqtSignal(float, float) # total_elapsed, rate
    syringe_synced = QtCore.pyqtSignal(dict)
    error_occurred = QtCore.pyqtSignal(str)
    
    # seg_index, seg_elapsed, total_elapsed, ideal_rate, actual_rate
    profile_progress = QtCore.pyqtSignal(int, float, float, float, float) 
    profile_status = QtCore.pyqtSignal(str)
    profile_finished = QtCore.pyqtSignal()

    def __init__(self, session_id):
        super().__init__()
        self.session_id = session_id
        self.port = None
        self.address = 0
        self.driver = None
        self.transport = None
        self.is_connected = False
        
        self.runner = None
        self.execution_log = [] # List of strings
        self.log_lock = QtCore.QMutex()
        
        self.syringe_info = {
            'manufacturer': 'Unknown',
            'model': 'Unknown',
            'diameter_mm': 0.0
        }
        self.logger = logging.getLogger(f"PumpSession-{session_id}")

    def log_execution(self, message):
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        self.log_lock.lock()
        self.execution_log.append(entry)
        if len(self.execution_log) > 1000:
            self.execution_log.pop(0)
        self.log_lock.unlock()
        self.logger.info(entry)

    def get_log(self):
        self.log_lock.lock()
        full_log = "\n".join(self.execution_log)
        self.log_lock.unlock()
        return full_log

    def connect_pump(self, port, address):
        self.port = port
        self.address = address
        try:
            tm = TransportManager()
            self.transport = tm.get_transport(port)
            if not self.transport.is_connected():
                self.transport.connect()
            
            self.driver = HarvardUltraDriver(self.transport, address=address)
            
            if self.driver.verify_connection():
                self.is_connected = True
                self.connection_changed.emit(True)
                self.refresh_status()
                return True
            else:
                self.error_occurred.emit("Could not verify pump protocol.")
                return False
        except Exception as e:
            self.is_connected = False
            self.error_occurred.emit(str(e))
            return False

    def disconnect_pump(self):
        self.stop_profile()
        self.is_connected = False
        self.connection_changed.emit(False)
        # We don't necessarily close the transport here 
        # because other sessions might be using it on the same port.

    def sync_syringe(self):
        if not self.is_connected: return
        try:
            self.syringe_info = self.driver.get_syringe_info()
            self.syringe_synced.emit(self.syringe_info)
        except Exception as e:
            self.error_occurred.emit(f"Syringe sync failed: {e}")

    def set_rate(self, rate, units, direction):
        if not self.is_connected: return
        try:
            self.driver.set_rate(rate, units, direction)
            self.refresh_status()
        except Exception as e:
            self.error_occurred.emit(f"Set rate failed: {e}")

    def run(self, direction):
        if not self.is_connected: return
        try:
            self.driver.run(direction)
            self.refresh_status()
        except Exception as e:
            self.error_occurred.emit(f"Run failed: {e}")

    def stop(self):
        if not self.is_connected: return
        try:
            self.driver.stop()
            self.refresh_status()
        except Exception as e:
            self.error_occurred.emit(f"Stop failed: {e}")

    def set_rate_fast(self, rate, units, direction):
        if not self.is_connected: return
        self.driver.set_rate(rate, units, direction)

    def run_fast(self, direction):
        if not self.is_connected: return
        self.driver.run(direction)

    def stop_fast(self):
        if not self.is_connected: return
        self.driver.stop()

    def start_profile(self, profile):
        if not self.is_connected: return
        if self.runner and self.runner.isRunning():
            self.error_occurred.emit("Profile already running.")
            return

        self.runner = ProfileRunner(self, profile)
        self.runner.progress_updated.connect(self.profile_progress.emit)
        self.runner.rate_acknowledged.connect(self.rate_acknowledged.emit)
        self.runner.status_msg.connect(self.profile_status.emit)
        self.runner.finished.connect(self._on_profile_finished)
        self.runner.aborted.connect(lambda msg: self.error_occurred.emit(f"Profile aborted: {msg}"))
        
        self.runner.start()
        self.profile_status.emit("Running Profile...")

    def pause_profile(self):
        if self.runner: self.runner.pause()

    def resume_profile(self):
        if self.runner: self.runner.resume()

    def stop_profile(self):
        if self.runner:
            self.runner.stop()
            self.runner.wait(2000) # Wait for thread to exit
        self.stop()
        self.profile_status.emit("Profile Stopped")

    def _on_profile_finished(self):
        self.stop()
        self.profile_finished.emit()
        self.profile_status.emit("Profile Finished")

    def refresh_status(self):
        if not self.is_connected: return
        try:
            status = self.driver.get_status()
            rate, units = self.driver.get_rate()
            self.status_updated.emit(status, rate if rate else 0.0, units if units else "")
        except Exception as e:
            self.logger.error(f"Status refresh failed: {e}")
