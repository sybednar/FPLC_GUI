#method_editor.py 0.4.6

import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidget,
    QTableWidgetItem, QFileDialog, QDialog, QDialogButtonBox, QSpinBox, QDoubleSpinBox, QComboBox
)
from PySide6.QtCore import Qt

class MethodEditor(QWidget):
    def __init__(self, parent=None, main_app=None):
        super().__init__(parent)
        self.main_app = main_app
        self.steps = []
        self.current_step_index = -1
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        title = QLabel("Method Sequence Editor")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Updated to 8 columns (merged PumpB Min/Max into Pump Mode)
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            "Step Number", "System Valve", "Flowrate (ml/min)", "Run Volume (ml)",
            "Pump Mode", "Frac Collect", "Diverter", "End Action"
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
        self.end_action_btn = QPushButton("Set End Action")
        self.end_action_btn.clicked.connect(self.set_end_action_dialog)
        button_layout.addWidget(self.end_action_btn)
        self.save_btn = QPushButton("Save Method")
        self.save_btn.clicked.connect(self.save_method)
        button_layout.addWidget(self.save_btn)
        self.load_btn = QPushButton("Load Method")
        self.load_btn.clicked.connect(self.load_method)
        button_layout.addWidget(self.load_btn)
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def add_step_dialog(self):
        self._step_index_dialog("Insert after step #", len(self.steps), self.add_step)

    def edit_step_dialog(self):
        self._step_index_dialog("Edit step #", len(self.steps), self.edit_step)

    def delete_step_dialog(self):
        self._step_index_dialog("Delete step #", len(self.steps) - 1, self.delete_step)

    def set_end_action_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Set End-of-Step Action")
        layout = QVBoxLayout(dialog)

        index_spin = QSpinBox()
        index_spin.setRange(1, len(self.steps))
        layout.addWidget(QLabel("Step #:"))
        layout.addWidget(index_spin)

        action_combo = QComboBox()
        action_combo.addItems(["Continue", "Pause", "Stop"])
        layout.addWidget(QLabel("Action:"))
        layout.addWidget(action_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(lambda: self.set_end_action(index_spin.value() - 1, action_combo.currentText(), dialog))
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

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

    def add_step(self, index, dialog=None):
        step = {
            "Step Number": "",
            "System Valve": "LOAD",
            "Flowrate (ml/min)": 1.0,
            "Run Volume (ml)": 1.0,
            "Pump Mode": "Isocratic",
            "PumpB Gradient": {"Min": 0.0, "Max": 100.0},
            "Frac Collect": "OFF",
            "Diverter": "OFF",
            "End Action": "Continue"
        }
        self.steps.insert(index + 1, step)
        self.update_table()
        if dialog:
            dialog.accept()

    def edit_step(self, index, dialog=None):
        if not (0 <= index < len(self.steps)):
            return
        step = self.steps[index]
        edit_dialog = QDialog(self)
        edit_dialog.setWindowTitle(f"Edit Step {index + 1}")
        layout = QVBoxLayout(edit_dialog)

        valve_combo = QComboBox()
        valve_combo.addItems(["LOAD", "INJECT", "WASH"])
        valve_combo.setCurrentText(step["System Valve"])

        flowrate_spin = QDoubleSpinBox()
        flowrate_spin.setRange(0.0, 10.0)
        flowrate_spin.setSingleStep(0.1)  # Increment by 0.1
        flowrate_spin.setDecimals(1)
        flowrate_spin.setValue(float(step["Flowrate (ml/min)"]))

        volume_spin = QDoubleSpinBox()
        volume_spin.setRange(0.0, 100.0)
        volume_spin.setSingleStep(1)
        volume_spin.setDecimals(1)
        volume_spin.setValue(float(step["Run Volume (ml)"]))

        pump_mode_combo = QComboBox()
        pump_mode_combo.addItems(["Isocratic", "Gradient"])
        pump_mode_combo.setCurrentText(step["Pump Mode"])

        pumpB_min_spin = QDoubleSpinBox()
        pumpB_min_spin.setRange(0.0, 100.0)
        pumpB_min_spin.setDecimals(1)
        pumpB_min_spin.setValue(step["PumpB Gradient"]["Min"])

        pumpB_max_spin = QDoubleSpinBox()
        pumpB_max_spin.setRange(0.0, 100.0)
        pumpB_max_spin.setDecimals(1)
        pumpB_max_spin.setValue(step["PumpB Gradient"]["Max"])

        frac_combo = QComboBox()
        frac_combo.addItems(["ON", "OFF"])
        frac_combo.setCurrentText(step["Frac Collect"])

        divert_combo = QComboBox()
        divert_combo.addItems(["ON", "OFF"])
        divert_combo.setCurrentText(step["Diverter"])

        end_action_combo = QComboBox()
        end_action_combo.addItems(["Continue", "Pause", "Stop"])
        end_action_combo.setCurrentText(step["End Action"])

        layout.addWidget(QLabel("System Valve:"))
        layout.addWidget(valve_combo)
        layout.addWidget(QLabel("Flowrate (ml/min):"))
        layout.addWidget(flowrate_spin)
        layout.addWidget(QLabel("Run Volume (ml):"))
        layout.addWidget(volume_spin)
        layout.addWidget(QLabel("Pump Mode:"))
        layout.addWidget(pump_mode_combo)
        layout.addWidget(QLabel("PumpB Min %:"))
        layout.addWidget(pumpB_min_spin)
        layout.addWidget(QLabel("PumpB Max %:"))
        layout.addWidget(pumpB_max_spin)
        layout.addWidget(QLabel("Frac Collect:"))
        layout.addWidget(frac_combo)
        layout.addWidget(QLabel("Diverter:"))
        layout.addWidget(divert_combo)
        layout.addWidget(QLabel("End Action:"))
        layout.addWidget(end_action_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)

        def apply_changes():
            self.steps[index].update({
                "System Valve": valve_combo.currentText(),
                "Flowrate (ml/min)": flowrate_spin.value(),
                "Run Volume (ml)": volume_spin.value(),
                "Pump Mode": pump_mode_combo.currentText(),
                "PumpB Gradient": {
                    "Min": pumpB_min_spin.value(),
                    "Max": pumpB_max_spin.value()
                },
                "Frac Collect": frac_combo.currentText(),
                "Diverter": divert_combo.currentText(),
                "End Action": end_action_combo.currentText()
            })
            self.update_table()
            edit_dialog.accept()
            if dialog:
                dialog.accept()

        buttons.accepted.connect(apply_changes)
        buttons.rejected.connect(edit_dialog.reject)
        edit_dialog.exec()

    def delete_step(self, index, dialog):
        if 0 <= index < len(self.steps):
            del self.steps[index]
            self.update_table()
        dialog.accept()

    def set_end_action(self, index, action, dialog):
        if 0 <= index < len(self.steps):
            self.steps[index]["End Action"] = action
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
                step["Diverter"],
                step["End Action"]
            ]
            for j, val in enumerate(values):
                self.table.setItem(i, j, QTableWidgetItem(str(val)))

    def save_method(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Method", "", "JSON Files (*.json)")
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
        file_name, _ = QFileDialog.getOpenFileName(self, "Load Method", "", "JSON Files (*.json)")
        if file_name:
            with open(file_name, 'r') as f:
                method_data = json.load(f)

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


