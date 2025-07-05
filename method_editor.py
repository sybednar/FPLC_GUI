#method_editor.py 0.4.9.2
#added monitor settings buttons to add and edit step dialog 

import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidget, QGridLayout,
    QTableWidgetItem, QFileDialog, QDialog, QDialogButtonBox, QSpinBox, QDoubleSpinBox,
    QComboBox, QMessageBox, QCheckBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor, QBrush
from pathlib import Path


DEFAULT_METHOD_DIR = Path("/home/sybednar/FPLC_controller_venv/FPLC_Method_Scripts")
DEFAULT_METHOD_DIR.mkdir(parents=True, exist_ok=True)


class UVMonitorSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("UV Monitor Settings")
        self.setMinimumWidth(300)
        layout = QVBoxLayout()

        self.uv_monitor_combo = QComboBox()
        self.uv_monitor_combo.addItems(["Pharmacia UV MII", "BioRad EM1"])
        layout.addWidget(QLabel("UV Monitor Type:"))
        layout.addWidget(self.uv_monitor_combo)

        self.aufs_combo = QComboBox()
        layout.addWidget(QLabel("AUFS:"))
        layout.addWidget(self.aufs_combo)

        self.uv_monitor_combo.currentTextChanged.connect(self.update_aufs_items)
        self.update_aufs_items()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def update_aufs_items(self):
        uv_type = self.uv_monitor_combo.currentText()
        self.aufs_combo.clear()
        if uv_type == "BioRad EM1":
            self.aufs_combo.addItems(["2.000", "1.000", "0.500", "0.200", "0.100", "0.050", "0.020", "0.010"])
        else:
            self.aufs_combo.addItems(["2.000", "1.000", "0.500", "0.200", "0.100", "0.050", "0.020", "0.010", "0.005", "0.002", "0.001"])

    def get_settings(self):
        return self.uv_monitor_combo.currentText(), float(self.aufs_combo.currentText())


class FlowRate_WarningDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Warning")
        self.setMinimumWidth(300)
        layout = QVBoxLayout()
        self.label = QLabel("Set FlowRate > 0 ml/min")
        layout.addWidget(self.label)
        self.confirm_button = QPushButton("Confirm")
        self.confirm_button.clicked.connect(self.accept)
        layout.addWidget(self.confirm_button)
        self.setLayout(layout)


class RunVolume_WarningDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Warning")
        self.setMinimumWidth(300)
        layout = QVBoxLayout()
        self.label = QLabel("Set Run Volume > 0 ml")
        layout.addWidget(self.label)
        self.confirm_button = QPushButton("Confirm")
        self.confirm_button.clicked.connect(self.accept)
        layout.addWidget(self.confirm_button)
        self.setLayout(layout)


