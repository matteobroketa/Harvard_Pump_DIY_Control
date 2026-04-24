import time
import logging
from PyQt5 import QtCore

class ProfileRunner(QtCore.QThread):
    # index, seg_elapsed, total_elapsed, ideal_rate, actual_rate
    progress_updated = QtCore.pyqtSignal(int, float, float, float, float) 
    rate_acknowledged = QtCore.pyqtSignal(float, float) # total_elapsed, rate
    status_msg = QtCore.pyqtSignal(str)
    segment_started = QtCore.pyqtSignal(int, str)
    finished = QtCore.pyqtSignal()
    aborted = QtCore.pyqtSignal(str)

    def __init__(self, session, profile):
        super().__init__()
        self.session = session
        self.profile = profile
        self.policy = profile.policy
        self._is_running = True
        self._is_paused = False
        self.logger = logging.getLogger(f"ProfileRunner-{session.session_id}")

        self.last_sent_rate = -1.0
        self.last_sent_time = 0.0

    def run(self):
        try:
            self.session.log_execution(f"STARTING PROFILE: {self.profile.name}")
            total_elapsed = 0.0

            for i, segment in enumerate(self.profile.segments):
                if not self._is_running: break
                
                self.session.log_execution(f"Entering Segment {i}: {segment}")
                self.segment_started.emit(i, str(segment))
                
                seg_elapsed = self._execute_segment(segment, i, total_elapsed)
                total_elapsed += segment.duration

            self.session.log_execution("PROFILE COMPLETED")
            self.finished.emit()

        except Exception as e:
            self.session.log_execution(f"CRITICAL ERROR: {e}")
            self.aborted.emit(str(e))

    def _execute_segment(self, segment, seg_index, prev_elapsed):
        start_time = time.time()
        seg_elapsed = 0.0
        
        # Initial segment rate
        ideal_start = segment.rate if segment.type == "hold" else segment.start_rate
        self._safe_set_rate(ideal_start, segment.units, segment.direction, prev_elapsed, force=True)
        self.session.run_fast(segment.direction)

        while seg_elapsed < segment.duration:
            if not self._is_running: break
            self._handle_pause()

            seg_elapsed = time.time() - start_time
            ideal_rate = segment.get_ideal_rate(seg_elapsed)
            
            # Divergence check: if we are too far from ideal, force a set_rate
            divergence = abs(ideal_rate - self.last_sent_rate)
            should_force = divergence > self.policy.max_divergence
            
            if segment.type == "ramp" or should_force:
                self._safe_set_rate(ideal_rate, segment.units, segment.direction, prev_elapsed + seg_elapsed, force=should_force)
            
            self.progress_updated.emit(seg_index, seg_elapsed, prev_elapsed + seg_elapsed, ideal_rate, self.last_sent_rate)
            
            time.sleep(self.policy.interval_ms / 1000.0)
            seg_elapsed = time.time() - start_time

        if self._is_running:
            ideal_end = segment.rate if segment.type == "hold" else segment.end_rate
            self._safe_set_rate(ideal_end, segment.units, segment.direction, prev_elapsed + seg_elapsed, force=True)
            
        return seg_elapsed

    def _safe_set_rate(self, rate, units, direction, current_total_time, force=False):
        now = time.time()
        
        delta = abs(rate - self.last_sent_rate)
        min_spacing = 1.0 / self.policy.max_hz
        
        # Skip if delta is too small AND we aren't forcing
        if not force and delta < self.policy.min_delta:
            return

        # Throttling
        if not force and (now - self.last_sent_time) < min_spacing:
            return

        try:
            t0 = time.time()
            self.session.set_rate_fast(rate, units, direction)
            latency = (time.time() - t0) * 1000.0
            
            self.last_sent_rate = rate
            self.last_sent_time = now
            self.rate_acknowledged.emit(current_total_time, rate)
            self.session.log_execution(f"RATE SET: {rate:.4f} {units} (Latency: {latency:.1f}ms)")
        except Exception as e:
            self.session.log_execution(f"CMD FAILED: {e}")

    def _handle_pause(self):
        while self._is_paused:
            if not self._is_running: break
            time.sleep(0.1)

    def pause(self):
        self._is_paused = True
        self.status_msg.emit("Paused")

    def resume(self):
        self._is_paused = False
        self.status_msg.emit("Resuming...")

    def stop(self):
        self._is_running = False
        self._is_paused = False
        self.status_msg.emit("Stopping...")
