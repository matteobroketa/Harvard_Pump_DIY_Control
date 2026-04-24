from PyQt5 import QtWidgets, QtCore, QtGui
from .serial_transport import SerialTransport
from .profile_model import PumpProfile, HoldSegment, RampSegment, RampPolicy
from .chart_widget import ProfileChartWidget

class PumpPanelWidget(QtWidgets.QFrame):
    remove_requested = QtCore.pyqtSignal(object) # emits self

    def __init__(self, session):
        super().__init__()
        self.session = session
        self.profile = PumpProfile()
        self.setFrameStyle(QtWidgets.QFrame.StyledPanel | QtWidgets.QFrame.Raised)
        self.setLineWidth(2)
        
        self.init_ui()
        self.wire_signals()
        self.update_ui_state(False)

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # ... (Header and Manual/Sync same as before)
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.addWidget(QtWidgets.QLabel(f"<b>Pump Session {self.session.session_id}</b>"))
        
        self.port_combo = QtWidgets.QComboBox()
        self.port_combo.addItems(SerialTransport.list_available_ports())
        header_layout.addWidget(QtWidgets.QLabel("Port:"))
        header_layout.addWidget(self.port_combo)
        
        self.addr_input = QtWidgets.QLineEdit("00")
        self.addr_input.setFixedWidth(30)
        header_layout.addWidget(QtWidgets.QLabel("Addr:"))
        header_layout.addWidget(self.addr_input)
        
        self.connect_btn = QtWidgets.QPushButton("Connect")
        self.connect_btn.clicked.connect(self.handle_connect_toggle)
        header_layout.addWidget(self.connect_btn)
        
        self.remove_btn = QtWidgets.QPushButton("X")
        self.remove_btn.setFixedWidth(25)
        self.remove_btn.setStyleSheet("color: red; font-weight: bold;")
        self.remove_btn.clicked.connect(lambda: self.remove_requested.emit(self))
        header_layout.addWidget(self.remove_btn)
        
        layout.addLayout(header_layout)

        mid_layout = QtWidgets.QHBoxLayout()
        sync_box = QtWidgets.QGroupBox("Syringe Sync")
        sync_layout = QtWidgets.QFormLayout(sync_box)
        self.sync_btn = QtWidgets.QPushButton("Get from Pump")
        self.sync_btn.clicked.connect(self.session.sync_syringe)
        sync_layout.addRow(self.sync_btn)
        self.mfg_field = QtWidgets.QLineEdit(); self.mfg_field.setReadOnly(True)
        sync_layout.addRow("Mfg:", self.mfg_field)
        self.model_field = QtWidgets.QLineEdit(); self.model_field.setReadOnly(True)
        sync_layout.addRow("Model:", self.model_field)
        self.dia_field = QtWidgets.QLineEdit(); self.dia_field.setReadOnly(True)
        sync_layout.addRow("Dia:", self.dia_field)
        mid_layout.addWidget(sync_box)

        manual_box = QtWidgets.QGroupBox("Manual Control")
        manual_layout = QtWidgets.QGridLayout(manual_box)
        self.rate_spin = QtWidgets.QDoubleSpinBox(); self.rate_spin.setRange(0, 999999); self.rate_spin.setDecimals(4)
        manual_layout.addWidget(QtWidgets.QLabel("Rate:"), 0, 0); manual_layout.addWidget(self.rate_spin, 0, 1)
        self.unit_combo = QtWidgets.QComboBox(); self.unit_combo.addItems(["ul/h", "ul/m", "ml/h", "ml/m"])
        manual_layout.addWidget(self.unit_combo, 0, 2)
        self.dir_combo = QtWidgets.QComboBox(); self.dir_combo.addItems(["infuse", "withdraw"])
        manual_layout.addWidget(QtWidgets.QLabel("Dir:"), 1, 0); manual_layout.addWidget(self.dir_combo, 1, 1, 1, 2)
        
        self.set_rate_btn = QtWidgets.QPushButton("Set Rate"); self.set_rate_btn.clicked.connect(self.handle_set_rate)
        manual_layout.addWidget(self.set_rate_btn, 2, 0, 1, 3)
        self.run_btn = QtWidgets.QPushButton("Run"); self.run_btn.clicked.connect(self.handle_run)
        manual_layout.addWidget(self.run_btn, 3, 0)
        self.stop_btn = QtWidgets.QPushButton("Stop"); self.stop_btn.clicked.connect(self.session.stop)
        manual_layout.addWidget(self.stop_btn, 3, 1)
        self.refresh_btn = QtWidgets.QPushButton("Refresh"); self.refresh_btn.clicked.connect(self.session.refresh_status)
        manual_layout.addWidget(self.refresh_btn, 3, 2)
        mid_layout.addWidget(manual_box)

        status_box = QtWidgets.QGroupBox("Status")
        status_layout = QtWidgets.QVBoxLayout(status_box)
        self.state_label = QtWidgets.QLabel("State: Unknown")
        status_layout.addWidget(self.state_label)
        self.rate_label = QtWidgets.QLabel("Rate: ---")
        status_layout.addWidget(self.rate_label)
        status_layout.addStretch()
        mid_layout.addWidget(status_box)
        layout.addLayout(mid_layout)

        # --- Profile Sub-panel ---
        self.profile_box = QtWidgets.QGroupBox("Profile Engine")
        profile_vlayout = QtWidgets.QVBoxLayout(self.profile_box)
        
        self.toggle_btn = QtWidgets.QPushButton("[-] Minimize Profile Engine")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.clicked.connect(self.toggle_profile_engine)
        profile_vlayout.addWidget(self.toggle_btn)
        
        self.profile_content = QtWidgets.QWidget()
        profile_main_layout = QtWidgets.QVBoxLayout(self.profile_content)
        profile_vlayout.addWidget(self.profile_content)
        
        top_prof_layout = QtWidgets.QHBoxLayout()
        # Profile List
        plist_layout = QtWidgets.QVBoxLayout()
        self.seg_table = QtWidgets.QTableWidget(0, 5)
        self.seg_table.setHorizontalHeaderLabels(["Type", "Start Rate", "End Rate", "Dur (s)", "Dir"])
        self.seg_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.seg_table.itemChanged.connect(self.handle_table_edit)
        plist_layout.addWidget(self.seg_table)
        
        abtn_layout = QtWidgets.QHBoxLayout()
        self.add_hold_btn = QtWidgets.QPushButton("Add Hold"); self.add_hold_btn.clicked.connect(self.handle_add_hold)
        self.add_ramp_btn = QtWidgets.QPushButton("Add Ramp"); self.add_ramp_btn.clicked.connect(self.handle_add_ramp)
        self.del_row_btn = QtWidgets.QPushButton("Delete Selected"); self.del_row_btn.clicked.connect(self.handle_delete_row)
        self.clear_prof_btn = QtWidgets.QPushButton("Clear"); self.clear_prof_btn.clicked.connect(self.handle_clear_profile)
        abtn_layout.addWidget(self.add_hold_btn); abtn_layout.addWidget(self.add_ramp_btn); abtn_layout.addWidget(self.del_row_btn); abtn_layout.addWidget(self.clear_prof_btn)
        plist_layout.addLayout(abtn_layout)
        top_prof_layout.addLayout(plist_layout, 2)
        
        # Profile Control & Policy
        pctrl_layout = QtWidgets.QVBoxLayout()
        policy_box = QtWidgets.QGroupBox("Ramp Policy")
        pol_layout = QtWidgets.QFormLayout(policy_box)
        self.pol_mode = QtWidgets.QComboBox(); self.pol_mode.addItems(["stepped_fine", "stepped_adaptive", "stepped_coarse", "custom"])
        self.pol_mode.setCurrentText("stepped_adaptive")
        self.pol_mode.currentTextChanged.connect(self.handle_policy_change)
        pol_layout.addRow("Mode:", self.pol_mode)
        self.pol_interval = QtWidgets.QSpinBox(); self.pol_interval.setRange(50, 5000); self.pol_interval.setSuffix("ms")
        self.pol_delta = QtWidgets.QDoubleSpinBox(); self.pol_delta.setRange(0.0001, 10.0); self.pol_delta.setDecimals(4)
        self.pol_hz = QtWidgets.QDoubleSpinBox(); self.pol_hz.setRange(0.1, 20.0); self.pol_hz.setDecimals(1)
        self.pol_div = QtWidgets.QDoubleSpinBox(); self.pol_div.setRange(0.001, 10.0); self.pol_div.setDecimals(3)
        pol_layout.addRow("Interval:", self.pol_interval)
        pol_layout.addRow("Min Delta:", self.pol_delta)
        pol_layout.addRow("Max Hz:", self.pol_hz)
        pol_layout.addRow("Max Div:", self.pol_div)
        
        pctrl_layout.addWidget(policy_box)
        
        self.estimate_label = QtWidgets.QLabel("Est. Commands: 0")
        pctrl_layout.addWidget(self.estimate_label)
        self.tail_label = QtWidgets.QLabel("Tail: ---")
        self.tail_label.setStyleSheet("color: blue; font-style: italic;")
        pctrl_layout.addWidget(self.tail_label)
        
        self.handle_policy_change() # Init values

        file_layout = QtWidgets.QHBoxLayout()
        self.save_btn = QtWidgets.QPushButton("Save"); self.save_btn.clicked.connect(self.handle_save_profile)
        self.load_btn = QtWidgets.QPushButton("Load"); self.load_btn.clicked.connect(self.handle_load_profile)
        file_layout.addWidget(self.save_btn); file_layout.addWidget(self.load_btn)
        pctrl_layout.addLayout(file_layout)

        self.start_prof_btn = QtWidgets.QPushButton("START Profile"); self.start_prof_btn.clicked.connect(self.handle_start_profile)
        pctrl_layout.addWidget(self.start_prof_btn)
        self.stop_prof_btn = QtWidgets.QPushButton("STOP"); self.stop_prof_btn.clicked.connect(self.session.stop_profile)
        pctrl_layout.addWidget(self.stop_prof_btn)
        
        top_prof_layout.addLayout(pctrl_layout, 1)
        profile_main_layout.addLayout(top_prof_layout)

        # --- Charting ---
        self.chart = ProfileChartWidget()
        profile_main_layout.addWidget(self.chart)
        
        self.progress_bar = QtWidgets.QProgressBar()
        profile_main_layout.addWidget(self.progress_bar)
        
        self.live_stats = QtWidgets.QLabel("Ideal: 0.00 | Actual: 0.00 | Div: 0.00")
        profile_main_layout.addWidget(self.live_stats)

        layout.addWidget(self.profile_box)

    def handle_policy_change(self):
        mode = self.pol_mode.currentText()
        self.profile.policy.mode = mode
        if mode != "custom":
            self.profile.policy.apply_preset(mode)
            # Disable inputs for presets
            for w in [self.pol_interval, self.pol_delta, self.pol_hz, self.pol_div]: w.setEnabled(False)
        else:
            for w in [self.pol_interval, self.pol_delta, self.pol_hz, self.pol_div]: w.setEnabled(True)
        
        # Sync UI with policy values
        self.pol_interval.blockSignals(True)
        self.pol_delta.blockSignals(True)
        self.pol_hz.blockSignals(True)
        self.pol_div.blockSignals(True)
        
        self.pol_interval.setValue(int(self.profile.policy.interval_ms))
        self.pol_delta.setValue(self.profile.policy.min_delta)
        self.pol_hz.setValue(self.profile.policy.max_hz)
        self.pol_div.setValue(self.profile.policy.max_divergence)
        
        self.pol_interval.blockSignals(False)
        self.pol_delta.blockSignals(False)
        self.pol_hz.blockSignals(False)
        self.pol_div.blockSignals(False)
        
        self.update_estimate()

    def update_policy_from_ui(self):
        if self.pol_mode.currentText() == "custom":
            self.profile.policy.interval_ms = self.pol_interval.value()
            self.profile.policy.min_delta = self.pol_delta.value()
            self.profile.policy.max_hz = self.pol_hz.value()
            self.profile.policy.max_divergence = self.pol_div.value()
        self.update_estimate()

    def update_estimate(self):
        # Very rough estimate
        total_cmds = len(self.profile.segments) # start of each seg
        for seg in self.profile.segments:
            if seg.type == "ramp":
                # Max commands based on interval vs duration
                max_ticks = (seg.duration * 1000) / max(1, self.profile.policy.interval_ms)
                total_cmds += min(max_ticks, seg.duration * self.profile.policy.max_hz)
        self.estimate_label.setText(f"Est. Max Commands: {int(total_cmds)}")

    def wire_signals(self):
        self.session.connection_changed.connect(self.update_ui_state)
        self.session.status_updated.connect(self.update_status_display)
        self.session.syringe_synced.connect(self.update_syringe_display)
        self.session.error_occurred.connect(lambda msg: QtWidgets.QMessageBox.warning(self, "Pump Error", msg))
        
        self.session.profile_progress.connect(self.update_profile_progress)
        self.session.rate_acknowledged.connect(self.chart.append_actual_rate)
        self.session.profile_status.connect(self.handle_profile_status)
        self.session.profile_finished.connect(self.handle_profile_finished)
        
        for w in [self.pol_interval, self.pol_delta, self.pol_hz, self.pol_div]:
            w.valueChanged.connect(self.update_policy_from_ui)

    def handle_start_profile(self):
        if not self.profile.segments: return
        self.chart.reset(self.profile)
        self.session.start_profile(self.profile)

    def update_profile_progress(self, seg_index, seg_elapsed, total_elapsed, ideal_r, actual_r):
        self.chart.update_cursor(total_elapsed)
        self.live_stats.setText(f"Ideal: {ideal_r:.3f} | Actual: {actual_r:.3f} | Div: {abs(ideal_r-actual_r):.3f}")
        
        total_dur = self.profile.total_duration()
        if total_dur > 0:
            self.progress_bar.setValue(int((total_elapsed / total_dur) * 100))
        
        # Highlight table row
        for r in range(self.seg_table.rowCount()):
            for c in range(self.seg_table.columnCount()):
                item = self.seg_table.item(r, c)
                if item: item.setBackground(QtGui.QColor("yellow") if r == seg_index else QtGui.QColor("white"))

    # ... (Rest of handlers: set_rate, run, save/load, add_hold/ramp, refresh_profile_table, same as Phase 4 but calling update_estimate)
    def get_profile_tail_state(self):
        """Returns (rate, units, direction) for the next segment to maintain continuity."""
        if not self.profile.segments:
            return self.rate_spin.value(), self.unit_combo.currentText(), self.dir_combo.currentText()
        
        last = self.profile.segments[-1]
        if last.type == "hold":
            return last.rate, last.units, last.direction
        else: # ramp
            return last.end_rate, last.units, last.direction

    def handle_add_hold(self):
        tail_rate, tail_units, tail_dir = self.get_profile_tail_state()
        
        rate, ok1 = QtWidgets.QInputDialog.getDouble(self, "Hold Rate", f"Rate ({tail_units}):", tail_rate, 0, 999999, 4)
        if not ok1: return
        
        duration, ok2 = QtWidgets.QInputDialog.getDouble(self, "Hold Duration", "Seconds:", 10.0, 0.1, 100000, 1)
        if ok2:
            seg = HoldSegment(rate, tail_units, duration, tail_dir)
            self.profile.add_segment(seg)
            self.refresh_profile_table()
            self.update_estimate()
            self.chart.reset(self.profile)

    def handle_add_ramp(self):
        tail_rate, tail_units, tail_dir = self.get_profile_tail_state()
        
        # Start rate defaults from tail, but we prompt just in case they want a jump
        start_rate, ok1 = QtWidgets.QInputDialog.getDouble(self, "Ramp Start Rate", f"Start Rate ({tail_units}):", tail_rate, 0, 999999, 4)
        if not ok1: return

        end_rate, ok2 = QtWidgets.QInputDialog.getDouble(self, "Ramp End Rate", f"Target Rate ({tail_units}):", tail_rate * 2, 0, 999999, 4)
        if not ok2: return
        
        duration, ok3 = QtWidgets.QInputDialog.getDouble(self, "Ramp Duration", "Seconds:", 10.0, 0.1, 100000, 1)
        if ok3:
            seg = RampSegment(start_rate, end_rate, tail_units, duration, tail_dir)
            self.profile.add_segment(seg)
            self.refresh_profile_table()
            self.update_estimate()
            self.chart.reset(self.profile)

    def toggle_profile_engine(self):
        if self.toggle_btn.isChecked():
            self.profile_content.hide()
            self.toggle_btn.setText("[+] Expand Profile Engine")
        else:
            self.profile_content.show()
            self.toggle_btn.setText("[-] Minimize Profile Engine")

    def handle_table_edit(self, item):
        row = item.row()
        col = item.column()
        if row >= len(self.profile.segments): return
        
        seg = self.profile.segments[row]
        val = item.text()
        
        try:
            if col == 1: # Start Rate / Hold Rate
                r = float(val)
                if seg.type == "hold": seg.rate = r
                else: seg.start_rate = r
            elif col == 2: # End Rate
                if seg.type == "ramp": seg.end_rate = float(val)
            elif col == 3: # Duration
                d = float(val)
                if d <= 0: raise ValueError("Duration must be > 0")
                seg.duration = d
            elif col == 4: # Direction
                if val.lower() in ["infuse", "withdraw"]:
                    seg.direction = val.lower()
                else:
                    raise ValueError("Direction must be infuse or withdraw")
            
            self.update_estimate()
            self.chart.reset(self.profile)
            self.refresh_profile_table() # Normalize view
        except ValueError as e:
            QtWidgets.QMessageBox.warning(self, "Invalid Value", f"Error in row {row+1}: {e}")
            self.refresh_profile_table() # Revert view

    def handle_delete_row(self):
        idx = self.seg_table.currentRow()
        if 0 <= idx < len(self.profile.segments):
            self.profile.segments.pop(idx)
            self.refresh_profile_table()
            self.update_estimate()
            self.chart.reset(self.profile)

    def refresh_profile_table(self):
        self.seg_table.blockSignals(True)
        self.seg_table.setRowCount(0)
        for seg in self.profile.segments:
            row = self.seg_table.rowCount()
            self.seg_table.insertRow(row)
            
            type_item = QtWidgets.QTableWidgetItem(seg.type.upper())
            type_item.setFlags(type_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.seg_table.setItem(row, 0, type_item)
            
            if seg.type == "hold":
                self.seg_table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(seg.rate)))
                end_item = QtWidgets.QTableWidgetItem("---")
                end_item.setFlags(end_item.flags() & ~QtCore.Qt.ItemIsEditable)
                self.seg_table.setItem(row, 2, end_item)
            else:
                self.seg_table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(seg.start_rate)))
                self.seg_table.setItem(row, 2, QtWidgets.QTableWidgetItem(str(seg.end_rate)))
            
            self.seg_table.setItem(row, 3, QtWidgets.QTableWidgetItem(str(seg.duration)))
            self.seg_table.setItem(row, 4, QtWidgets.QTableWidgetItem(seg.direction))
        
        self.seg_table.blockSignals(False)
        # Update tail label
        tr, tu, td = self.get_profile_tail_state()
        self.tail_label.setText(f"Tail: {tr:.2f} {tu} {td}")

    def handle_profile_status(self, status):
        self.start_prof_btn.setText(status)
        is_running = any(x in status for x in ["Running", "Paused", "Resuming"])
        self.update_profile_ui_state(is_running)

    def update_profile_ui_state(self, running):
        self.seg_table.setEnabled(not running)
        self.add_hold_btn.setEnabled(not running)
        self.add_ramp_btn.setEnabled(not running)
        self.del_row_btn.setEnabled(not running)
        self.clear_prof_btn.setEnabled(not running)
        self.load_btn.setEnabled(not running)
        self.pol_mode.setEnabled(not running)

    def handle_profile_finished(self):
        self.update_profile_ui_state(False)
        self.progress_bar.setValue(100)
        for r in range(self.seg_table.rowCount()):
            for c in range(self.seg_table.columnCount()):
                item = self.seg_table.item(r, c)
                if item: item.setBackground(QtGui.QColor("white"))

    def handle_connect_toggle(self):
        if self.session.is_connected:
            self.session.disconnect_pump()
        else:
            port = self.port_combo.currentText()
            try:
                addr = int(self.addr_input.text())
                self.session.connect_pump(port, addr)
            except ValueError:
                QtWidgets.QMessageBox.warning(self, "Error", "Invalid Address.")

    def handle_set_rate(self):
        self.session.set_rate(self.rate_spin.value(), self.unit_combo.currentText(), self.dir_combo.currentText())

    def handle_run(self):
        self.session.run(self.dir_combo.currentText())

    def update_status_display(self, status, rate, units):
        self.state_label.setText(f"State: {status}")
        self.rate_label.setText(f"Rate: {rate:.4f} {units}")

    def update_syringe_display(self, info):
        self.mfg_field.setText(info['manufacturer'])
        self.model_field.setText(info['model'])
        self.dia_field.setText(str(info['diameter_mm']))

    def update_ui_state(self, connected):
        self.port_combo.setEnabled(not connected)
        self.addr_input.setEnabled(not connected)
        self.connect_btn.setText("Disconnect" if connected else "Connect")
        self.sync_btn.setEnabled(connected)
        self.set_rate_btn.setEnabled(connected)
        self.run_btn.setEnabled(connected)
        self.stop_btn.setEnabled(connected)
        self.refresh_btn.setEnabled(connected)
        self.start_prof_btn.setEnabled(connected)
        self.stop_prof_btn.setEnabled(connected)

    def handle_clear_profile(self):
        self.profile.segments = []
        self.refresh_profile_table()
        self.update_estimate()
        self.chart.reset(self.profile)

    def handle_save_profile(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Profile", "", "JSON (*.json)")
        if path:
            try:
                self.profile.save_to_file(path)
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Save Failed", str(e))

    def handle_load_profile(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load Profile", "", "JSON (*.json)")
        if path:
            try:
                self.profile = PumpProfile.load_from_file(path)
                # Set UI mode - this will trigger handle_policy_change if it changes
                self.pol_mode.setCurrentText(self.profile.policy.mode)
                # Always call handle_policy_change to ensure UI sync even if mode didn't change
                self.handle_policy_change()
                self.refresh_profile_table()
                self.update_estimate()
                self.chart.reset(self.profile)
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Load Failed", str(e))
