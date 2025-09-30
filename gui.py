#gui.py (ver0.5.0) added monitor setting button, Run, Pause, Stop_Method button color indicator handling
#adding plotting of pumpB percent
import sys
import os
import csv
import time
import threading
import gpiod
from gpiod.line import Direction, Value
from datetime import datetime
from time import sleep
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QMessageBox, QVBoxLayout, QHBoxLayout,
    QWidget, QLabel, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QGridLayout, QDialog, QDialogButtonBox, QProgressBar, QFileDialog,
    QLineEdit, QTextEdit, QGraphicsOpacityEffect
)
from PySide6.QtCore import Signal, QObject, Qt
from PySide6.QtGui import QFont, QStandardItemModel, QStandardItem, QPalette, QColor

import pyqtgraph as pg
from pyqtgraph.exporters import ImageExporter
import socket
import json
import pandas as pd
import numpy as np
from network import FPLCServer
from hardware import set_gpio17, toggle_gpio17
from plotting import create_plot_widget, update_plot
from data_logger import DataLogger
from listener import ReceiveClientSignalsAndData
from method_editor import MethodEditor
from data_analysis import replot_from_csv, smooth_and_detect_peaks, extract_metadata_from_csv

import data_analysis
print("Using data_analysis from:", data_analysis.__file__)
               

class SetPumpAVolume_WarningDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Warning")
        self.setMinimumWidth(300)  # Adjust the width as needed
        layout = QVBoxLayout()
        self.label = QLabel("Set PumpA volume > 0 ml/min")
        layout.addWidget(self.label)
        self.confirm_button = QPushButton("Confirm")
        self.confirm_button.clicked.connect(self.accept)
        layout.addWidget(self.confirm_button)
        self.setLayout(layout)

class ConnectionWarningDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connection Warning")
        self.setMinimumWidth(300)
        layout = QVBoxLayout()

        label = QLabel("FPLC server and client not connected\nEstablish connection.....")
        label.setWordWrap(True)
        layout.addWidget(label)

        self.exit_button = QPushButton("Exit")
        self.exit_button.clicked.connect(self.reject)
        layout.addWidget(self.exit_button)

        self.setLayout(layout)
        
        # Connect to parent's signal
        if parent:
            parent.connection_established.connect(self.close_dialog)

    def close_dialog(self):
        self.accept()# or self.close()

class PauseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Paused")
        self.setMinimumWidth(400)
        layout = QVBoxLayout()
        font = self.font()
        font.setPointSize(16)  # adjust font size
        self.setFont(font)
        horizontal_layout = QHBoxLayout()
        self.label = QLabel("Run Paused...")
        horizontal_layout.addWidget(self.label)
        layout.addLayout(horizontal_layout)
        buttonLayout = QHBoxLayout()
        self.resume_button = QPushButton("Resume")
        self.resume_button.clicked.connect(self.accept)  # Close dialog on resume
        layout.addWidget(self.resume_button)
        self.setLayout(layout)


class SaveDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Save Data")
        self.setMinimumWidth(300)  # Adjust the width as needed
        layout = QVBoxLayout()
        font = self.font()
        font.setPointSize(16)  # Increase font size
        self.setFont(font)
        self.label = QLabel("Save acquired data?")
        layout.addWidget(self.label)

        self.yes_button = QPushButton("Yes")
        self.yes_button.clicked.connect(self.accept)
        layout.addWidget(self.yes_button)

        self.no_button = QPushButton("No")
        self.no_button.clicked.connect(self.reject)
        layout.addWidget(self.no_button)

        self.setLayout(layout)


class FractionCollectorErrorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Fraction Collector Error")
        self.setMinimumWidth(400)
        layout = QVBoxLayout()
        self.label = QLabel("Clear Frac-200 error before continuing")
        self.label.setWordWrap(True)
        layout.addWidget(self.label)
        self.exit_button = QPushButton("Exit")
        self.exit_button.clicked.connect(self.exit_error_dialog)
        layout.addWidget(self.exit_button)
        self.setLayout(layout)
        self.error_cleared = False

    def exit_error_dialog(self):
        if self.error_cleared:
            print("Calling accept()")
            self.accept()# Close the dialog
            #self.parent().stop_save_acquisition()# Activate the Stop and Save function
        else:
            QMessageBox.warning(self, "Error", "Please clear the fraction collector error before continuing.")

    def set_error_cleared(self):
        self.error_cleared = True # Update error status

class PumpErrorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pump Error")
        self.setMinimumWidth(400)
        self.layout = QVBoxLayout()
        self.label = QLabel()
        self.layout.addWidget(self.label)
        self.exit_button = QPushButton("Exit")
        self.exit_button.clicked.connect(self.exit_error_dialog)
        self.layout.addWidget(self.exit_button)
        self.setLayout(self.layout)

    def update_error_list(self, pump_errors):
        error_texts = []
        if pump_errors["A"]:
            error_texts.append("PumpA error detected.")
        if pump_errors["B"]:
            error_texts.append("PumpB error detected.")
        self.label.setText("\n".join(error_texts))

    def exit_error_dialog(self):
        QMessageBox.warning(self, "Error", "Please clear all pump errors before continuing.")

class SolventExchangeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Solvent Exchange")
        self.setMinimumWidth(300)

        layout = QVBoxLayout()

        self.pumpA_button = QPushButton("PumpA (OFF)")
        self.pumpA_button.clicked.connect(self.toggle_pumpA)
        layout.addWidget(self.pumpA_button)

        self.pumpB_button = QPushButton("PumpB (OFF)")
        self.pumpB_button.clicked.connect(self.toggle_pumpB)
        layout.addWidget(self.pumpB_button)

        self.start_wash_button = QPushButton("Start Wash")
        self.start_wash_button.clicked.connect(self.start_wash)
        layout.addWidget(self.start_wash_button)

        self.exit_button = QPushButton("Exit")
        self.exit_button.clicked.connect(self.exit_dialog)
        layout.addWidget(self.exit_button)

        self.setLayout(layout)

    def toggle_pumpA(self):
        self.parent().wash_pumpA = not self.parent().wash_pumpA
        if self.parent().wash_pumpA:
            self.pumpA_button.setText("PumpA_Wash-Press Start")           
        else:
            self.pumpA_button.setText("PumpA_Wash OFF")

    def toggle_pumpB(self):
        self.parent().wash_pumpB = not self.parent().wash_pumpB
        if self.parent().wash_pumpB:
            self.pumpB_button.setText("PumpB_Wash-Press Start")
        else:
            self.pumpB_button.setText("PumpB_Wash OFF")

    def start_wash(self):
        wash_pumps = []
        if self.parent().wash_pumpA:
            wash_pumps.append("A")
            self.parent().pumpA_wash_started = True
            if self.parent().pumpA_wash_started:
                self.pumpA_button.setText("PumpA_Wash-ON")
                self.pumpA_button.setStyleSheet("background-color: green; color: white;")
            self.parent().pumpA_wash_done = False
        if self.parent().wash_pumpB:
            wash_pumps.append("B")
            self.parent().pumpB_wash_started = True
            if self.parent().pumpB_wash_started:
                self.pumpB_button.setText("PumpB_Wash-ON")
                self.pumpB_button.setStyleSheet("background-color: green; color: white;")
            self.parent().pumpB_wash_done = False

        if wash_pumps and self.parent().connection:
            message = f'WASH_PUMPS_JSON:{json.dumps({"WASH_PUMPS": wash_pumps})}'
            self.parent().connection.sendall(message.encode('utf-8'))
            print(f"Sent WASH_PUMPS_JSON message: {message}")

    def exit_dialog(self):
        self.parent().wash_pumpA = False
        self.parent().wash_pumpB = False
        self.pumpA_button.setText("PumpA OFF")
        self.pumpB_button.setText("PumpB OFF")
        self.close()

class AdaptiveStepSpinBox(QDoubleSpinBox):
    def stepBy(self, steps):
        current = self.value()
        if current < 1000:
            step = 100
        elif current < 10000:
            step = 1000
        elif current < 100000:
            step = 10000
        elif current < 1e6:
            step = 100000
        else:
            step = 1e6
        self.setSingleStep(step)
        super().stepBy(steps)


