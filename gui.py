#gui.py (ver0.2)
# Imports and setup
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
    QGridLayout, QDialog, QDialogButtonBox
)
from PySide6.QtCore import Signal, QObject, Qt
from PySide6.QtGui import QFont
import pyqtgraph as pg
import socket
from network import FPLCServer
from hardware import set_gpio17, toggle_gpio17
from plotting import create_plot_widget, update_plot
from data_logger import DataLogger
from listener import ReceiveClientSignalsAndData





class OpenMethodModeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Method Options")
        self.setMinimumWidth(400)

        layout = QVBoxLayout()
        font = self.font()
        font.setPointSize(16)
        self.setFont(font)
        label = QLabel("Choose an option:")
        layout.addWidget(label)

        self.buttons = QDialogButtonBox()
        self.exit_button = self.buttons.addButton("Exit", QDialogButtonBox.ButtonRole.RejectRole)
        self.open_button = self.buttons.addButton("Open Method File", QDialogButtonBox.ButtonRole.ActionRole)
        self.create_button = self.buttons.addButton("Create New Method", QDialogButtonBox.ButtonRole.AcceptRole)

        layout.addWidget(self.buttons)
        self.setLayout(layout)

        self.buttons.clicked.connect(self.on_button_clicked)
        self.selected_option = None

    def on_button_clicked(self, button):
        if button == self.exit_button:
            self.selected_option = "Exit"
            self.reject()
        elif button == self.open_button:
            self.selected_option = "Open"
            self.accept()
        elif button == self.create_button:
            self.selected_option = "Create"
            self.accept()


class RunTimeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Run Time")
        self.setMinimumWidth(400)  # Adjust the width as needed
        layout = QVBoxLayout()

        # Create a grid layout for labels and spin boxes
        grid_layout = QGridLayout()

        # Create spin boxes for hours, minutes, and seconds
        self.hr_spinbox = QSpinBox()
        self.hr_spinbox.setRange(0, 24)  # 0 to 24 hours
        self.hr_spinbox.setMinimumWidth(75)
        self.hr_spinbox.setMinimumHeight(100)

        self.min_spinbox = QSpinBox()
        self.min_spinbox.setRange(0, 59)  # 0 to 59 minutes
        self.min_spinbox.setMinimumWidth(75)
        self.min_spinbox.setMinimumHeight(100)

        self.sec_spinbox = QSpinBox()
        self.sec_spinbox.setRange(0, 59)  # 0 to 59 seconds
        self.sec_spinbox.setMinimumWidth(75)
        self.sec_spinbox.setMinimumHeight(100)

        # Apply custom styles to increase contrast of up/down arrows
                # Apply custom styles to increase contrast of up/down arrows; for dark background change to background-color: #444444;  /* Dark background for buttons *
        # use #cccccc for light background for up-down arrow background
        style = """
        QSpinBox {
            background-color: #2c2c2c;  /* Dark background for the spin box */
            color: #ffffff;  /* White text */
            border: 1px solid #444444;  /* Border color */
            font-size: 36px;  /* Increase font size */
        }
        QSpinBox::up-button, QSpinBox::down-button {
            background-color: #444444;  /* dark background for buttons */
            border: none;  /* Remove border */
            width: 40px;  /* Increase button width */
            height: 40px;  /* Increase button height */
            background-position: center;  /* Center the images */
            background-repeat: no-repeat;  /* Do not repeat the images */
        }
        QSpinBox::up-button {
            background-image: url(/home/sybednar/FPLC_controller_venv/FPLC_server/FPLC_GUI_customization/uparrow_3pt_white.png);  /* Replace inside of () with your up arrow image */
        }
        QSpinBox::down-button {
            background-image: url(/home/sybednar/FPLC_controller_venv/FPLC_server/FPLC_GUI_customization/downarrow_3pt_white.png);  /* Replace with your down arrow image */
        }
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {
            background-color: #555555;  /* Lighter background on hover */
        }
        """
        
        self.hr_spinbox.setStyleSheet(style)
        self.min_spinbox.setStyleSheet(style)
        self.sec_spinbox.setStyleSheet(style)

        font = self.font()
        font.setPointSize(24)  # Increase font size
        self.setFont(font)

        grid_layout.addWidget(QLabel("Hr"), 0, 0, alignment=Qt.AlignmentFlag.AlignCenter)
        grid_layout.addWidget(QLabel("Min"), 0, 1, alignment=Qt.AlignmentFlag.AlignCenter)
        grid_layout.addWidget(QLabel("Sec"), 0, 2, alignment=Qt.AlignmentFlag.AlignCenter)

        # Add spin boxes to the grid layout
        grid_layout.addWidget(self.hr_spinbox, 1, 0)
        grid_layout.addWidget(self.min_spinbox, 1, 1)
        grid_layout.addWidget(self.sec_spinbox, 1, 2)

        layout.addLayout(grid_layout)  # Add the grid layout to the main layout

        font.setPointSize(16)  # Increase font size
        self.setFont(font)
        self.confirm_button = QPushButton("Confirm")
        self.confirm_button.clicked.connect(self.accept)
        layout.addWidget(self.confirm_button)

        self.setLayout(layout)
        self.load_saved_values()  # Load previously saved values

    def load_saved_values(self):
        # Load saved values from the parent (assuming you save them there)
        if hasattr(self.parent(), 'saved_run_time'):
            hr, min, sec = self.parent().saved_run_time
            self.hr_spinbox.setValue(hr)
            self.min_spinbox.setValue(min)
            self.sec_spinbox.setValue(sec)

    def accept(self):
        # Save the values upon acceptance
        self.parent().saved_run_time = (
            self.hr_spinbox.value(),
            self.min_spinbox.value(),
            self.sec_spinbox.value()
        )
        super().accept()

    def get_run_time(self):
        return (self.hr_spinbox.value() * 3600) + (self.min_spinbox.value() * 60) + self.sec_spinbox.value()

class FlowRateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set FlowRate")
        self.setMinimumWidth(200)  # Adjust the width as needed

        # Create the main vertical layout
        main_layout = QVBoxLayout()

        # Create a horizontal layout for the spin box and label
        h_layout = QHBoxLayout()

        # Create a double spin box for ml/min
        self.ml_per_min_spinbox = QDoubleSpinBox()
        self.ml_per_min_spinbox.setRange(0.0, 9.9)  # 0 to 9.9 ml/min
        self.ml_per_min_spinbox.setSingleStep(0.1)  # Increment by 0.1
        self.ml_per_min_spinbox.setDecimals(1)  # Display one decimal place
        self.ml_per_min_spinbox.setMinimumWidth(75)
        self.ml_per_min_spinbox.setMinimumHeight(100)

        # Apply custom styles to increase contrast of up/down arrows
        style = """
        QDoubleSpinBox {
            background-color: #2c2c2c;  /* Dark background for the spin box */
            color: #ffffff;  /* White text */
            border: 1px solid #444444;  /* Border color */
            font-size: 36px;  /* Increase font size */
        }
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
            background-color: #444444;  /* Dark background for buttons */
            border: none;  /* Remove border */
            width: 40px;  /* Increase button width */
            height: 40px;  /* Increase button height */
            background-position: center;  /* Center the images */
            background-repeat: no-repeat;  /* Do not repeat the images */
        }
        QDoubleSpinBox::up-button {
            background-image: url(/home/sybednar/FPLC_controller_venv/FPLC_server/FPLC_GUI_customization/uparrow_3pt_white.png);
        }
        QDoubleSpinBox::down-button {
            background-image: url(/home/sybednar/FPLC_controller_venv/FPLC_server/FPLC_GUI_customization/downarrow_3pt_white.png);
        }
        QDoubleSpinBox::up-button:hover, QSpinBox::down-button:hover {
            background-color: #555555;  /* Lighter background on hover */
        }
        """
        self.ml_per_min_spinbox.setStyleSheet(style)
        font = self.font()
        font.setPointSize(24)  # Increase font size
        self.setFont(font)

        # Add the spin box and label to the horizontal layout
        h_layout.addWidget(self.ml_per_min_spinbox)
        h_layout.addWidget(QLabel("ml/min"), alignment=Qt.AlignmentFlag.AlignCenter)

        # Add the horizontal layout to the main vertical layout
        main_layout.addLayout(h_layout)

        font = self.font()
        font.setPointSize(16)
        self.setFont(font)

        self.confirm_button = QPushButton("Confirm")
        self.confirm_button.clicked.connect(self.accept)
        main_layout.addWidget(self.confirm_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(main_layout)
        self.load_saved_values()  # Load previously saved values
        
    def load_saved_values(self):
        # Load saved values from the parent (assuming you save them there)
        if hasattr(self.parent(), 'saved_flowrate'):
            ml_per_min = self.parent().saved_flowrate
            self.ml_per_min_spinbox.setValue(ml_per_min)

    def accept(self):
        # Save the values upon acceptance
        self.parent().saved_flowrate = self.ml_per_min_spinbox.value()
        super().accept()

    def get_flowrate(self):
        return self.ml_per_min_spinbox.value()

class RunTime_WarningDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Warning")
        self.setMinimumWidth(300)  # Adjust the width as needed
        layout = QVBoxLayout()

        self.label = QLabel("Set Run Time > 0 sec")
        layout.addWidget(self.label)

        self.confirm_button = QPushButton("Confirm")
        self.confirm_button.clicked.connect(self.accept)
        layout.addWidget(self.confirm_button)

        self.setLayout(layout)

class FlowRate_WarningDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Warning")
        self.setMinimumWidth(300)  # Adjust the width as needed
        layout = QVBoxLayout()
        self.label = QLabel("Set FlowRate > 0 ml/min")
        layout.addWidget(self.label)
        self.confirm_button = QPushButton("Confirm")
        self.confirm_button.clicked.connect(self.accept)
        layout.addWidget(self.confirm_button)
        self.setLayout(layout)

class AUFS_WarningDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Warning")
        self.setMinimumWidth(300)  # Adjust the width as needed
        layout = QVBoxLayout()
        self.label = QLabel("Set UVMonitor AUFS value > 0 AUFS")
        layout.addWidget(self.label)
        self.confirm_button = QPushButton("Confirm")
        self.confirm_button.clicked.connect(self.accept)
        layout.addWidget(self.confirm_button)
        self.setLayout(layout)

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

class ColumnTypeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        font = self.font()
        font.setPointSize(16)  # Increase font size
        self.setFont(font)
        self.setWindowTitle("Select Column Type")
        self.setMinimumWidth(300)

        layout = QVBoxLayout()

        self.combo_box = QComboBox()
        self.combo_box.addItems([
            "Superdex-200",
            "Superose-6",
            "Mono Q 5/50",
            "Mono S 5/50",
            "His Trap",
            "Other"
        ])
        layout.addWidget(self.combo_box)

        self.confirm_button = QPushButton("Confirm")
        self.confirm_button.clicked.connect(self.accept)  # Close dialog on confirm
        layout.addWidget(self.confirm_button)

        self.setLayout(layout)

# UV monitor AUFS setting Dialog class
class UV_Monitor_Dialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        font = self.font()
        font.setPointSize(16)  # Increase font size
        self.setFont(font)
        self.setWindowTitle("Set UV_Monitor/AUFS")
        self.setMinimumWidth(200)
        layout = QVBoxLayout()

        # First combo box to specify uv-monitor
        self.combo_box_uv_monitor = QComboBox()
        self.combo_box_uv_monitor.addItems(["Pharmacia UV MII", "BioRad EM1"])
        self.combo_box_uv_monitor.currentIndexChanged.connect(self.update_aufs_items)
        layout.addWidget(self.combo_box_uv_monitor)

        # Second combo box for AUFS values
        self.combo_box_aufs = QComboBox()
        self.combo_box_aufs.addItems([
            "2.000 AUFS", "1.000 AUFS", "0.500 AUFS", "0.200 AUFS", "0.100 AUFS",
            "0.050 AUFS", "0.020 AUFS", "0.010 AUFS", "0.005 AUFS", "0.002 AUFS", "0.001 AUFS"
        ])
        layout.addWidget(self.combo_box_aufs)

        self.confirm_button = QPushButton("Confirm")
        self.confirm_button.clicked.connect(self.accept)  # Close dialog on confirm
        layout.addWidget(self.confirm_button)
        self.setLayout(layout)

    def update_aufs_items(self):
        selected_uv_monitor_text = self.combo_box_uv_monitor.currentText()
        if selected_uv_monitor_text == "BioRad EM1":
            self.combo_box_aufs.clear()
            self.combo_box_aufs.addItems([
                "2.000 AUFS", "1.000 AUFS", "0.500 AUFS", "0.200 AUFS", "0.100 AUFS",
                "0.050 AUFS", "0.020 AUFS", "0.010 AUFS"
            ])
        else:
            self.combo_box_aufs.clear()
            self.combo_box_aufs.addItems([
                "2.000 AUFS", "1.000 AUFS", "0.500 AUFS", "0.200 AUFS", "0.100 AUFS",
                "0.050 AUFS", "0.020 AUFS", "0.010 AUFS", "0.005 AUFS", "0.002 AUFS", "0.001 AUFS"
            ])

    def accept(self):
        selected_aufs_text = self.combo_box_aufs.currentText()
        self.parent().selected_AUFS_value = float(selected_aufs_text.split()[0])
        selected_uv_monitor_text = self.combo_box_uv_monitor.currentText()
        if selected_uv_monitor_text == "Pharmacia UV MII":
            self.parent().uv_monitor_FS_value = 0.1
        elif selected_uv_monitor_text == "BioRad EM1":
            self.parent().uv_monitor_FS_value = 1.0
            if self.parent().selected_AUFS_value <= 0.01:
                self.parent().selected_AUFS_value = 0.01
        self.parent().selected_uv_monitor = selected_uv_monitor_text
        super().accept()   

class FractionCollectorErrorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Fraction Collector Error")
        self.setMinimumWidth(300)
        layout = QVBoxLayout()
        self.label = QLabel("Frac-200 error has occurred. \nClear error before continuing..")
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
            self.parent().stop_save_acquisition()# Activate the Stop and Save function
        else:
            QMessageBox.warning(self, "Error", "Please clear the fraction collector error before continuing.")

    def set_error_cleared(self):
        self.error_cleared = True # Update error status


class SolventExchangeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Solvent Exchange")
        self.setMinimumWidth(300)

        layout = QVBoxLayout()

        self.pumpA_button = QPushButton("PumpA (OFF)")
        #self.pumpA_button.setStyleSheet("background-color: lightgray;")
        self.pumpA_button.clicked.connect(self.toggle_pumpA)
        layout.addWidget(self.pumpA_button)

        self.pumpB_button = QPushButton("PumpB (OFF)")
        #self.pumpB_button.setStyleSheet("background-color: lightgray;")
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
            self.pumpA_button.setText("PumpA_Wash ON")
            self.pumpA_button.setStyleSheet("background-color: green; color: white;")
        else:
            self.pumpA_button.setText("PumpA_Wash OFF")
            self.pumpA_button.setStyleSheet("background-color: lightgray;")

    def toggle_pumpB(self):
        self.parent().wash_pumpB = not self.parent().wash_pumpB
        if self.parent().wash_pumpB:
            self.pumpB_button.setText("PumpB_Wash ON")
            self.pumpB_button.setStyleSheet("background-color: green; color: white;")
        else:
            self.pumpB_button.setText("PumpB_Wash OFF")
            self.pumpB_button.setStyleSheet("background-color: lightgray;")

    def start_wash(self):
        if self.parent().connection:
            if self.parent().wash_pumpA:
                print("WASH_A signal sent")
                self.parent().connection.sendall('WASH_PUMP_A'.encode('utf-8'))
            if self.parent().wash_pumpB:
                print("WASH_B signal sent")
                self.parent().connection.sendall('WASH_PUMP_B'.encode('utf-8'))

    def exit_dialog(self):
        self.parent().wash_pumpA = False
        self.parent().wash_pumpB = False
        self.pumpA_button.setText("PumpA OFF")
        self.pumpA_button.setStyleSheet("background-color: lightgray;")
        self.pumpB_button.setText("PumpB OFF")
        self.pumpB_button.setStyleSheet("background-color: lightgray;")
        self.close()

class pumpA_isocratic_Dialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PumpA Isocratic")
        self.setMinimumWidth(200)  # Adjust the width as needed

        # Create the main vertical layout
        main_layout = QVBoxLayout()

        # Create a horizontal layout for the spin box and label
        h_layout = QHBoxLayout()

        # Create a double spin box for ml/min
        self.pumpA_ml_spinbox = QDoubleSpinBox()
        self.pumpA_ml_spinbox.setRange(0, 99)  # 0 to 99 ml
        self.pumpA_ml_spinbox.setSingleStep(1)  # Increment by 1.0
        self.pumpA_ml_spinbox.setDecimals(1)  # Display one decimal place
        self.pumpA_ml_spinbox.setMinimumWidth(75)
        self.pumpA_ml_spinbox.setMinimumHeight(100)

        # Apply custom styles to increase contrast of up/down arrows
        style = """
        QDoubleSpinBox {
            background-color: #2c2c2c;  /* Dark background for the spin box */
            color: #ffffff;  /* White text */
            border: 1px solid #444444;  /* Border color */
            font-size: 36px;  /* Increase font size */
        }
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
            background-color: #444444;  /* Dark background for buttons */
            border: none;  /* Remove border */
            width: 40px;  /* Increase button width */
            height: 40px;  /* Increase button height */
            background-position: center;  /* Center the images */
            background-repeat: no-repeat;  /* Do not repeat the images */
        }
        QDoubleSpinBox::up-button {
            background-image: url(/home/sybednar/FPLC_controller_venv/FPLC_server/FPLC_GUI_customization/uparrow_3pt_white.png);
        }
        QDoubleSpinBox::down-button {
            background-image: url(/home/sybednar/FPLC_controller_venv/FPLC_server/FPLC_GUI_customization/downarrow_3pt_white.png);
        }
        QDoubleSpinBox::up-button:hover, QSpinBox::down-button:hover {
            background-color: #555555;  /* Lighter background on hover */
        }
        """
        self.pumpA_ml_spinbox.setStyleSheet(style)
        font = self.font()
        font.setPointSize(24)  # Increase font size
        self.setFont(font)

        # Add the spin box and label to the horizontal layout
        h_layout.addWidget(self.pumpA_ml_spinbox)
        h_layout.addWidget(QLabel("PumpA (ml)"), alignment=Qt.AlignmentFlag.AlignCenter)

        # Add the horizontal layout to the main vertical layout
        main_layout.addLayout(h_layout)

        font = self.font()
        font.setPointSize(16)
        self.setFont(font)

        self.confirm_button = QPushButton("Confirm")
        self.confirm_button.clicked.connect(self.accept)
        main_layout.addWidget(self.confirm_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(main_layout)
        self.load_saved_values()  # Load previously saved values
        
    def load_saved_values(self):
        # Load saved values from the parent (assuming you save them there)
        if hasattr(self.parent(), 'saved_pumpA_volume'):
            pumpA_ml = self.parent().saved_pumpA_volume
            self.pumpA_ml_spinbox.setValue(pumpA_ml)

    def accept(self):
        # Save the values upon acceptance
        self.parent().saved_pumpA_volume = self.pumpA_ml_spinbox.value()
        super().accept()

    def get_pumpA_volume(self):
        return self.pumpA_ml_spinbox.value()
    

# Worker class for background data acquisition
class Worker(QObject):
    data_signal = Signal(float, float, float, float, float)
    finished = Signal()
    error_signal = Signal(str)
    error_cleared_signal = Signal(str)

    def __init__(self, run_time, channels, write_to_csv_callback, main_app, selected_uv_monitor, selected_AUFS_value, connection):
        super().__init__()
        self.run_time = run_time
        self.channels = channels
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
        if "Fraction Collector error" in message:
            if not self.error_emitted:
                self.error_signal.emit("Frac-200 error has occurred.\nClear error before continuing..")
                self.error_emitted = True
            return
        elif "Fraction Collector Error has been cleared" in message:
            self.error_cleared_signal.emit("Fraction Collector Error has been cleared")
            self.error_emitted = False
            return            

        values = message.split(',')
        if len(values) == 5:
            try:
                value1 = int(values[0])
                value2 = int(values[1])
                elapsed_time = float(values[2])
                eluate_volume = float(values[3])
                frac_mark = float(values[4])
                Chan1 = (value1 / 32768.0) * 0.256
                Chan2 = (value2 / 32768.0) * 0.256
                if self.selected_uv_monitor == "Pharmacia UV MII":
                    Chan1_AU280 = max(0.001, round(Chan1 * (self.selected_AUFS_value / 0.1), 4))
                elif self.selected_uv_monitor == "BioRad EM1":
                    Chan1_AU280 = max(0.001, round(Chan1 * (self.selected_AUFS_value / 1.0), 4))
                else:
                    Chan1_AU280 = Chan1
                self.data_signal.emit(elapsed_time, frac_mark, Chan1, Chan1_AU280, Chan2)
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
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(1024, 768)
        
        self.connection_status_label = QLabel("FPLC not connected", self)
        self.connection_status_label.setGeometry(848, 320, 150, 30)
        self.connection_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.connection_status_label.setStyleSheet("background-color: red; color: white; border: 1px solid black;")

        # Initialize state variables
        self.connection = None
        self.worker = None
        self.thread = None
        self.error_dialog_open = False
        self.channels = [0, 1]
        self.num_channels = len(self.channels)
        self.scan_rate = 10
        self.run_time = 0
        self.run_volume = 0
        self.is_running = False
        self.saved_run_time = (0, 0, 0)
        self.last_run_time = 0
        self.total_pause_duration = 0
        self.saved_flowrate = 0.0
        self.last_flowrate = 0.0
        self.selected_column_type = "Superdex-200"
        self.selected_AUFS_value = 0.0
        self.flowrate = 0.0
        self.RunDateTime = datetime.strftime(datetime.now(), "%Y_%b_%d_%H%M%S")
        self.uv_monitor_FS_value = 0.1
        self.max_y_value = self.selected_AUFS_value
        self.selected_uv_monitor = "Pharmacia UV MII"
        self.metadata_written = False
        self.gpio17_mode = 'OFF'
        self.manual_mode_enabled = False
        self.method_mode = None # Tracks 'Open', 'Create', or None
        self.wash_pumpA = False
        self.wash_pumpB = False
        self.elution_method = "Isocratic"
        self.pumpA_button = None
        self.pumpA_volume = 0
        self.saved_pumpA_volume = 0
        self.last_pumpA_volume = 0
        self.run_pumpA = False
        self.pumpB_button = None
        self.pump_listener = None
        

        # Data storage
        self.elapsed_time_data = []
        self.eluate_volume_data = []
        self.frac_mark_data = []
        self.chan1_data = []
        self.chan1_AU280_data = []
        self.chan2_data = []

        # Setup paths and logger
        self.basepath = '/home/sybednar/FPLC_controller_venv/Measurement_Computing'
        self.mypath = os.path.join(self.basepath, 'Scanning_log_files')
        self.metadata_fieldnames = [
        "RUNTIME (sec)", "Year/Date/Time", "Column_type", "AUFS_setting",
        "UV_monitor", "UV_monitor_FS_value (Volts)", "Flowrate (ml/min)"
        ]
        self.data_fieldnames = [
        "Elapsed_Time (sec)", "Eluate_Volume (ml)", "Frac_Mark",
        "Chan1 (volt)", "Chan1_AU280 (AU)", "Chan2"
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
        self.connection_status_label.setGeometry(848, 320, 150, 30)
        self.connection_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.connection_status_label.setStyleSheet("background-color: red; color: white; border: 1px solid black;")

        # Labels
        left_top_label = QLabel("Program Control", container)
        left_top_label.setGeometry(50, 20, 100, 30)
        left_top_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        left_middle_label = QLabel("Method Operate", container)
        left_middle_label.setGeometry(50, 160, 100, 30)
        left_middle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        right_label = QLabel("Data Analysis", container)
        right_label.setGeometry(874, 20, 100, 30)
        right_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Left-side buttons
        self.manual_mode_button = QPushButton("Manual (OFF)", container)
        self.manual_mode_button.setGeometry(50, 60, 100, 30)
        self.manual_mode_button.clicked.connect(self.handle_manual_mode_button_click)

        self.method_mode_button = QPushButton("Method", container)
        self.method_mode_button.setGeometry(50, 100, 100, 30)
        self.method_mode_button.clicked.connect(self.handle_method_mode_button_click)

        self.method_run_button = QPushButton("Run_Method", container)
        self.method_run_button.setGeometry(50, 200, 100, 30)
        self.method_run_button.clicked.connect(self.handle_method_run_button_click)

        self.method_pause_button = QPushButton("Pause_Method", container)
        self.method_pause_button.setGeometry(50, 240, 100, 30)
        self.method_pause_button.clicked.connect(self.handle_method_pause_button_click)

        self.method_stop_button = QPushButton("Stop_Method", container)
        self.method_stop_button.setGeometry(50, 280, 100, 30)
        self.method_stop_button.clicked.connect(self.handle_method_stop_button_click)

        # Right-side buttons
        self.Peak_ID_button = QPushButton("Peak_ID", container)
        self.Peak_ID_button.setGeometry(874, 60, 100, 30)
        self.Peak_ID_button.clicked.connect(self.handle_Peak_ID_button_click)

        self.Baseline_Corr_button = QPushButton("Baseline_Corr", container)
        self.Baseline_Corr_button.setGeometry(874, 100, 100, 30)
        self.Baseline_Corr_button.clicked.connect(self.handle_Baseline_Corr_button_click)

        self.Peak_Smoothing_button = QPushButton("Peak_Smoothing", container)
        self.Peak_Smoothing_button.setGeometry(874, 140, 100, 30)
        self.Peak_Smoothing_button.clicked.connect(self.handle_Peak_Smoothing_button_click)

        self.desktop_button = QPushButton("Desktop", container)
        self.desktop_button.setGeometry(874, 280, 100, 30)
        self.desktop_button.clicked.connect(self.close_application)

        # Settings and control buttons
        self.run_time_button = QPushButton("Set Run Time", container)
        self.run_time_button.setGeometry(212, 360, 100, 30)
        self.run_time_button.clicked.connect(self.open_run_time_dialog)

        self.UVMonitor_button = QPushButton("UVMonitor", container)
        self.UVMonitor_button.setGeometry(322, 360, 100, 30)
        self.UVMonitor_button.clicked.connect(self.open_UV_Monitor_dialog)

        self.FlowRate_button = QPushButton("FlowRate", container)
        self.FlowRate_button.setGeometry(432, 360, 100, 30)
        self.FlowRate_button.clicked.connect(self.open_flowrate_dialog)

        self.column_type_button = QPushButton("Column Type", container)
        self.column_type_button.setGeometry(542, 360, 100, 30)
        self.column_type_button.clicked.connect(self.open_column_type_dialog)

        self.gpio17_button = QPushButton("GPIO17_OFF", container)
        self.gpio17_button.setGeometry(652, 360, 100, 30)
        self.gpio17_button.clicked.connect(self.toggle_gpio17)

        self.start_button = QPushButton("Start", container)
        self.start_button.setGeometry(212, 400, 100, 30)
        self.start_button.clicked.connect(self.start_acquisition)

        self.pause_button = QPushButton("Pause", container)
        self.pause_button.setGeometry(322, 400, 100, 30)
        self.pause_button.clicked.connect(self.open_pause_dialog)

        self.stop_save_button = QPushButton("Stop and Save", container)
        self.stop_save_button.setGeometry(432, 400, 100, 30)
        self.stop_save_button.clicked.connect(self.stop_save_acquisition)
        
        self.divert_valve_button = QPushButton("Diverter(OFF)", container)
        self.divert_valve_button.setGeometry(542, 400, 100, 30)
        #self.divert_valve_button.clicked.connect(self.toggle_divert_valve)
               
        self.injection_valve_button = QPushButton("Injection_Valve", container)
        self.injection_valve_button.setGeometry(652, 400, 100, 30)

        # Additional labels
        settings_label = QLabel("Settings", container)
        settings_label.setGeometry(136, 360, 100, 30)
        settings_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        fraction_collector_label = QLabel("Fraction Collector", container)
        fraction_collector_label.setGeometry(110, 400, 100, 30)
        fraction_collector_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        Pumps_Valves_label = QLabel("Pumps and Valves", container)
        Pumps_Valves_label.setGeometry(108, 440, 100, 30)
        Pumps_Valves_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Pump and valve control buttons
        self.pump_wash_button = QPushButton("Solvent Change", container)
        self.pump_wash_button.setGeometry(212, 440, 100, 30)
        self.pump_wash_button.clicked.connect(self.open_solvent_exchange_dialog)

        self.isocratic_gradient_button = QPushButton("Isocratic", container)
        self.isocratic_gradient_button.setGeometry(322, 440, 100, 30)
        self.isocratic_gradient_button.clicked.connect(self.toggle_isocratic_gradient)

        self.pumpA_button = QPushButton("Pump_A", container) #Run/Standby
        self.pumpA_button.setGeometry(432, 440, 100, 30)
        self.pumpA_button.clicked.connect(self.open_pumpA_dialog)

        self.pumpB_button = QPushButton("Pump_B", container) #Run/Standby
        self.pumpB_button.setGeometry(542, 440, 100, 30)
        self.pumpB_button.clicked.connect(self.open_pumpB_dialog)

        self.standby_run_pumps_button = QPushButton("StandBy", container)
        self.standby_run_pumps_button.setGeometry(652, 440, 100, 30)
        self.standby_run_pumps_button.clicked.connect(self.Standby_Run_pumps)



    def handle_manual_mode_button_click(self):
        self.manual_mode_enabled = not self.manual_mode_enabled
        self.manual_mode_button.setText("Manual (ON)" if self.manual_mode_enabled else "Manual (OFF)")

        if self.manual_mode_enabled:
            print("Manual mode enabled")
        else:
            print("Manual moded disabled")
        self.update_manual_controls()

    def handle_method_mode_button_click(self):
        self.manual_mode_enabled = False # Disable manual mode when Method dialog is opened
        self.manual_mode_button.setText("Manual (OFF)")
        self.update_manual_controls()
        dialog = OpenMethodModeDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.selected_option == "Open":
                self.method_mode = "Open"
                print("Open Method File selected")
                # TODO: Add logic to open method file
            elif dialog.selected_option == "Create":
                self.method_mode = "Create"
                print("Create New Method selected")
                # TODO: Add logic to create new method
        else:
            # If user exits the dialog, re-enable manual mode
            self.manual_mode_enabled = True
            self.manual_mode_button.setText("Manual (ON)")
            self.update_manual_controls()
            print("Method dialog exited_Manual mode re-enabled")

    def handle_method_run_button_click(self):
        print("Left Button 3 clicked")

    def handle_method_pause_button_click(self):
        print("Left Button 4 clicked")
        
    def handle_method_stop_button_click(self):
        print("Left Button 5 clicked")

    def handle_Peak_ID_button_click(self):
        print("Peak_ID Button clicked")

    def handle_Baseline_Corr_button_click(self):
        print("Baseline_Corr Button, set order of polynomial and iterations of baseline calculation")

    def handle_Peak_Smoothing_button_click(self):
        print("Peak_Smoothing Button, set Savitzky-Golay window length and polyorder values")
   

    def update_manual_controls(self):
        is_connected = self.connection is not None and self.connection.fileno() != -1
        enable_controls = self.manual_mode_enabled and is_connected
        self.start_button.setEnabled(enable_controls)
        self.pause_button.setEnabled(enable_controls)
        self.stop_save_button.setEnabled(enable_controls)

    def toggle_gpio17(self):
        self.gpio17_mode = toggle_gpio17(self.gpio17_mode)
        self.gpio17_button.setText(f"GPIO17-{self.gpio17_mode}")
        if self.connection:
            self.connection.sendall('TOGGLE_LED'.encode('utf-8'))

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
                self.update_manual_controls()

                if not hasattr(self, 'listener') or self.listener is None:
                    self.listener = ReceiveClientSignalsAndData(self.connection)
                    self.listener.pumpA_wash_completed_signal.connect(self.handle_pumpA_wash_completed)
                    self.listener.fraction_collector_error_signal.connect(self.handle_fraction_collector_error)
                    self.listener.fraction_collector_error_cleared_signal.connect(self.handle_fraction_collector_error_cleared)

                    if self.worker:
                        self.listener.data_received_signal.connect(self.worker.handle_data_received)

                    self.listener.start()
            time.sleep(5)

    def open_solvent_exchange_dialog(self):
        self.solvent_exchange_dialog = SolventExchangeDialog(self)
        self.solvent_exchange_dialog.exec()
        
    def handle_pumpA_wash_completed(self):
        if self.pumpA_button:
            self.pumpA_button.setText("Pump OFF")
        if hasattr(self, 'solvent_exchange_dialog') and self.solvent_exchange_dialog.isVisible():
            self.solvent_exchange_dialog.close()
        
    def toggle_isocratic_gradient(self):
        if self.elution_method == "Isocratic":
            self.isocratic_gradient_button.setText("Gradient")
            self.elution_method = "Gradient"
            self.pumpB_button.setEnabled(True)
        elif self.elution_method == "Gradient":
            self.isocratic_gradient_button.setText("Isocratic")
            self.elution_method = "Isocratic"
            self.pumpB_button.setEnabled(False)
            
    def open_pumpA_dialog(self):
        if self.elution_method == "Isocratic":
            dialog = pumpA_isocratic_Dialog(self)                   
            if dialog.exec() == QDialog.DialogCode.Accepted:   
                new_pumpA_volume = dialog.get_pumpA_volume()  # Get the new volume from the dialog  
                if new_pumpA_volume > 0:  # Check if the new pumpA_volume is valid  
                    self.pumpA_volume = new_pumpA_volume  # Update the pumpA_volume  
                    self.last_pumpA_volume = new_pumpA_volume  # Save the last valid pumpA_volume                      
                    print(f"PumpA_Volume:{self.pumpA_volume} ml")
                    if self.connection:
                        try:
                            self.connection.sendall(f'PumpA_Volume:{self.pumpA_volume}'.encode('utf-8'))
                            print(f"Sent PumpA_Volume:{self.pumpA_volume} ml to client")
                        except socket.error as e:
                            print(f"Error sending PumpA_Volume: {e}")
                            self.handle_disconnection()
                else: 
                    # If the new pumpA_volume is invalid, keep the last valid pumpA_volume 
                    self.pumpA_volume = self.last_pumpA_volume     
            
        
    def open_pumpB_dialog(self):
        if self.elution_method == "Isocratic":
            self.pumpB_button.setEnabled(False)
        else:
            print("PumpB Button clicked") #placeholder for additional logic

    def Standby_Run_pumps(self):
        if self.pumpA_volume <= 0.0:
            set_pumpA_volume_warning_dialog = SetPumpAVolume_WarningDialog(self)
            if set_pumpA_volume_warning_dialog.exec() == QDialog.DialogCode.Accepted:
                self.open_pumpA_dialog()
            return

        if self.flowrate <= 0.0:
            flowrate_warning_dialog = FlowRate_WarningDialog(self)
            if flowrate_warning_dialog.exec() == QDialog.DialogCode.Accepted:
                self.open_flowrate_dialog()
            return

        if self.run_pumpA == False:
            self.run_pumpA = True
            self.standby_run_pumps_button.setText("Pumps Running")
            if self.connection is None or self.connection.fileno() == -1:
                self.connection = self.server.accept_connection()
            self.connection.sendall('START_PUMPS'.encode('utf-8'))

        else:
            self.run_pumpA = False
            self.standby_run_pumps_button.setText("StandBy")
            if self.connection is None or self.connection.fileno() == -1:
                self.connection = self.server.accept_connection()
            self.connection.sendall('STOP_PUMPS'.encode('utf-8'))

    def open_run_time_dialog(self):
        dialog = RunTimeDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_run_time = dialog.get_run_time()
            if new_run_time > 0:
                self.run_time = new_run_time
                self.last_run_time = new_run_time
                self.run_volume = self.run_time * (self.flowrate / 60)
                if self.run_volume > 0:
                    self.plot_widget.setXRange(0, self.run_volume)
            else:
                self.run_time = self.last_run_time

    def open_flowrate_dialog(self):
        dialog = FlowRateDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_flowrate = round(dialog.get_flowrate(), 2)
            if new_flowrate > 0:
                self.flowrate = new_flowrate
                self.last_flowrate = new_flowrate
                self.run_volume = self.run_time * (self.flowrate / 60)
                if self.run_volume > 0:
                    self.plot_widget.setXRange(0, self.run_volume)
                self.update_plot_title()
                if self.connection:
                    try:
                        self.connection.sendall(f'FLOWRATE:{self.flowrate}'.encode('utf-8'))
                        print(f"Sent FLOWRATE:{self.flowrate} to client")
                    except socket.error as e:
                        print(f"Error sending FLOWRATE: {e}")
                        self.handle_disconnection()
            else:
                self.flowrate = self.last_flowrate

    def start_acquisition(self):
        if self.run_time <= 0.0:
            runtime_warning_dialog = RunTime_WarningDialog(self)
            if runtime_warning_dialog.exec() == QDialog.DialogCode.Accepted:
                self.open_run_time_dialog()
            return

        if self.flowrate <= 0.0:
            flowrate_warning_dialog = FlowRate_WarningDialog(self)
            if flowrate_warning_dialog.exec() == QDialog.DialogCode.Accepted:
                self.open_flowrate_dialog()
            return

        if self.selected_AUFS_value <= 0.0:
            aufs_warning_dialog = AUFS_WarningDialog(self)
            if aufs_warning_dialog.exec() == QDialog.DialogCode.Accepted:
                self.open_UV_Monitor_dialog()
            return

        self.run_time_button.setEnabled(False)

        if self.connection is None or self.connection.fileno() == -1:
            self.connection = self.server.accept_connection()

        self.connection.sendall('START_ADC'.encode('utf-8'))
        self.run_acquisition()

    def run_acquisition(self):
        if self.worker is not None and self.worker.is_running:
            print("Acquisition already running.")
            return
        
        self.RunDateTime = datetime.strftime(datetime.now(), "%Y_%b_%d_%H%M%S")
        self.update_plot_title()

        self.worker = Worker(self.run_time, self.channels, self.logger.append_data_row, self, self.selected_uv_monitor, self.selected_AUFS_value, self.connection)
        self.listener.data_received_signal.connect(self.worker.handle_data_received)
        self.worker.data_signal.connect(self.update_plot_data)
        self.worker.finished.connect(self.enable_buttons)
        self.worker.error_signal.connect(self.handle_fraction_collector_error)
        self.worker.error_cleared_signal.connect(self.handle_fraction_collector_error_cleared)
        self.thread = threading.Thread(target=self.worker.run, name="WorkerThread")
        self.thread.start()

    def update_plot_data(self, elapsed_time, frac_mark, Chan1, Chan1_AU280, Chan2):
        self.elapsed_time_data.append(elapsed_time)
        self.chan1_data.append(Chan1)
        self.chan1_AU280_data.append(Chan1_AU280)
        self.chan2_data.append(Chan2)

        eluate_volume = elapsed_time * (self.flowrate / 60)
        self.eluate_volume_data.append(eluate_volume)

        data_row = {
            "Elapsed_Time (sec)": elapsed_time,
            "Eluate_Volume (ml)": eluate_volume,
            "Frac_Mark": frac_mark,
            "Chan1 (volt)": Chan1,
            "Chan1_AU280 (AU)": Chan1_AU280,
            "Chan2": Chan2
        }

        if not self.metadata_written:
            metadata = {
                "RUNTIME (sec)": self.run_time,
                "Year/Date/Time": self.RunDateTime,
                "Column_type": self.selected_column_type,
                "AUFS_setting": self.selected_AUFS_value,
                "UV_monitor": self.selected_uv_monitor,
                "UV_monitor_FS_value (Volts)": self.uv_monitor_FS_value,
                "Flowrate (ml/min)": self.flowrate
            }
            self.logger.write_metadata({**data_row, **metadata})
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
            self.max_y_value
        )

        if elapsed_time >= self.run_time:
            self.stop_save_acquisition()

    def stop_save_acquisition(self):
        if self.connection and self.connection.fileno() != -1:
            self.connection.sendall('STOP_ADC'.encode('utf-8'))
            print("STOP_ADC sent to client")

        if hasattr(self, 'worker') and self.worker.is_running:
            self.worker.stop()
            self.worker.is_running = False
            if self.thread is not None:
                self.thread.join()

        self.show_save_dialog()
        self.clear_plot_and_reset()

    def show_save_dialog(self):
        dialog = SaveDialog(self)
        dialog.accepted.connect(self.save_data)
        dialog.rejected.connect(self.clear_plot_and_reset)
        dialog.finished.connect(self.enable_buttons)
        dialog.exec()

    def save_data(self):
        self.logger.save_final_csv_and_plot(self.plot_widget)
        self.clear_data()
        self.plot_widget.clear()
        print('Plot cleared and system reset. Ready for next acquisition.')

    def clear_plot_and_reset(self):
        self.clear_data()
        self.plot_widget.clear()
        self.update_plot_title()
        self.metadata_written = False
        self.logger.clear_data()
        print('Plot cleared and system reset. Ready for next acquisition.')

    def clear_data(self):
        self.elapsed_time_data.clear()
        self.eluate_volume_data.clear()
        self.frac_mark_data.clear()
        self.chan1_data.clear()
        self.chan1_AU280_data.clear()
        self.chan2_data.clear()
        print('Data cleared. Ready for next acquisition.')

    def enable_buttons(self):
        self.run_time_button.setEnabled(True)
        self.start_button.setEnabled(True)

    def update_plot_title(self):
        plot_title = f"<b><br>{self.selected_column_type}: {self.RunDateTime}</b><br>Flowrate: {self.flowrate} ml/min, {self.selected_uv_monitor}: {self.selected_AUFS_value} AUFS"
        self.plot_widget.setTitle(plot_title, size='12pt', color='w')
        if self.selected_uv_monitor == "Pharmacia UV MII":
            self.max_y_value = self.selected_AUFS_value
        elif self.selected_uv_monitor == "BioRad EM1":
            self.max_y_value = 0.1 * self.selected_AUFS_value
        self.plot_widget.setYRange(0, self.max_y_value)

    def open_column_type_dialog(self):
        dialog = ColumnTypeDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.selected_column_type = dialog.combo_box.currentText()
            self.update_plot_title()

    def open_UV_Monitor_dialog(self):
        dialog = UV_Monitor_Dialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            print(f"Selected AUFS value: {self.selected_AUFS_value}")
            print(f"Selected UV monitor: {self.selected_uv_monitor}")
            print(f"UV monitor FS value: {self.uv_monitor_FS_value}")
            self.update_plot_title()

    def open_pause_dialog(self):
        dialog = PauseDialog(self)
        if self.connection is None or self.connection.fileno() == -1:
            self.connection = self.server.accept_connection()
        self.connection.sendall('PAUSE_ADC'.encode('utf-8'))
        print("PAUSE_ADC sent to client")
        if self.worker is not None:
            self.worker.pause()

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.worker.resume()
            if self.connection is None or self.connection.fileno() == -1:
                self.connection = self.server.accept_connection()
            self.connection.sendall('RESUME_ADC'.encode('utf-8'))
            print("RESUME_ADC sent to client")
        else:
            self.worker.pause()
            print("Paused the acquisition")

    def handle_fraction_collector_error(self, error_message):
        if self.error_dialog_open:
            return        
        print(f"Handling error: {error_message}")
        self.error_dialog_open = True
        self.error_dialog = FractionCollectorErrorDialog(self)
        self.error_dialog.label.setText(error_message)
        self.error_dialog.finished.connect(self.reset_error_dialog_flag)
        self.error_dialog.exec()
        
    def reset_error_dialog_flag(self):
        self.error_dialog_open = False

    def handle_fraction_collector_error_cleared(self, message):
        print(f"Handling error cleared: {message}")
        if hasattr(self, 'error_dialog'):
            print(f"Dialog visible: {self.error_dialog.isVisible()}")
            self.error_dialog.set_error_cleared()
            self.error_dialog.exit_error_dialog()
            #self.stop_save_acquisition()

    def handle_disconnection(self):
        print("Client disconnected. Attempting to reconnect...")
        if self.listener:
            self.listener.stop()
            self.listener = None
        self.connection = None
        self.connection_status_label.setText("FPLC not connected")
        self.connection_status_label.setStyleSheet("background-color: red; color: white; border: 1px solid black;")
        self.update_manual_controls()

    def close_application(self):
        self.close()

    def closeEvent(self, event):
        self.is_running = False
        if self.thread is not None:
            self.thread.join()
        event.accept()