class MethodEditor(QWidget):
    def __init__(self, parent=None, main_app=None):
        super().__init__(parent)
        self.main_app = main_app
        self.steps = []
        self.current_step_index = -1
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        title = QLabel("Method Editor")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Updated to 8 columns (merged PumpB Min/Max into Pump Mode)
        self.table = QTableWidget(0, 9)
        self.table.setStyleSheet("border: 1px solid white;")    
        self.table.verticalHeader().setVisible(False)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.table.setHorizontalHeaderLabels([
            "Step Number", "System Valve", "Flowrate (ml/min)", "Run Volume (ml)",
            "Pump Mode", "Frac Collect", "Monitor", "Diverter", "End Action"
        ])

        # Adjust column widths
        self.table.setColumnWidth(0, 90)
        self.table.setColumnWidth(1, 90)
        self.table.setColumnWidth(2, 125)
        self.table.setColumnWidth(3, 125)
        self.table.setColumnWidth(4, 160)# Pump Mode
        self.table.setColumnWidth(5, 85)
        self.table.setColumnWidth(6, 85)
        self.table.setColumnWidth(7, 90)

        layout.addWidget(self.table)
        button_layout = QHBoxLayout()
        self.add_step_btn = QPushButton("Add Step")
        self.add_step_btn.clicked.connect(self.add_step_dialog)
        button_layout.addWidget(self.add_step_btn)
        self.edit_step_btn = QPushButton("Edit Step")
        self.edit_step_btn.clicked.connect(self.edit_step_dialog)
        button_layout.addWidget(self.edit_step_btn)
        self.delete_step_btn = QPushButton("Delete Step")
        self.delete_step_btn.clicked.connect(self.delete_step_dialog)
        button_layout.addWidget(self.delete_step_btn)
        self.save_btn = QPushButton("Save Method")
        self.save_btn.clicked.connect(self.save_method)
        button_layout.addWidget(self.save_btn)
        self.load_btn = QPushButton("Load Method")
        self.load_btn.clicked.connect(self.load_method)
        button_layout.addWidget(self.load_btn)
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def add_step_dialog(self):
        if self.main_app and hasattr(self.main_app, "plot_widget"):
            self.main_app.plot_widget.clear()
        if not self.steps:
            # If no steps exist, insert the first step directly
            self.show_step_dialog(-1, self.add_step)# -1 so it inserts at index 0
        else:
            # Otherwise, open the  step insert dialog
            self._step_insert_dialog()

    def edit_step_dialog(self):
        if not self.steps:
            return# No steps to edit
        self._step_index_dialog("Edit step #", len(self.steps), self._edit_step_callback)

    def _edit_step_callback(self, index, dialog=None):
        self.show_step_dialog(index, self.edit_step)
        if dialog:
            dialog.accept()

    def delete_step_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Delete Step")
        layout = QVBoxLayout(dialog)

        label = QLabel("Delete Step Number:")
        spin = QSpinBox()
        spin.setRange(1, len(self.steps))
        spin.setValue(1)

        checkbox = QCheckBox("Delete All Steps:")
        layout.addWidget(label)
        layout.addWidget(spin)
        layout.addWidget(checkbox)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)

        def on_accept():
            if checkbox.isChecked():
                self.steps.clear()
                self.update_table()
            else:
                index = spin.value() - 1
                if 0 <= index < len(self.steps):
                    del self.steps[index]
                    self.update_table()
            dialog.accept()

        buttons.accepted.connect(on_accept)
        buttons.rejected.connect(dialog.reject)
        dialog.exec()

    def _step_insert_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Insert Step")
        layout = QVBoxLayout(dialog)

        position_combo = QComboBox()
        position_combo.addItems(["Before step", "After step"])

        index_spin = QSpinBox()
        index_spin.setRange(1, max(1, len(self.steps)))# At least 1 step
        index_spin.setValue(len(self.steps))# Default to last step

        layout.addWidget(QLabel("Insert step:"))
        layout.addWidget(position_combo)
        layout.addWidget(index_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)

        def on_accept():
            selected_index = index_spin.value() - 1
            if position_combo.currentText() == "Before step":
                insert_index = selected_index
            else:# After step
                insert_index = selected_index + 1
            dialog.accept()
            self.show_step_dialog(insert_index, self.add_step)

        buttons.accepted.connect(on_accept)
        buttons.rejected.connect(dialog.reject)
        dialog.exec()

    def show_step_dialog(self, index, callback):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Step" if index < 0 else f"Edit Step {index + 1}")
        layout = QVBoxLayout(dialog)

        # --- Widgets ---
        column_type_combo = QComboBox()
        column_type_combo.addItems(["Superdex-200", "Superose-6", "Mono Q 5/50", "Mono S 5/50", "His Trap", "Other"])

        valve_combo = QComboBox()
        valve_combo.addItems(["LOAD", "INJECT", "WASH"])

        flowrate_spin = QDoubleSpinBox()
        flowrate_spin.setRange(0.0, 10.0)
        flowrate_spin.setSingleStep(0.1)
        flowrate_spin.setDecimals(1)

        volume_spin = QDoubleSpinBox()
        volume_spin.setRange(0.0, 100.0)
        volume_spin.setSingleStep(1)
        volume_spin.setDecimals(1)

        pump_mode_combo = QComboBox()
        pump_mode_combo.addItems(["Isocratic", "Gradient"])

        pumpB_min_label = QLabel("PumpB Min %:")
        pumpB_min_spin = QDoubleSpinBox()
        pumpB_min_spin.setRange(0.0, 100.0)
        pumpB_min_spin.setDecimals(1)

        pumpB_max_label = QLabel("PumpB Max %:")
        pumpB_max_spin = QDoubleSpinBox()
        pumpB_max_spin.setRange(0.0, 100.0)
        pumpB_max_spin.setDecimals(1)
        pumpB_max_spin.setValue(100.0)

        frac_combo = QComboBox()
        frac_combo.addItems(["ON", "OFF"])

        monitor_combo = QComboBox()
        monitor_combo.addItems(["UV_ON", "UV_OFF"])
        
        monitor_settings_label = QLabel("Monitor Settings")
        monitor_settings_btn = QPushButton("Edit Settings")
        monitor_settings_btn.setEnabled(False) # Initially disabled

        divert_combo = QComboBox()
        divert_combo.addItems(["ON", "OFF"])

        end_action_combo = QComboBox()
        end_action_combo.addItems(["Continue", "Pause", "Stop"])

        def update_monitor_settings_button_state(text):
            is_enabled = text == "UV_ON"
            monitor_settings_btn.setEnabled(is_enabled)
            if is_enabled:
                monitor_settings_btn.setStyleSheet("")# Reset to default
                monitor_settings_label.setStyleSheet("color: white;")
            else:
                monitor_settings_btn.setStyleSheet("color: gray; background-color: #2e2e2e;")
                monitor_settings_label.setStyleSheet("color: gray;")
        # --- UV Monitor settings ---
        uv_monitor_type = "Pharmacia UV MII"
        aufs_value = 0.1

        def open_uv_monitor_settings():
            nonlocal uv_monitor_type, aufs_value
            dialog = UVMonitorSettingsDialog()
            if dialog.exec() == QDialog.Accepted:
                uv_monitor_type, aufs_value = dialog.get_settings()
                if self.main_app:
                    self.main_app.selected_uv_monitor = uv_monitor_type
                    self.main_app.selected_AUFS_value = aufs_value
                    self.main_app.uv_monitor_FS_value = 0.1 if uv_monitor_type == "Pharmacia UV MII" else 1.0

        monitor_combo.currentTextChanged.connect(lambda text: open_uv_monitor_settings() if text == "UV_ON" else None)
        monitor_combo.currentTextChanged.connect(update_monitor_settings_button_state)
        update_monitor_settings_button_state(monitor_combo.currentText())
        monitor_settings_btn.clicked.connect(open_uv_monitor_settings)
        
            # --- Palette helpers ---
        def apply_disabled_palette(widget):
            palette = widget.palette()
            palette.setColor(QPalette.ColorRole.Text, QColor("gray"))
            palette.setColor(QPalette.ColorRole.Base, QColor("#2e2e2e"))
            widget.setPalette(palette)

        def apply_enabled_palette(widget):
            palette = widget.palette()
            palette.setColor(QPalette.ColorRole.Text, QColor("white"))
            palette.setColor(QPalette.ColorRole.Base, QColor("#1e1e1e"))
            widget.setPalette(palette)


        def update_pumpB_controls(mode):
            is_gradient = (mode == "Gradient")
            pumpB_min_spin.setEnabled(is_gradient)
            pumpB_max_spin.setEnabled(is_gradient)

            pumpB_min_label.setStyleSheet("color: white;" if is_gradient else "color: gray;")
            pumpB_max_label.setStyleSheet("color: white;" if is_gradient else "color: gray;")

            if is_gradient:
                apply_enabled_palette(pumpB_min_spin)
                apply_enabled_palette(pumpB_max_spin)
                pumpB_max_spin.setValue(100.0)
            else:
                apply_disabled_palette(pumpB_min_spin)
                apply_disabled_palette(pumpB_max_spin)
                pumpB_min_spin.setValue(0.0)
                pumpB_max_spin.setValue(0.0)

        # Connect and initialize
        pump_mode_combo.currentTextChanged.connect(update_pumpB_controls)
        update_pumpB_controls(pump_mode_combo.currentText())# Initial state



        # --- Pre-fill if editing ---
        if index >= 0 and index < len(self.steps):
            step = self.steps[index]
            column_type_combo.setCurrentText(step.get("Column Type", "Superdex-200"))
            valve_combo.setCurrentText(step["System Valve"])
            flowrate_spin.setValue(step["Flowrate (ml/min)"])
            volume_spin.setValue(step["Run Volume (ml)"])
            pump_mode_combo.setCurrentText(step["Pump Mode"])
            pumpB_min_spin.setValue(step["PumpB Gradient"]["Min"])
            pumpB_max_spin.setValue(step["PumpB Gradient"]["Max"])
            frac_combo.setCurrentText(step["Frac Collect"])
            monitor_combo.setCurrentText(step.get("Monitor", "UV_OFF"))
            divert_combo.setCurrentText(step["Diverter"])
            end_action_combo.setCurrentText(step["End Action"])
            uv_monitor_type = step.get("UV Monitor Type", "Pharmacia UV MII")
            aufs_value = step.get("AUFS", 0.1)
        else:
            if hasattr(self.main_app, "saved_flowrate"):
                flowrate_spin.setValue(self.main_app.saved_flowrate)
            if hasattr(self.main_app, "saved_run_volume"):
                volume_spin.setValue(self.main_app.saved_run_volume)
            column_type_combo.setCurrentText(getattr(self.main_app, "selected_column_type", "Superdex-200"))
            frac_combo.setCurrentText("OFF")
            monitor_combo.setCurrentText("UV_OFF")
            divert_combo.setCurrentText("OFF")

        # --- Layout ---
        grid = QGridLayout()
        grid.setHorizontalSpacing(30)

        # Column 1
        grid.addWidget(QLabel("Column Type"), 0, 0)
        grid.addWidget(column_type_combo, 1, 0)
        grid.addWidget(QLabel("System Valve"), 4, 0)
        grid.addWidget(valve_combo, 5, 0)

        # Column 2
        grid.addWidget(QLabel("Flowrate (ml/min)"), 0, 1)
        grid.addWidget(flowrate_spin, 1, 1)
        grid.addWidget(QLabel("Run Volume (ml)"), 4, 1)
        grid.addWidget(volume_spin, 5, 1)

        # Column 3
        grid.addWidget(QLabel("Pump Mode"), 0, 2)
        grid.addWidget(pump_mode_combo, 1, 2)
        grid.addWidget(pumpB_min_label, 2, 2)
        grid.addWidget(pumpB_min_spin, 3, 2)
        grid.addWidget(pumpB_max_label, 4, 2)
        grid.addWidget(pumpB_max_spin, 5, 2)

        # Column 4
        grid.addWidget(QLabel("Fraction Collect"), 0, 3)
        grid.addWidget(frac_combo, 1, 3)
        grid.addWidget(QLabel("Monitor"), 2, 3)
        grid.addWidget(monitor_combo, 3, 3)
        grid.addWidget(monitor_settings_label, 4, 3)
        grid.addWidget(monitor_settings_btn, 5, 3)        

        # Column 5
        grid.addWidget(QLabel("Diverter Valve"), 0, 4)
        grid.addWidget(divert_combo, 1, 4)
        grid.addWidget(QLabel("Step End Action"), 4, 4)
        grid.addWidget(end_action_combo, 5, 4)

        layout.addLayout(grid)
        layout.addSpacing(20) # Add space between grid and buttons
        
        # --- Buttons ---
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)       
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(buttons)
        button_layout.addStretch()
        layout.addLayout(button_layout)


        def apply_changes():
            if flowrate_spin.value() <= 0.0:
                QMessageBox.warning(dialog, "Invalid Flowrate", "Flowrate must be greater than 0.")
                return
            if volume_spin.value() <= 0.0:
                QMessageBox.warning(dialog, "Invalid Volume", "Run Volume must be greater than 0.")
                return
            if monitor_combo.currentText() == "UV_ON" and aufs_value <= 0.0:
                QMessageBox.warning(dialog, "Invalid AUFS", "AUFS must be greater than 0.")
                return

            step_data = {
                "Column Type": column_type_combo.currentText(),
                "System Valve": valve_combo.currentText(),
                "Flowrate (ml/min)": round(flowrate_spin.value(), 2),
                "Run Volume (ml)": round(volume_spin.value(), 2),
                "Pump Mode": pump_mode_combo.currentText(),
                "PumpB Gradient": {
                "Min": pumpB_min_spin.value(),
                "Max": pumpB_max_spin.value()
                },
                "Frac Collect": frac_combo.currentText(),
                "Monitor": monitor_combo.currentText(),
                "UV Monitor Type": uv_monitor_type,
                "AUFS": aufs_value,
                "Diverter": divert_combo.currentText(),
                "End Action": end_action_combo.currentText()
            }
            callback(index, step_data, dialog)
            dialog.accept()

        buttons.accepted.connect(apply_changes)
        buttons.rejected.connect(dialog.reject)
        dialog.exec()

    def _step_index_dialog(self, title, max_index, callback):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        layout = QVBoxLayout(dialog)

        spin = QSpinBox()
        spin.setRange(1, max_index + 1)
        layout.addWidget(spin)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(lambda: callback(spin.value() - 1, dialog))
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        dialog.exec()

    def add_step(self, index, step_data, dialog=None):
        step = {
            "Step Number": "",
            "System Valve": step_data["System Valve"],
            "Flowrate (ml/min)": step_data["Flowrate (ml/min)"],
            "Run Volume (ml)": step_data["Run Volume (ml)"],
            "Pump Mode": step_data["Pump Mode"],
            "PumpB Gradient": {
            "Min": step_data["PumpB Gradient"]["Min"],
            "Max": step_data["PumpB Gradient"]["Max"]
            },
            "Frac Collect": step_data["Frac Collect"],
            "Monitor": step_data["Monitor"],
            "Diverter": step_data["Diverter"],
            "End Action": step_data["End Action"]
        }

        insert_index = index if index >= 0 else 0
        self.steps.insert(insert_index, step)
        self.update_table()

        # Update global values in main_app
        if self.main_app:
            self.main_app.selected_column_type = step_data["Column Type"]
            self.main_app.flowrate = step["Flowrate (ml/min)"]
            self.main_app.run_volume = step["Run Volume (ml)"]
            self.main_app.saved_flowrate = step["Flowrate (ml/min)"]
            self.main_app.saved_run_volume = step["Run Volume (ml)"]
            self.main_app.last_flowrate = step["Flowrate (ml/min)"]
            self.main_app.last_run_volume = step["Run Volume (ml)"]
            self.main_app.plot_widget.setXRange(0, step["Run Volume (ml)"])
            self.main_app.update_plot_title()

        if step["Monitor"] == "UV_ON":
            if hasattr(self.main_app, "open_UV_Monitor_dialog"):
                self.main_app.open_UV_Monitor_dialog()

        if dialog:
            dialog.accept()

    def edit_step(self, index, step_data, dialog=None):
        self.steps[index].update(step_data)
        self.update_table()

        if self.main_app:
            self.main_app.selected_column_type = step_data["Column Type"]
            self.main_app.flowrate = step_data["Flowrate (ml/min)"]
            self.main_app.run_volume = step_data["Run Volume (ml)"]
            self.main_app.saved_flowrate = step_data["Flowrate (ml/min)"]
            self.main_app.saved_run_volume = step_data["Run Volume (ml)"]
            self.main_app.last_flowrate = step_data["Flowrate (ml/min)"]
            self.main_app.last_run_volume = step_data["Run Volume (ml)"]
            self.main_app.plot_widget.setXRange(0, step_data["Run Volume (ml)"])
            self.main_app.update_plot_title()

        if step_data["Monitor"] == "UV_ON":
            if hasattr(self.main_app, "open_UV_Monitor_dialog"):
                self.main_app.open_UV_Monitor_dialog()

    def delete_step(self, index, dialog):
        if 0 <= index < len(self.steps):
            del self.steps[index]
            self.update_table()
        dialog.accept()


    def update_table(self):
        self.table.setRowCount(len(self.steps))
        for i, step in enumerate(self.steps):
            step["Step Number"] = f"Step {i + 1}"
            pump_mode_display = "Isocratic"
            if step["Pump Mode"] == "Gradient":
                min_val = step["PumpB Gradient"]["Min"]
                max_val = step["PumpB Gradient"]["Max"]
                pump_mode_display = f"Gradient ({min_val:.1f}->{max_val:.1f}%)"
            values = [
                step["Step Number"],
                step["System Valve"],
                f"{step['Flowrate (ml/min)']:.1f}",
                f"{step['Run Volume (ml)']:.1f}",
                pump_mode_display,
                step["Frac Collect"],
                step.get("Monitor", "UV_OFF"),
                step["Diverter"],
                step["End Action"]
            ]
            #for j, val in enumerate(values):
                #self.table.setItem(i, j, QTableWidgetItem(str(val)))
            for j, val in enumerate(values):#centered parameters
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, j, item)

    def save_method(self):
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Save Method", str(DEFAULT_METHOD_DIR), "JSON Files (*.json)"
        )
        if file_name:
            if not file_name.endswith(".json"):
                file_name += ".json"
            method_data = {
                "metadata": {
                "ColumnType": self.main_app.selected_column_type,
                "UVMonitor": self.main_app.selected_uv_monitor,
                "AUFS": self.main_app.selected_AUFS_value
                },
                "steps": self.steps
            }
            with open(file_name, 'w') as f:
                json.dump(method_data, f, indent=4)

    def load_method(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Load Method", str(DEFAULT_METHOD_DIR), "JSON Files (*.json)"
        )
        if file_name:
            with open(file_name, 'r') as f:
                method_data = json.load(f)
                
            # Clear plot if main_app and plot_widget are available
            if self.main_app and hasattr(self.main_app, "plot_widget"):
                self.main_app.plot_widget.clear()

            # Load metadata
            if "metadata" in method_data:
                metadata = method_data["metadata"]
                self.main_app.selected_column_type = metadata.get("ColumnType", "Superdex-200")
                self.main_app.selected_uv_monitor = metadata.get("UVMonitor", "Pharmacia UV MII")
                self.main_app.selected_AUFS_value = metadata.get("AUFS", 0.1)
                self.main_app.update_plot_title()

            # Load steps
            self.steps = method_data.get("steps", [])

        # Ensure backward compatibility with older format
            for step in self.steps:
                if "Pump Mode" not in step:
                    # Infer mode from presence of Min/Max
                    min_val = step.get("PumpB Min %", 0.0)
                    max_val = step.get("PumpB Max %", 0.0)
                    if min_val != max_val:
                        step["Pump Mode"] = "Gradient"
                        step["PumpB Gradient"] = {"Min": min_val, "Max": max_val}
                    else:
                        step["Pump Mode"] = "Isocratic"
                        step["PumpB Gradient"] = {"Min": 0.0, "Max": 100.0}
                    # Remove old keys if present
                    step.pop("PumpB Min %", None)
                    step.pop("PumpB Max %", None)

            self.update_table()

            # Apply flowrate and run volume from first step
            if self.steps:
                first_step = self.steps[0]
                flowrate = float(first_step.get("Flowrate (ml/min)", 0.0))
                run_volume = float(first_step.get("Run Volume (ml)", 0.0))
                self.main_app.flowrate = flowrate
                self.main_app.run_volume = run_volume
                self.main_app.last_flowrate = flowrate
                self.main_app.last_run_volume = run_volume
                self.main_app.saved_flowrate = flowrate
                self.main_app.saved_run_volume = run_volume
                self.main_app.plot_widget.setXRange(0, run_volume)
                self.main_app.update_plot_title()

    def get_method_sequence(self):
        return self.steps

    def new_method(self):
        self.steps = []
        self.update_table()
        
    def highlight_step_row(self, step_index, color=QColor("green")):
        """Highlight a row in the method table with a given color."""
        for col in range(self.table.columnCount()):
            item = self.table.item(step_index, col)
            if item:
                item.setBackground(QBrush(color))

    def reset_step_row_color(self, step_index):
        """Reset a row's background color to match the dark theme."""
        default_color = QColor(53, 53, 53)# Matches dark theme background
        for col in range(self.table.columnCount()):
            item = self.table.item(step_index, col)
            if item:
                item.setBackground(QBrush(default_color))