class PeakSmoothingDialog(QDialog):
    parameters_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Baseline and Peak Smoothing")
        self.setMinimumWidth(500)

        main_layout = QVBoxLayout()
        grid_layout = QGridLayout()
        self.move(200,200)
        # --- Open Data File Button ---
        self.open_data_button = QPushButton("Open Data File")
        main_layout.addWidget(self.open_data_button)
        if parent and hasattr(parent, 'Regraph_data_file'):
            self.open_data_button.clicked.connect(lambda: parent.Regraph_data_file(show_exit_dialog=False))
            #self.open_data_button.clicked.connect(parent.Regraph_data_file)

        # --- Section Headers ---
        self.left_header = QLabel("<b>Baseline Correction</b>")
        self.right_header = QLabel("<b>Peak Detection</b>")
        self.left_header.setAlignment(Qt.AlignCenter)
        self.right_header.setAlignment(Qt.AlignCenter)
        grid_layout.addWidget(self.left_header, 0, 0)
        grid_layout.addWidget(self.right_header, 0, 1)

        # --- Baseline Controls ---
        self.baseline_checkbox = QPushButton("AsLS Baseline (OFF)")
        self.baseline_checkbox.setCheckable(True)
        self.baseline_checkbox.setChecked(False)
        self.baseline_checkbox.clicked.connect(self.toggle_baseline)

        self.lam_label = QLabel("AsLS λ (lambda):")
        self.lam_spin = AdaptiveStepSpinBox()
        self.lam_spin.setRange(1e2, 1e8)
        self.lam_spin.setDecimals(0)
        self.lam_spin.setValue(1e5)

        self.p_label = QLabel("AsLS p:")
        self.p_spin = QDoubleSpinBox()
        self.p_spin.setRange(0.001, 1.0)
        self.p_spin.setDecimals(3)
        self.p_spin.setSingleStep(0.01)
        self.p_spin.setValue(0.01)

        self.max_iter_label = QLabel("AsLS max_iter:")
        self.max_iter_spin = QSpinBox()
        self.max_iter_spin.setRange(1, 50)
        self.max_iter_spin.setValue(10)

        # --- Peak Detection Controls ---
        self.peak_id_button = QPushButton("Peak_ID (OFF)")
        self.peak_id_button.setCheckable(True)
        self.peak_id_button.setChecked(False)
        self.peak_id_button.clicked.connect(self.toggle_peak_id)
        self.peak_id_on = False

        self.window_label = QLabel("SG_Window Length (odd):")
        self.window_spin = QSpinBox()
        self.window_spin.setRange(5, 199)
        self.window_spin.setSingleStep(2)
        self.window_spin.setValue(51)

        self.poly_label = QLabel("SG_Polynomial Order:")
        self.poly_spin = QSpinBox()
        self.poly_spin.setRange(1, 10)
        self.poly_spin.setValue(3)

        self.distance_label = QLabel("Min Distance Between Peaks:")
        self.distance_spin = QSpinBox()
        self.distance_spin.setRange(1, 1000)
        self.distance_spin.setValue(100)

        # --- Add Widgets to Grid ---
        grid_layout.addWidget(self.baseline_checkbox, 1, 0)
        grid_layout.addWidget(self.lam_label, 2, 0)
        grid_layout.addWidget(self.lam_spin, 3, 0)
        grid_layout.addWidget(self.p_label, 4, 0)
        grid_layout.addWidget(self.p_spin, 5, 0)
        grid_layout.addWidget(self.max_iter_label, 6, 0)
        grid_layout.addWidget(self.max_iter_spin, 7, 0)

        grid_layout.addWidget(self.peak_id_button, 1, 1)
        grid_layout.addWidget(self.window_label, 2, 1)
        grid_layout.addWidget(self.window_spin, 3, 1)
        grid_layout.addWidget(self.poly_label, 4, 1)
        grid_layout.addWidget(self.poly_spin, 5, 1)
        grid_layout.addWidget(self.distance_label, 6, 1)
        grid_layout.addWidget(self.distance_spin, 7, 1)

        # --- Confirm and Exit Buttons ---
        button_layout = QHBoxLayout()
        self.confirm_button = QPushButton("Save Processed Data")
        self.exit_button = QPushButton("Exit")
        button_layout.addWidget(self.confirm_button)
        button_layout.addWidget(self.exit_button)

        main_layout.addLayout(grid_layout)
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

        self.confirm_button.clicked.connect(self.accept)
        self.exit_button.clicked.connect(self.reject)

        for spin in [self.lam_spin, self.p_spin, self.max_iter_spin, self.window_spin, self.poly_spin, self.distance_spin]:
            spin.valueChanged.connect(lambda _: self.parameters_changed.emit())
        self.baseline_checkbox.clicked.connect(lambda: self.parameters_changed.emit())

        self.update_baseline_controls()
        self.update_peak_controls()

    def toggle_baseline(self):
        is_checked = self.baseline_checkbox.isChecked()
        self.baseline_checkbox.setText("AsLS Baseline (ON)" if is_checked else "AsLS Baseline (OFF)")
        self.update_baseline_controls()

    def update_baseline_controls(self):
        enabled = self.baseline_checkbox.isChecked()
        for widget in [self.lam_spin, self.p_spin, self.max_iter_spin]:
            widget.setEnabled(enabled)
            palette = widget.palette()
            palette.setColor(QPalette.ColorRole.Text, QColor("white") if enabled else QColor("gray"))
            widget.setPalette(palette)

        for label in [self.lam_label, self.p_label, self.max_iter_label]:
            palette = label.palette()
            palette.setColor(QPalette.ColorRole.WindowText, QColor("white") if enabled else QColor("gray"))
            label.setPalette(palette)

    def toggle_peak_id(self):
        self.peak_id_on = not self.peak_id_on
        self.peak_id_button.setText("Peak_ID (ON)" if self.peak_id_on else "Peak_ID (OFF)")
        self.update_peak_controls()
        self.parameters_changed.emit()

    def update_peak_controls(self):
        enabled = self.peak_id_on
        for widget in [self.window_spin, self.poly_spin, self.distance_spin]:
            widget.setEnabled(enabled)
            palette = widget.palette()
            palette.setColor(QPalette.ColorRole.Text, QColor("white") if enabled else QColor("gray"))
            widget.setPalette(palette)
        for label in [self.window_label, self.poly_label, self.distance_label]:
            palette = label.palette()
            palette.setColor(QPalette.ColorRole.WindowText, QColor("white") if enabled else QColor("gray"))
            label.setPalette(palette)

    def get_values(self):
        return (
            self.window_spin.value(),
            self.poly_spin.value(),
            self.peak_id_on,
            self.distance_spin.value(),
            self.baseline_checkbox.isChecked(),
            self.lam_spin.value(),
            self.p_spin.value(),
            self.max_iter_spin.value()
        )

class NotesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Run Notes")
        self.setMinimumWidth(400)
        layout = QVBoxLayout()

        self.sample_input = QLineEdit()
        self.bufferA_input = QLineEdit()
        self.bufferB_input = QLineEdit()
        self.notes_input = QTextEdit()

        layout.addWidget(QLabel("Sample (e.g., SCD2A 1 mg/ml):"))
        layout.addWidget(self.sample_input)
        layout.addWidget(QLabel("Buffer A:"))
        layout.addWidget(self.bufferA_input)
        layout.addWidget(QLabel("Buffer B:"))
        layout.addWidget(self.bufferB_input)
        layout.addWidget(QLabel("Other Notes:"))
        layout.addWidget(self.notes_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def get_notes(self):
        return {
            "Sample": self.sample_input.text(),
            "Buffer_A": self.bufferA_input.text(),
            "Buffer_B": self.bufferB_input.text(),
            "Other_Notes": self.notes_input.toPlainText()
        }

#---------- Worker class for background data acquisition----------
class Worker(QObject):
    data_signal = Signal(float, float, float, float, float, float)
    finished = Signal()
    error_signal = Signal(str)
    error_cleared_signal = Signal(str)

    def __init__(self, write_to_csv_callback, main_app, selected_uv_monitor, selected_AUFS_value, connection):
        super().__init__()
        self.is_running = False
        self.write_to_csv_callback = write_to_csv_callback
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set()
        self.total_pause_duration = 0
        self.pause_start_time = None
        self.selected_uv_monitor = selected_uv_monitor
        self.selected_AUFS_value = selected_AUFS_value
        self.main_app = main_app
        self.connection = connection
        self.error_emitted = False

    def run(self):
        self.is_running = True
        while self.is_running and not self.stop_event.is_set():
            self.pause_event.wait()
            time.sleep(0.1)
        self.is_running = False
        self.finished.emit()
            
            
    def handle_data_received(self, message):
        # This is called by the centralized listener

        values = message.split(',')
        if len(values) == 6:  #changed from 5 to 6 09-27-25
            try:
                value1 = int(values[0])
                value2 = int(values[1])
                elapsed_time = float(values[2])
                eluate_volume = float(values[3])
                frac_mark = float(values[4])
                pumpB_percent = float(values[5]) #line added 09-27-25
                #Chan1 = (value1 / 32768.0) * 0.256
                #Chan2 = (value2 / 32768.0) * 0.256 #replaced with code below 090325
                
                # Determine full-scale voltage based on monitor type
                if self.selected_uv_monitor == "Uvcord SII":
                    fs_voltage = 1.024
                else:
                    fs_voltage = 0.256

                Chan1 = (value1 / 32768.0) * fs_voltage
                Chan2 = (value2 / 32768.0) * fs_voltage
                
                if self.selected_uv_monitor == "Pharmacia UV MII":
                    Chan1_AU280 = max(0.001, round(Chan1 * (self.selected_AUFS_value / 0.1), 4))
                elif self.selected_uv_monitor == "Uvcord SII":
                    Chan1_AU280 = max(0.001, round(Chan1 * (self.selected_AUFS_value / 1.0), 4))
                else:
                    Chan1_AU280 = Chan1
                self.data_signal.emit(elapsed_time, frac_mark, Chan1, Chan1_AU280, Chan2, pumpB_percent)
            except ValueError: 
                print("Error parsing acquisition data:", message)
        else:
            print("Received malformed data:", message) 


    def pause(self):
        self.pause_start_time = time.time()
        self.pause_event.clear()

    def resume(self):
        if self.pause_start_time is not None:
            pause_duration = time.time() - self.pause_start_time
            self.total_pause_duration += pause_duration
            self.pause_start_time = None
        self.pause_event.set()

    def stop(self):
        self.is_running = False
        self.stop_event.set()
        
class FPLCSystemApp(QMainWindow):
    connection_established = Signal()
    
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(1024, 768)
        
        self.connection_status_label = QLabel("FPLC not connected", self)
        self.connection_status_label.setGeometry(848, 10, 150, 30)
        self.connection_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.connection_status_label.setStyleSheet("background-color: red; color: white; border: 1px solid black;")
                
        # Initialize state variables
        self.connection = None
        self.worker = None
        self.thread = None
        self.error_dialog_open = False
        self.scan_rate = 10
        self.run_volume = 0.0
        self.is_running = False
        self.acquisition_stopped = False #prevent multiple save dialog windows from opening
        self.saved_run_volume = 0.0
        self.last_run_volume = 0.0
        self.total_pause_duration = 0
        self.saved_flowrate = 0.0
        self.last_flowrate = 0.0
        self.selected_column_type = "Superdex-200"
        self.selected_AUFS_value = 0.0
        self.flowrate = 0.0
        self.uv_monitor_FS_value = 0.1
        self.max_y_value = self.selected_AUFS_value
        self.selected_uv_monitor = "Pharmacia UV MII"
        self.metadata_written = False
        self.toggle_pump_calibration_mode = 'OFF'
        self.program_mode = None # Tracks 'Open', 'Create', or None
        self.wash_pumpA = False #Tracks whether the user enabled PumpA wash in the GUI
        self.wash_pumpB = False
        self.pumpA_wash_started = False #Tracks if wash command was sent client
        self.pumpB_wash_started = False
        self.pumpA_wash_done = False #Tracks if client reported completion of the wash.
        self.pumpB_wash_done = False
        self.elution_method = "Isocratic"
        self.pumpA_button = None
        self.pumpA_volume = 0
        self.saved_pumpA_volume = 0
        self.last_pumpA_volume = 0
        self.run_pumpA = False
        self.pumpB_button = None
        self.pump_listener = None
        self.system_valve_position = "LOAD"
        self.divert_valve_mode = False 
        self.fraction_collector_mode_enabled = False
        self.saved_pumpB_min = 0.0
        self.saved_pumpB_max = 100.0
        self.pump_errors = {"A": False, "B": False}
        self.current_step_index = 0
        self.method_sequence = []
        self.run_notes_written = False
        self.RunDateTime = None



        # Data storage
        self.elapsed_time_data = []
        self.eluate_volume_data = []
        self.frac_mark_data = []
        self.chan1_data = []
        self.chan1_AU280_data = []
        self.chan2_data = []
        self.pumpB_percent_data = []
        self.user_notes = {}

        # Setup paths and logger
        self.basepath = '/home/sybednar/FPLC_controller_venv/Measurement_Computing'
        self.mypath = os.path.join(self.basepath, 'Scanning_log_files')
        self.metadata_fieldnames = [
        "RUN_VOLUME (ml)", "Year/Date/Time", "Column_type", "AUFS_setting",
        "UV_monitor", "UV_monitor_FS_value (Volts)", "Flowrate (ml/min)"
        ]
        self.data_fieldnames = [
        "Elapsed_Time (sec)", "Eluate_Volume (ml)", "Frac_Mark",
        "Chan1 (volt)", "Chan1_AU280 (AU)", "Chan2", "PumpB_percent"
        ]
        self.logger = DataLogger(self.basepath, self.metadata_fieldnames, self.data_fieldnames)

        # UI setup
        self.init_ui()
        self.server = FPLCServer()
        self.server.start_server()
        self.connection = None
        self.start_connection_monitor()

    def init_ui(self):
        container = QWidget(self)
        container.setGeometry(0, 0, 1024, 768)

        # Plot widget
        self.plot_widget = create_plot_widget(container)
        self.plot_widget.setGeometry(212, 50, 600, 300)

        # Connection status label
        self.connection_status_label = QLabel("FPLC not connected", self)
        self.connection_status_label.setGeometry(848, 10, 150, 30)
        self.connection_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.connection_status_label.setStyleSheet("background-color: red; color: white; border: 1px solid black;")

        # Labels
        #left_top_label = QLabel("Method", container)
        #left_top_label.setGeometry(50, 520, 100, 30)
        #left_top_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        left_middle_label = QLabel("Method Operate", container)
        left_middle_label.setGeometry(50, 60, 100, 30)
        left_middle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        left_wash_label = QLabel("Pump Wash", container)
        left_wash_label.setGeometry(50, 320, 100, 30)
        left_wash_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        right_label = QLabel("Chromatogram", container)
        right_label.setGeometry(874, 60, 100, 30)
        right_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.method_run_button = QPushButton("Run_Method", container)
        self.method_run_button.setGeometry(50, 100, 100, 30)
        self.method_run_button.clicked.connect(self.handle_method_run)

        self.method_pause_button = QPushButton("Pause_Method", container)
        self.method_pause_button.setGeometry(50, 180, 100, 30)
        self.method_pause_button.clicked.connect(self.handle_method_pause)

        self.method_stop_button = QPushButton("Stop_Method", container)
        self.method_stop_button.setGeometry(50, 260, 100, 30)
        self.method_stop_button.clicked.connect(self.handle_method_stop)

        # Right-side buttons
        self.Regraph_button = QPushButton("Plot View", container)
        self.Regraph_button.setGeometry(874, 100, 100, 30)
        self.Regraph_button.clicked.connect(lambda: self.Regraph_data_file(show_exit_dialog=True))
        #self.Regraph_button.clicked.connect(self.Regraph_data_file)
        #self.Regraph_button.setStyleSheet("color: blue;")


        self.Peak_Processing_button = QPushButton("Peak_ID", container)
        self.Peak_Processing_button.setGeometry(874, 180, 100, 30)
        self.Peak_Processing_button.clicked.connect(self.Peak_Smoothing_PeakID)

        self.run_notes_button = QPushButton("Run Notes", container)
        self.run_notes_button.setGeometry(874, 260, 100, 30)
        self.run_notes_button.clicked.connect(self.open_run_notes_dialog)

        self.desktop_button = QPushButton("Desktop", container)
        self.desktop_button.setGeometry(874, 680, 100, 30)
        self.desktop_button.clicked.connect(self.close_application)
            
        # Pump and valve control buttons
        self.pump_wash_button = QPushButton("Solvent Change", container)
        self.pump_wash_button.setGeometry(50, 360, 100, 30)
        self.pump_wash_button.clicked.connect(self.open_solvent_exchange_dialog)

        #self.pump_calibration_button = QPushButton("Pump_Calibration", container)
        #self.pump_calibration_button.setGeometry(874, 400, 100, 30)
        #self.pump_calibration_button.clicked.connect(self.toggle_pump_calibration)
        
        Pumps_label = QLabel("Pumps", container)
        Pumps_label.setGeometry(280, 680, 100, 30)
        Pumps_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.volume_delivered_progress_bar = QProgressBar(self)
        self.volume_delivered_progress_bar.setGeometry(363, 680, 300, 30)
        self.volume_delivered_progress_bar.setRange(0, 100)
        self.volume_delivered_progress_bar.setValue(0)
        self.volume_delivered_progress_bar.setFormat("Idle")
        self.volume_delivered_progress_bar.setStyleSheet("QProgressBar { color: white; }")

        self.method_editor = MethodEditor(container, main_app=self)
        self.method_editor.setGeometry(25, 420, 975, 240) # Adjust size and position as needed

    #adding stylization
    def update_run_button_state(self, state):
        if state == "running":
            self.method_run_button.setStyleSheet("background-color: green; color: white;")
        elif state == "paused":
            self.method_run_button.setStyleSheet("background-color: yellow; color: black;")
        elif state == "error":
            self.method_run_button.setStyleSheet("background-color: red; color: white;")
        else:
            self.method_run_button.setStyleSheet("")# Reset to default

    def restore_run_button_state_after_error(self):
        if self.worker and self.worker.is_running:
            if self.worker.pause_event.is_set():
                self.update_run_button_state("running")
            else:
                self.update_run_button_state("paused")

    def handle_method_run(self):
        if self.connection is None or self.connection.fileno() == -1:
            QMessageBox.critical(self, "Connection Error", "FPLC client is not connected. Please wait for connection.")
            print("Run_Method clicked but client is not connected. Button will not turn green.")
            return
        
        if not self.user_notes:
            self.open_run_notes_dialog()       
        if not self.run_notes_written:
            self.RunDateTime = datetime.strftime(datetime.now(), "%Y_%b_%d_%H%M%S") #sets year/date/time stamp at beginning of run throughout 
            self.write_run_notes_on_start()
            self.run_notes_written = True       
        self.set_all_buttons_enabled(False)
        self.method_sequence = self.method_editor.get_method_sequence()
        self.update_run_button_state("running")
        self.method_pause_button.setStyleSheet("background-color: yellow; color: black;")
        self.method_stop_button.setStyleSheet("background-color: red; color: white;")
        self.current_step_index = 0
        self.run_next_step()

    def write_run_notes_on_start(self):
        if not self.user_notes:
            self.user_notes = {
                "Sample": "",
                "Buffer_A": "",
                "Buffer_B": "",
                "Other_Notes": ""
            }
        method_text = "\nRun Method:\n"
        for i, step in enumerate(self.method_editor.get_method_sequence(), 1):
            method_text += f"Step {i}: " + ", ".join(f"{k}: {v}" for k, v in step.items()) + "\n"
        self.user_notes["Other_Notes"] += " " + method_text
        self.notes_timestamp = datetime.strftime(datetime.now(), "%Y_%b_%d_%H%M%S")
        self.logger.write_run_notes(self.user_notes, self.notes_timestamp)
        
    def set_all_buttons_enabled(self, enabled: bool):
        """
        Enable or disable all QPushButton widgets in the GUI,
        except 'Pause_Method' and 'Stop_Method'.
        'Run_Method' is enabled only when not running.
        Dim disabled buttons using opacity and style.
        """
        for button in self.findChildren(QPushButton):
            if button.text() in ["Pause_Method", "Stop_Method"]:
                button.setEnabled(True)
                button.setGraphicsEffect(None)
                button.setStyleSheet("")# Reset style
            elif button.text() == "Run_Method":
                button.setEnabled(not self.is_running)
                if self.is_running:
                    effect = QGraphicsOpacityEffect()
                    effect.setOpacity(0.4)
                    button.setGraphicsEffect(effect)
                    button.setStyleSheet("color: gray; background-color: #444;")
                else:
                    button.setGraphicsEffect(None)
                    button.setStyleSheet("")
            else:
                button.setEnabled(enabled)
                if not enabled:
                    effect = QGraphicsOpacityEffect()
                    effect.setOpacity(0.4)
                    button.setGraphicsEffect(effect)
                    button.setStyleSheet("color: gray; background-color: #444;")
                else:
                    button.setGraphicsEffect(None)
                    button.setStyleSheet("")

        # Dim MethodEditor widget
        if hasattr(self, 'method_editor'):
            self.method_editor.setEnabled(enabled)
            if not enabled:
                effect = QGraphicsOpacityEffect()
                effect.setOpacity(0.4)
                self.method_editor.setGraphicsEffect(effect)
            else:
                self.method_editor.setGraphicsEffect(None)

    def run_next_step(self):
        if self.connection is None or self.connection.fileno() == -1:
            QMessageBox.critical(self, "Connection Error", "FPLC client is not connected. Please wait for connection.")
            print("run_next_step aborted: No connection to client.")
            return
        
        if self.current_step_index >= len(self.method_sequence):
            print("All steps completed.")
            return

        step = self.method_sequence[self.current_step_index]

        # Highlight the current step row
        self.method_editor.highlight_step_row(self.current_step_index)

        # Update flowrate and run volume
        self.flowrate = float(step["Flowrate (ml/min)"])
        self.run_volume = float(step["Run Volume (ml)"])
        self.last_flowrate = self.flowrate
        self.last_run_volume = self.run_volume
        self.saved_flowrate = self.flowrate
        self.saved_run_volume = self.run_volume

        # Update plot
        self.plot_widget.setXRange(0, self.run_volume)
        self.update_plot_title()

        # Determine pump mode and prepare run packet
        pump_mode = step.get("Pump Mode", "Isocratic")
        run_packet = {
            "System_Valve_Position": step["System Valve"],
            "FLOWRATE": self.flowrate,
            "VOLUME": self.run_volume,
            "DIVERTER_VALVE": step["Diverter"],
            "START_PUMPS": True,
            "UV_MONITOR_TYPE": self.selected_uv_monitor #added 090325
        }
        #if self.fraction_collector_mode_enabled: #removed ver 4.6.5
        if step.get("Monitor", "UV_OFF") == "UV_ON": #added ver 4.6.5
            run_packet["START_ADC"] = True
        if step.get("Frac Collect", "OFF") == "ON":
            run_packet["START_FRAC"] = True

        if pump_mode == "Gradient":
            gradient = step.get("PumpB Gradient", {"Min": 0.0, "Max": 100.0})
            run_packet["PumpB_min_percent"] = gradient.get("Min", 0.0)
            run_packet["PumpB_max_percent"] = gradient.get("Max", 100.0)
            message = f'GRADIENT_RUN_METHOD_JSON:{json.dumps(run_packet)}'
        else:
            run_packet["PumpB_min_percent"] = 0.0
            run_packet["PumpB_max_percent"] = 0.0
            message = f'ISOCRATIC_RUN_METHOD_JSON:{json.dumps(run_packet)}'

        try:
            self.connection.sendall(message.encode('utf-8'))
            print(f"Sent step {self.current_step_index + 1}: {message}")
        except socket.error as e:
            print(f"Error sending step: {e}")
            self.handle_disconnection()
            return

        if step.get("Monitor", "UV_OFF") == "UV_ON": #addded ver 4.6.5
            self.run_acquisition()

    def handle_next_step(self):
        if self.current_step_index >= len(self.method_sequence):
            return
        
        # Reset the previous step row color
        self.method_editor.reset_step_row_color(self.current_step_index)

        step = self.method_sequence[self.current_step_index]
        end_action = step.get("End Action", "Continue")

        if end_action == "Continue":
            self.current_step_index += 1
            self.run_next_step()
        elif end_action == "Pause":
            self.handle_method_pause()
        elif end_action == "Stop":
            self.handle_method_stop()

    def handle_method_pause(self):
        self.update_run_button_state("paused")
        print("Method Pause clicked")
        self.open_pause_dialog()
        
    def handle_method_stop(self):
        self.update_run_button_state("default")
        print("Method Stop clicked")
        
        # Reset all method table row colors
        if self.method_editor and hasattr(self.method_editor, "reset_step_row_color"):
            for i in range(len(self.method_sequence)):
                self.method_editor.reset_step_row_color(i)
        
        if self.connection:
            stop_method_packet = {
                "STOP_PUMPS": True,
                "System_Valve_Position": "LOAD",
                "FLOWRATE": 0.0,
                "PumpA_Volume": 0.0,
                "PumpB_min_percent": 0.0,
                "PumpB_max_percent": 0.0
            }

            if self.method_sequence and self.method_sequence[-1].get("Monitor", "UV_OFF") == "UV_ON":
                stop_method_packet["STOP_ADC"] = True
            
            if self.method_sequence and self.method_sequence[-1].get("Frac Collect", "OFF") == "ON":
                stop_method_packet["STOP_FRAC"] = True

            if self.divert_valve_mode:
                stop_method_packet["DIVERTER_VALVE"] = False # could delete as default setting in client when stop is "OFF" 

            try:
                self.connection.sendall(f'METHOD_STOP_JSON:{json.dumps(stop_method_packet)}'.encode('utf-8'))
                print(f"Sent METHOD_STOP_JSON: {stop_method_packet}")
            except socket.error as e:
                print(f"Error sending METHOD_STOP_JSON: {e}")
                self.handle_disconnection()

            self.reset_progress_bar()
            self.run_notes_written = False
            self.method_pause_button.setStyleSheet("")
            self.method_stop_button.setStyleSheet("")
            self.set_all_buttons_enabled(True)
            if self.fraction_collector_mode_enabled:
                self.stop_save_acquisition()

    def Regraph_data_file(self, show_exit_dialog=True):
        print("ReGraph Button clicked")
        try:
            file_dialog = QFileDialog()
            file_dialog.setNameFilter("CSV files (*.csv)")
            file_dialog.setDirectory(os.path.join(self.basepath, 'Scanning_log_files'))
            if file_dialog.exec():
                selected_files = file_dialog.selectedFiles()
                if selected_files:
                    self.csv_path = selected_files[0]#  Store file path for reuse
                    metadata = extract_metadata_from_csv(self.csv_path)
                    replot_from_csv(
                        basepath=self.basepath,
                        plot_widget=self.plot_widget,
                        run_volume=self.run_volume,
                        max_y_value=self.max_y_value,
                        update_plot=update_plot,
                        csv_path=self.csv_path#  Pass the selected file
                    )
                    plot_title = f"<b><br>{metadata['Column_type']}: {metadata['Year/Date/Time']}</b><br>Flowrate: {metadata['Flowrate (ml/min)']} ml/min"
                    self.plot_widget.setTitle(plot_title, size='12pt', color='w')

                    if show_exit_dialog:
                        # Extract filename from path
                        filename = os.path.basename(self.csv_path) if self.csv_path else "ReGraph"

                        exit_dialog = QMessageBox(self)
                        #exit_dialog.setWindowTitle(filename)  # Show current file name
                        exit_dialog.setWindowTitle("Plot view")
                        exit_dialog.setText("Click Close to clear the plot and exit.")
                        exit_dialog.setStandardButtons(QMessageBox.Close)
                        exit_dialog.setDefaultButton(QMessageBox.Close)

                        response = exit_dialog.exec()
                        if response == QMessageBox.Close:
                            self.clear_plot_and_reset()
                            self.csv_path = None
                            print("Plot cleared and system reset after ReGraph.")


        except Exception as e:
            print(f"Error during replot: {e}")
 
    def Peak_Smoothing_PeakID(self):
        print("Peak_Smoothing Button clicked")
        # Clear plot and reset before analysis
        self.clear_plot_and_reset()
        dialog = PeakSmoothingDialog(self)
        dialog.rejected.connect(self.clear_plot_and_reset)
  
        def apply_and_plot():
            window_length, polyorder, peak_id_on, distance, baseline_on, lam, p, max_iter = dialog.get_values()

            try:
                if hasattr(self, 'csv_path'):
                    metadata = extract_metadata_from_csv(self.csv_path)
                    df, peaks, frac_marks = smooth_and_detect_peaks(
                        self.csv_path,
                        window_length,
                        polyorder,
                        distance,
                        baseline_correction=baseline_on,
                        lam=lam,
                        p=p,
                        max_iter=max_iter
                    )

                    x = df["Eluate_Volume (ml)"]
                    y_raw = df["Chan1_AU280 (AU)"]
                    y_smooth = df["Chan1_AU280_Smoothed (AU)"]
                    y_frac = df["Frac_Mark_Scaled"]
                    max_y = max(y_raw.max(), y_smooth.max()) * 1.1
                    x_max = df["RUN_VOLUME (ml)"].dropna().values[0] if "RUN_VOLUME (ml)" in df.columns and df["RUN_VOLUME (ml)"].notna().any() else x.max()

                    self.plot_widget.clear()
                    pen_raw = pg.mkPen(color='c', width=2)
                    pen_smooth = pg.mkPen(color='g', width=2)
                    pen_frac = pg.mkPen(color='m', width=2)

                    self.plot_widget.plot(x, y_raw, pen=pen_raw, name="Raw AU280")
                    self.plot_widget.plot(x, y_smooth, pen=pen_smooth, name="Smoothed AU280")
                    self.plot_widget.plot(x, y_frac, pen=pen_frac, name="Fraction")
                                       
                    # --- PumpB % Plotting (Reference Only; not smoothed) ---
                    if 'PumpB_percent' in df.columns and df['PumpB_percent'].notna().any() and df['PumpB_percent'].any():
                        x = df["Eluate_Volume (ml)"]
                        pumpB_percent_data = df['PumpB_percent'].values

                        # Initialize right axis if not already present
                        if not hasattr(self.plot_widget, 'right_axis') or self.plot_widget.right_axis is None:
                            right_axis = pg.ViewBox()
                            self.plot_widget.scene().addItem(right_axis)
                            self.plot_widget.getPlotItem().showAxis('right')
                            self.plot_widget.getPlotItem().getAxis('right').linkToView(right_axis)
                            self.plot_widget.getPlotItem().getAxis('right').setLabel('PumpB %', units='%')
                            right_axis.setXLink(self.plot_widget)
                            self.plot_widget.right_axis = right_axis
                            self.plot_widget.getPlotItem().getAxis('right').setRange(0, 100)
                            self.plot_widget.right_axis.setYRange(0, 100)

                        # Clear previous PumpB plot if any
                        if hasattr(self.plot_widget, 'right_axis') and self.plot_widget.right_axis is not None:
                            self.plot_widget.right_axis.clear()

                        # Plot PumpB % as dashed red line
                        pen_pumpB = pg.mkPen(color='r', width=2, style=pg.QtCore.Qt.DashLine)
                        curve_pumpB = pg.PlotCurveItem(x=x.values, y=pumpB_percent_data, pen=pen_pumpB, name='PumpB %')
                        self.plot_widget.right_axis.addItem(curve_pumpB)
                        
                        # Prevent duplicate legend entry
                        legend_items = [item[1].text for item in self.plot_widget.plotItem.legend.items]
                        if 'PumpB %' not in legend_items:
                            self.plot_widget.plotItem.legend.addItem(curve_pumpB, 'PumpB %')


                        # Sync right axis view
                        def update_views():
                            if hasattr(self.plot_widget, 'right_axis') and self.plot_widget.right_axis is not None:
                                self.plot_widget.right_axis.setGeometry(self.plot_widget.getPlotItem().vb.sceneBoundingRect())
                                self.plot_widget.right_axis.linkedViewChanged(self.plot_widget.getPlotItem().vb, self.plot_widget.right_axis.XAxis)

                        self.plot_widget.getPlotItem().vb.sigResized.connect(update_views)



                    self.plot_widget.setYRange(0, max_y)
                    self.plot_widget.setXRange(0, x_max)

                    # Peak labeling
                    if peak_id_on:
                        df["Peak_ID"] = ""
                        for i, peak in enumerate(peaks, start=1):
                            peak_x = x.iloc[peak]
                            peak_y = y_smooth[peak]
                            label = pg.TextItem(text=str(i), color='w', anchor=(0.5, 1.0))
                            label.setPos(peak_x, peak_y)
                            self.plot_widget.addItem(label)
                            df.at[peak, "Peak_ID"] = f"Peak_{i}"

                        for i, idx in enumerate(frac_marks, start=1):
                            mark_x = x.iloc[idx]
                            mark_y = y_frac[idx]
                            label = pg.TextItem(text=f"f{i}", color='w', anchor=(0.5, 1.0))
                            label.setPos(mark_x, mark_y)
                            self.plot_widget.addItem(label)

                    column_type = metadata.get("Column_type", "Unknown Column")
                    run_datetime = metadata.get("Year/Date/Time", "Unknown Time")
                    flowrate = metadata.get("Flowrate (ml/min)", "N/A")
                    plot_title = f"<b><br>{column_type}: {run_datetime}</b><br>Flowrate: {flowrate} ml/min"
                    self.plot_widget.setTitle(plot_title, size='12pt', color='w')

                    dialog.df = df
                    dialog.metadata = metadata

            except Exception as e:
                print(f"Error during smoothing: {e}")

        dialog.parameters_changed.connect(apply_and_plot)
        apply_and_plot()
        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            df = dialog.df
            metadata = dialog.metadata
            window_length, polyorder, peak_id_on, distance, baseline_on, lam, p, max_iter = dialog.get_values()
            
            base_name = os.path.splitext(os.path.basename(self.csv_path))[0]
            default_dir = os.path.join(self.basepath, 'Scanning_log_files', 'Processed_data_and_plots')
            os.makedirs(default_dir, exist_ok=True)
            save_dir = QFileDialog.getExistingDirectory(self, "Select Save Directory", default_dir, QFileDialog.Option.ShowDirsOnly)

            if save_dir:
                processed_csv = os.path.join(save_dir, f"{base_name}_processed.csv")
                processed_png = os.path.join(save_dir, f"{base_name}_processed.png")

                written_fields = set()

                with open(processed_csv, 'w', encoding='utf-8') as f:
                    f.write("Parameter,Value\n")

                    # Write metadata
                    for key in ["Column_type", "Year/Date/Time"]:
                        if key in metadata and key not in written_fields:
                            f.write(f"{key},{metadata[key]}\n")
                            written_fields.add(key)

                    # Write run notes (only once per field)
                    notes_filename = f"{base_name}_run_notes.csv"
                    notes_path = os.path.join(self.basepath, 'Scanning_log_files', notes_filename)
                    if os.path.exists(notes_path):
                        with open(notes_path, 'r', encoding='utf-8') as notes_file:
                            reader = csv.reader(notes_file)
                            next(reader)# Skip header
                            for row in reader:
                                if len(row) == 2 and row[0] not in written_fields:
                                    f.write(f"{row[0]},{row[1]}\n")
                                    written_fields.add(row[0])
                        
                    # Save peak processing parameters
                    f.write(f"\n")
                    f.write(f"Processing parameters\n")
                    f.write(f"AsLS Baseline,{'ON' if baseline_on else 'OFF'}\n")
                    if baseline_on:
                        f.write(f"AsLS lambda,{lam}\n")
                        f.write(f"AsLS p,{p}\n")
                        f.write(f"AsLS max_iter,{max_iter}\n")
                    f.write(f"SG Window Length,{window_length}\n")
                    f.write(f"SG Polynomial Order,{polyorder}\n")
                    f.write("\n") # Blank line between metadata and data                 
                    df[["Eluate_Volume (ml)", "Chan1_AU280 (AU)", "Chan1_AU280_Smoothed (AU)", "Frac_Mark_Scaled", "Peak_ID"]].to_csv(f, index=False)

                exporter = ImageExporter(self.plot_widget.plotItem)
                exporter.export(processed_png)

                print(f"Saved: {processed_csv}")
                print(f"Saved: {processed_png}")
            else:
                print("Save canceled: No directory selected.")
        else:
            print("Dialog closed without saving. Clearing plot.")
            self.plot_widget.clear()
            self.plot_widget.setTitle("")
            self.csv_path = None            
   
    def toggle_pump_calibration(self):
        print("Pump_Calibration Button clicked")
        #self.toggle_pump_calibration_mode = 'OFF'

    def toggle_divert_valve(self):
        if not self.divert_valve_mode:
            #self.connection.sendall("DIVERTER_VALVE_ON".encode('utf-8'))
            self.divert_valve_button.setText("Diverter(ON)")
            self.divert_valve_mode = True
            if self.method_editor.steps:
                self.method_editor.steps[-1]["Diverter"] = self.divert_valve_mode
                self.method_editor.update_table()
        else:
            #self.connection.sendall("DIVERTER_VALVE_OFF".encode('utf-8'))
            self.divert_valve_button.setText("Diverter(OFF)")
            self.divert_valve_mode = False
            if self.method_editor.steps:
                self.method_editor.steps[-1]["Diverter"] = self.divert_valve_mode
                self.method_editor.update_table()

    def start_connection_monitor(self):
        self.connection_thread = threading.Thread(target=self.monitor_connection, daemon=True)
        self.connection_thread.start()

    def monitor_connection(self):
        while True:
            if self.connection is None or self.connection.fileno() == -1:
                print("Attempting to establish connection...")
                self.connection = self.server.accept_connection()
                self.connection_status_label.setText("FPLC connected")
                self.connection_status_label.setStyleSheet("background-color: green; color: white; border: 1px solid black;")
                self.connection_established.emit() #Emit signal to notify connection is established

                if not hasattr(self, 'listener') or self.listener is None:
                    self.listener = ReceiveClientSignalsAndData(self.connection)
                    self.listener.pumpA_wash_completed_signal.connect(self.handle_pumpA_wash_completed)
                    self.listener.pumpB_wash_completed_signal.connect(self.handle_pumpB_wash_completed)
                    self.listener.fraction_collector_error_signal.connect(self.handle_fraction_collector_error)
                    self.listener.fraction_collector_error_cleared_signal.connect(self.handle_fraction_collector_error_cleared)
                    self.listener.pumpA_error_signal.connect(self.handle_PumpA_error)
                    self.listener.pumpA_error_cleared_signal.connect(self.handle_PumpA_error_cleared)
                    self.listener.pumpB_error_signal.connect(self.handle_PumpB_error)
                    self.listener.pumpB_error_cleared_signal.connect(self.handle_PumpB_error_cleared)               
                    self.listener.disconnected_signal.connect(self.handle_disconnection)
                    self.listener.stop_save_signal.connect(self.stop_save_acquisition)
                    self.listener.pumpA_volume_signal.connect(self.update_volume_delivered_progress)
                    self.listener.pumpA_volume_signal.connect(self.on_pumpA_volume_update)
                    self.listener.gradient_volume_signal.connect(self.update_volume_delivered_progress)
                    self.listener.gradient_volume_signal.connect(self.on_gradient_volume_update)
                    self.listener.valve_error_signal.connect(self.handle_valve_error)
                    self.listener.valve_position_signal.connect(self.handle_valve_position)
                    if self.worker:
                        self.listener.data_received_signal.connect(self.worker.handle_data_received)

                    self.listener.start()
            time.sleep(5)

    def open_solvent_exchange_dialog(self):
        if not hasattr(self, 'solvent_exchange_dialog') or not self.solvent_exchange_dialog.isVisible():
            self.solvent_exchange_dialog = SolventExchangeDialog(self)
            self.solvent_exchange_dialog.setModal(True)
            self.solvent_exchange_dialog.show() #.show() ensures the dialog is modal and non-blocking

    def set_solvent_button_enabled(self, enabled):
        self.pump_wash_button.setEnabled(enabled)
        if enabled:
            self.pump_wash_button.setStyleSheet("")# Reset to default
        else:
            self.pump_wash_button.setStyleSheet("color: gray; background-color: #2e2e2e;")

    def handle_pumpA_wash_completed(self):
        print("[DEBUG] PumpA wash completed signal received")
        self.pumpA_wash_done = True
        if hasattr(self, 'solvent_exchange_dialog') and self.solvent_exchange_dialog.isVisible():
            self.solvent_exchange_dialog.pumpA_button.setText("PumpA_Wash-Completed")
            self.solvent_exchange_dialog.pumpA_button.setStyleSheet("")
        self.check_if_wash_complete()

    def handle_pumpB_wash_completed(self):
        print("[DEBUG] PumpB wash completed signal received")
        self.pumpB_wash_done = True
        if hasattr(self, 'solvent_exchange_dialog') and self.solvent_exchange_dialog.isVisible():
            self.solvent_exchange_dialog.pumpB_button.setText("PumpB_Wash-Completed")      
            self.solvent_exchange_dialog.pumpB_button.setStyleSheet("")
        self.check_if_wash_complete()

    def check_if_wash_complete(self):
        print(f"[DEBUG] pumpA_wash_started: {self.pumpA_wash_started}, pumpA_wash_done: {self.pumpA_wash_done}")
        print(f"[DEBUG] pumpB_wash_started: {self.pumpB_wash_started}, pumpB_wash_done: {self.pumpB_wash_done}")

        if ((self.pumpA_wash_started and self.pumpA_wash_done) and
            (self.pumpB_wash_started and self.pumpB_wash_done)) or \
            (self.pumpA_wash_started and not self.pumpB_wash_started and self.pumpA_wash_done) or \
            (self.pumpB_wash_started and not self.pumpA_wash_started and self.pumpB_wash_done):
            print("[DEBUG] All required washes completed. Closing dialog.")
            if hasattr(self, 'solvent_exchange_dialog') and self.solvent_exchange_dialog.isVisible():
                self.solvent_exchange_dialog.close()
            self.reset_wash_flags()

    def reset_wash_flags(self):
        self.pumpA_wash_started = False
        self.pumpB_wash_started = False
        self.pumpA_wash_done = False
        self.pumpB_wash_done = False
        
            
    def update_volume_delivered_progress(self, volume_delivered: float):
        if self.run_volume > 0:
            percent = max(0, min(100, int((volume_delivered / self.run_volume) * 100)))
            current_mode = "Isocratic"
            if 0 <= self.current_step_index < len(self.method_sequence):
                current_mode = self.method_sequence[self.current_step_index].get("Pump Mode", "Isocratic")
            label = "PumpA" if current_mode == "Isocratic" else "Gradient"
            self.volume_delivered_progress_bar.setValue(percent)
            self.volume_delivered_progress_bar.setFormat(f"{label}: {volume_delivered:.2f} ml ({percent}%)")
        else:
            self.volume_delivered_progress_bar.setValue(0)
            self.volume_delivered_progress_bar.setFormat("Idle")

    def on_pumpA_volume_update(self, volume):
        self.update_volume_delivered_progress(volume)
        if self.run_volume > 0 and volume >= self.run_volume:
            self.handle_next_step()

    def on_gradient_volume_update(self, volume):
        self.update_volume_delivered_progress(volume)
        if self.run_volume > 0 and volume >= self.run_volume:
            self.handle_next_step()

    def run_acquisition(self):
        if self.worker is not None and self.worker.is_running:
            print("Acquisition already running.")
            return
        self.update_plot_title()

        self.worker = Worker(self.logger.append_data_row, self, self.selected_uv_monitor, self.selected_AUFS_value, self.connection)
        self.listener.data_received_signal.connect(self.worker.handle_data_received)
        self.worker.data_signal.connect(self.update_plot_data)
        #self.worker.finished.connect(self.enable_buttons)
        self.worker.error_signal.connect(self.handle_fraction_collector_error)
        self.worker.error_cleared_signal.connect(self.handle_fraction_collector_error_cleared)
        self.thread = threading.Thread(target=self.worker.run, name="WorkerThread")
        self.thread.start()

    def update_plot_data(self, elapsed_time, frac_mark, Chan1, Chan1_AU280, Chan2, pumpB_percent): #added , pumpB_percent 09-27-25
        self.elapsed_time_data.append(elapsed_time)
        self.chan1_data.append(Chan1)
        self.chan1_AU280_data.append(Chan1_AU280)
        self.chan2_data.append(Chan2)
        self.pumpB_percent_data.append(pumpB_percent)

        eluate_volume = elapsed_time * (self.flowrate / 60)
        self.eluate_volume_data.append(eluate_volume)

        data_row = {
            "Elapsed_Time (sec)": elapsed_time,
            "Eluate_Volume (ml)": eluate_volume,
            "Frac_Mark": frac_mark,
            "Chan1 (volt)": Chan1,
            "Chan1_AU280 (AU)": Chan1_AU280,
            "Chan2": Chan2,
            "PumpB_percent": pumpB_percent
        }

        if not self.metadata_written:
            metadata = {
                "RUN_VOLUME (ml)": self.run_volume,
                "Year/Date/Time": self.RunDateTime,
                "Column_type": self.selected_column_type,
                "AUFS_setting": self.selected_AUFS_value,
                "UV_monitor": self.selected_uv_monitor,
                "UV_monitor_FS_value (Volts)": self.uv_monitor_FS_value,
                "Flowrate (ml/min)": self.flowrate
            }
            
            #full_metadata = {**data_row, **metadata, **self.user_notes}
            self.logger.write_metadata({**data_row, **metadata}) #change to self.logger.write_metadata(full_metadata)
            self.metadata_written = True
        else:
            self.logger.append_data_row(data_row)

        if frac_mark == 1.0:
            frac_mark_value = 0.1 * self.max_y_value
        else:
            frac_mark_value = 0.0
        self.frac_mark_data.append(frac_mark_value)

        self.max_y_value = update_plot(
            self.plot_widget,
            self.elapsed_time_data,
            self.eluate_volume_data,
            self.chan1_AU280_data,
            self.chan2_data,
            self.frac_mark_data,
            self.run_volume,
            self.max_y_value,
            self.pumpB_percent_data
        )

        if eluate_volume >= self.run_volume:
            self.stop_save_acquisition()
            # Check if the current step's End Action is "Stop"
            method_sequence = self.method_editor.get_method_sequence()
            if method_sequence and method_sequence[-1].get("End Action") == "Stop":
                self.handle_method_stop()

    def open_run_notes_dialog(self):
        dialog = NotesDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.user_notes = dialog.get_notes()
            self.notes_timestamp = self.RunDateTime
            #self.notes_timestamp = datetime.strftime(datetime.now(), "%Y_%b_%d_%H%M%S")
            #self.logger.write_run_notes(self.user_notes, self.notes_timestamp)
            #print("Run notes saved:", self.user_notes)
        else:
            print("Run notes dialog canceled.")

    def stop_save_acquisition(self):
        if self.acquisition_stopped:
            return
        self.acquisition_stopped = True
                
        if self.worker is not None and self.worker.is_running:
            self.worker.stop()
            self.worker.is_running = False
        if self.thread is not None:
                self.thread.join()
                self.thread = None

        self.show_save_dialog()
        self.clear_plot_and_reset()
        self.run_notes_written = False
        self.method_pause_button.setStyleSheet("")
        self.method_stop_button.setStyleSheet("")
        self.set_all_buttons_enabled(True)
        self.reset_progress_bar()

    def show_save_dialog(self):
        dialog = SaveDialog(self)
        dialog.accepted.connect(self.save_data)
        dialog.rejected.connect(self.clear_plot_and_reset)
        #dialog.finished.connect(self.enable_buttons)
        dialog.exec()

    def save_data(self):
        self.logger.save_final_csv_and_plot(self.plot_widget, self.RunDateTime)
        self.clear_data()
        self.plot_widget.clear()
        print('Plot cleared and system reset. Ready for next acquisition.')

    def clear_plot_and_reset(self):
        self.acquisition_stopped = False
        self.clear_data()
        self.plot_widget.clear()

        # Clear the legend (added to clear pumpB % legend)
        if self.plot_widget.plotItem.legend:
            try:
                self.plot_widget.plotItem.legend.clear()
                print("Legend cleared successfully.")
            except Exception as e:
                print(f"Error clearing legend: {e}")

        # Safely clear PumpB axis
        try:
            if hasattr(self.plot_widget, 'right_axis') and self.plot_widget.right_axis is not None:
                try:
                    if self.plot_widget.right_axis.scene() is self.plot_widget.scene():
                        self.plot_widget.scene().removeItem(self.plot_widget.right_axis)
                except Exception as e:
                    print(f"[DEBUG] removeItem failed: {e}")

                try:
                    right_axis_obj = self.plot_widget.getPlotItem().getAxis('right')
                    if right_axis_obj is not None:
                        self.plot_widget.getPlotItem().hideAxis('right')
                except Exception as e:
                    print(f"[DEBUG] axis hide failed: {e}")

                try:
                    self.plot_widget.right_axis.setParentItem(None)
                except Exception as e:
                    print(f"[DEBUG] setParentItem(None) failed: {e}")

                # Optional: disconnect sigResized
                try:
                    self.plot_widget.getPlotItem().vb.sigResized.disconnect()
                except Exception:
                    pass  # Ignore if not connected

                self.plot_widget.right_axis = None
                print("PumpB axis cleared successfully.")
        except Exception as e:
            print(f"Error clearing PumpB axis: {e}")
       
        self.RunDateTime = None
        self.notes_timestamp = None
        self.run_notes_written = False
        self.update_plot_title()
        self.metadata_written = False
        self.logger.clear_data()
        print('Plot cleared and system reset. Ready for next acquisition.')

    def reset_progress_bar(self):
        self.volume_delivered_progress_bar.setValue(0)
        self.volume_delivered_progress_bar.setFormat("Idle")

    def clear_data(self):
        self.elapsed_time_data.clear()
        self.eluate_volume_data.clear()
        self.frac_mark_data.clear()
        self.chan1_data.clear()
        self.chan1_AU280_data.clear()
        self.chan2_data.clear()
        self.pumpB_percent_data.clear()
        print('Data cleared. Ready for next acquisition.')

    #def enable_buttons(self):
        #print('Buttons enabled')
        #self.run_volume_button.setEnabled(True)
        #self.start_button.setEnabled(True)

    def update_plot_title(self):
        timestamp = self.RunDateTime if self.RunDateTime else "Not Started"
        plot_title = (
            f"<b><br>{self.selected_column_type}: {timestamp}</b>"
            f"<br>Flowrate: {self.flowrate: .1f} ml/min, "
            f"{self.selected_uv_monitor}: {self.selected_AUFS_value: .3f} AUFS"
        )
        self.plot_widget.setTitle(plot_title, size='12pt', color='w')
        if self.selected_uv_monitor == "Pharmacia UV MII":
            self.max_y_value = self.selected_AUFS_value
        elif self.selected_uv_monitor == "Uvcord SII":
            self.max_y_value = self.selected_AUFS_value
        self.plot_widget.setYRange(0, self.max_y_value)


    def open_pause_dialog(self):
        dialog = PauseDialog(self)
        if self.connection is None or self.connection.fileno() == -1:
            self.connection = self.server.accept_connection()
        self.connection.sendall('PAUSE_ADC'.encode('utf-8'))
        print("PAUSE_ADC sent to client")
        if self.worker is not None:
            self.worker.pause()

        if dialog.exec() == QDialog.DialogCode.Accepted:
            if self.connection is None or self.connection.fileno() == -1:
                self.connection = self.server.accept_connection()
            self.connection.sendall('RESUME_ADC'.encode('utf-8'))
            print("RESUME_ADC sent to client")
            if self.worker is not None:
                self.worker.resume()
                self.update_run_button_state("running")
                
        else:
            self.worker.pause()
            print("Paused the acquisition")

    def handle_fraction_collector_error(self, error_message):
        self.update_run_button_state("error")
        if self.error_dialog_open:
            return        
        print(f"Handling error: {error_message}")
        self.error_dialog_open = True
        self.error_dialog = FractionCollectorErrorDialog(self)
        self.error_dialog.label.setText(error_message)
        self.error_dialog.finished.connect(self.reset_error_dialog_flag)
        self.error_dialog.exec()
        
    def reset_error_dialog_flag(self): # added back in 0.4.9
        self.error_dialog_open = False
        
    def handle_PumpA_error(self, error_message):
        self.update_run_button_state("error")
        self.pump_errors["A"] = True
        self.show_pump_error_dialog()

    def handle_PumpB_error(self, error_message):
        self.update_run_button_state("error")
        self.pump_errors["B"] = True
        self.show_pump_error_dialog()

    def handle_PumpA_error_cleared(self, message):
        self.pump_errors["A"] = False
        self.update_or_close_pump_error_dialog()
        self.restore_run_button_state_after_error()

    def handle_PumpB_error_cleared(self, message):
        self.pump_errors["B"] = False
        self.update_or_close_pump_error_dialog()
        self.restore_run_button_state_after_error()

    def show_pump_error_dialog(self):
        if not hasattr(self, 'pump_error_dialog') or not self.pump_error_dialog.isVisible():
            self.pump_error_dialog = PumpErrorDialog(self)
            self.pump_error_dialog.update_error_list(self.pump_errors)
            self.pump_error_dialog.show()
        else:
            self.pump_error_dialog.update_error_list(self.pump_errors)

    def update_or_close_pump_error_dialog(self):
        if any(self.pump_errors.values()):
            self.pump_error_dialog.update_error_list(self.pump_errors)
        else:
            self.pump_error_dialog.accept()        

    def handle_fraction_collector_error_cleared(self, message):
        print(f"Handling error cleared: {message}")
        if hasattr(self, 'error_dialog'):
            print(f"Dialog visible: {self.error_dialog.isVisible()}")
            self.error_dialog.set_error_cleared()
            self.error_dialog.exit_error_dialog()
        self.restore_run_button_state_after_error()

    def handle_valve_error(self, message):
        QMessageBox.critical(self, "Valve Error", message)
        self.handle_method_stop()

    def handle_valve_position(self, position):
        print(f"Valve Position: Valve successfully moved to: {position}")
        #QMessageBox.information(self, "Valve Position", f"Valve successfully moved to: {position}")
        

    def handle_disconnection(self):
        print("Client disconnected. Attempting to reconnect...")
        if self.listener:
            self.listener.stop()
            self.listener = None
        self.connection = None
        self.connection_status_label.setText("FPLC not connected")
        self.connection_status_label.setStyleSheet("background-color: red; color: white; border: 1px solid black;")
        #self.update_manual_controls()

    def close_application(self):
        self.close()

    def closeEvent(self, event):
        self.is_running = False
        if self.thread is not None:
            self.thread.join()
        event.accept()
