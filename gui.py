#gui.py (ver0.4.6) adding method editor
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
    QGridLayout, QDialog, QDialogButtonBox, QProgressBar
)
from PySide6.QtCore import Signal, QObject, Qt
from PySide6.QtGui import QFont, QStandardItemModel, QStandardItem
import pyqtgraph as pg
import socket
import json
from network import FPLCServer
from hardware import set_gpio17, toggle_gpio17
from plotting import create_plot_widget, update_plot
from data_logger import DataLogger
from listener import ReceiveClientSignalsAndData
from method_editor import MethodEditor



class OpenProgramModeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Program Options")
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


class Volume_Dialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Run Volume")
        self.setMinimumWidth(200)

        # Main layout
        main_layout = QVBoxLayout()

        # Horizontal layout for spin box and label
        h_layout = QHBoxLayout()

        # Spin box for volume in ml
        self.run_volume_ml_spinbox = QDoubleSpinBox()
        self.run_volume_ml_spinbox.setRange(0.0, 99)
        self.run_volume_ml_spinbox.setSingleStep(1)
        self.run_volume_ml_spinbox.setDecimals(1)
        self.run_volume_ml_spinbox.setMinimumWidth(75)
        self.run_volume_ml_spinbox.setMinimumHeight(100)

        # Style for dark theme
        style = """
        QDoubleSpinBox {
            background-color: #2c2c2c;
            color: #ffffff;
            border: 1px solid #444444;
            font-size: 36px;
        }
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
            background-color: #444444;
            border: none;
            width: 40px;
            height: 40px;
            background-position: center;
            background-repeat: no-repeat;
        }
        QDoubleSpinBox::up-button {
            background-image: url(/home/sybednar/FPLC_controller_venv/FPLC_server/FPLC_GUI_customization/uparrow_3pt_white.png);
        }
        QDoubleSpinBox::down-button {
            background-image: url(/home/sybednar/FPLC_controller_venv/FPLC_server/FPLC_GUI_customization/downarrow_3pt_white.png);
        }
        QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
            background-color: #555555;
        }
        """
        self.run_volume_ml_spinbox.setStyleSheet(style)

        # Font styling
        font = self.font()
        font.setPointSize(24)
        self.setFont(font)

        # Add widgets to layout
        h_layout.addWidget(self.run_volume_ml_spinbox)
        h_layout.addWidget(QLabel("Volume (ml)"), alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addLayout(h_layout)

        # Confirm button
        font.setPointSize(16)
        self.setFont(font)
        self.confirm_button = QPushButton("Confirm")
        self.confirm_button.clicked.connect(self.accept)
        main_layout.addWidget(self.confirm_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(main_layout)
        self.load_saved_values()

    def load_saved_values(self):
        if hasattr(self.parent(), 'saved_run_volume'):
            self.run_volume_ml_spinbox.setValue(self.parent().saved_run_volume)

    def accept(self):
        self.parent().saved_run_volume = self.run_volume_ml_spinbox.value()
        super().accept()

    def get_run_volume(self):
        return self.run_volume_ml_spinbox.value()


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

class RunVolume_WarningDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Warning")
        self.setMinimumWidth(300)  # Adjust the width as needed
        layout = QVBoxLayout()

        self.label = QLabel("Set Run Volume > 0 sec")
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

class SystemValveDialog(QDialog):   
    def __init__(self, parent=None):
        super().__init__(parent)
        font = self.font()
        font.setPointSize(16)  # Increase font size
        self.setFont(font)
        self.setWindowTitle("System Valve Position")
        self.setMinimumWidth(300)

        layout = QVBoxLayout()

        self.combo_box = QComboBox()

        # Create a model to center-align items
        model = QStandardItemModel()
        for text in ["LOAD", "INJECT", "WASH"]:
            item = QStandardItem(text)
            item.setTextAlignment(Qt.AlignCenter)
            model.appendRow(item)
        self.combo_box.setModel(model)

        # Center the current text in the combo box
        self.combo_box.setEditable(True)
        self.combo_box.lineEdit().setAlignment(Qt.AlignCenter)
        self.combo_box.setEditable(False)

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

class PumpModeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        font = self.font()
        font.setPointSize(16)  # Increase font size
        self.setFont(font)
        self.setWindowTitle("Select Pump Mode")
        self.setMinimumWidth(300)
        layout = QVBoxLayout()

        self.combo_box = QComboBox()
        self.combo_box.addItems(["Isocratic", "Gradient"])
        layout.addWidget(self.combo_box)

        confirm_button = QPushButton("Confirm")
        confirm_button.clicked.connect(self.accept)
        layout.addWidget(confirm_button)

        self.setLayout(layout)

    def get_selected_mode(self):
        return self.combo_box.currentText()

class gradient_settings_Dialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PumpB Gradient Settings")
        self.setMinimumWidth(300)

        main_layout = QVBoxLayout()

        # Shared style for both spin boxes
        style = """
        QDoubleSpinBox {
            background-color: #2c2c2c;
            color: #ffffff;
            border: 1px solid #444444;
            font-size: 36px;
        }
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
            background-color: #444444;
            border: none;
            width: 40px;
            height: 40px;
            background-position: center;
            background-repeat: no-repeat;
        }
        QDoubleSpinBox::up-button {
            background-image: url(/home/sybednar/FPLC_controller_venv/FPLC_server/FPLC_GUI_customization/uparrow_3pt_white.png);
        }
        QDoubleSpinBox::down-button {
            background-image: url(/home/sybednar/FPLC_controller_venv/FPLC_server/FPLC_GUI_customization/downarrow_3pt_white.png);
        }
        QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
            background-color: #555555;
        }
        """
        font = self.font()
        font.setPointSize(24)
        self.setFont(font)

        # PumpB Min SpinBox
        pumpB_min_layout = QVBoxLayout()
        pumpB_min_label = QLabel("Min (%)")
        pumpB_min_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pumpB_min_spinbox = QDoubleSpinBox()
        self.pumpB_min_spinbox.setRange(0, 100)
        self.pumpB_min_spinbox.setSingleStep(1)
        self.pumpB_min_spinbox.setDecimals(1)
        self.pumpB_min_spinbox.setMinimumWidth(75)
        self.pumpB_min_spinbox.setMinimumHeight(100)
        self.pumpB_min_spinbox.setStyleSheet(style)
        pumpB_min_layout.addWidget(pumpB_min_label)
        pumpB_min_layout.addWidget(self.pumpB_min_spinbox)

        # PumpB Max SpinBox
        pumpB_max_layout = QVBoxLayout()
        pumpB_max_label = QLabel("Max (%)")
        pumpB_max_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pumpB_max_spinbox = QDoubleSpinBox()
        self.pumpB_max_spinbox.setRange(0, 100)
        self.pumpB_max_spinbox.setSingleStep(1)
        self.pumpB_max_spinbox.setDecimals(1)
        self.pumpB_max_spinbox.setMinimumWidth(75)
        self.pumpB_max_spinbox.setMinimumHeight(100)
        self.pumpB_max_spinbox.setStyleSheet(style)
        pumpB_max_layout.addWidget(pumpB_max_label)
        pumpB_max_layout.addWidget(self.pumpB_max_spinbox)
        
        # Combine into horizontal layout
        spinbox_row = QHBoxLayout()
        spinbox_row.addLayout(pumpB_min_layout)
        spinbox_row.addLayout(pumpB_max_layout)

        main_layout.addLayout(spinbox_row)

        # Confirm Button
        font.setPointSize(16)
        self.setFont(font)
        self.confirm_button = QPushButton("Confirm")
        self.confirm_button.clicked.connect(self.accept)
        main_layout.addWidget(self.confirm_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(main_layout)
        self.load_saved_values()

    def load_saved_values(self):
        if hasattr(self.parent(), 'saved_pumpB_min'):
            self.pumpB_min_spinbox.setValue(self.parent().saved_pumpB_min)
        if hasattr(self.parent(), 'saved_pumpB_max'):
            self.pumpB_max_spinbox.setValue(self.parent().saved_pumpB_max)

    def accept(self):
        self.parent().saved_pumpB_min = self.pumpB_min_spinbox.value()
        self.parent().saved_pumpB_max = self.pumpB_max_spinbox.value()
        super().accept()

    def get_pumpB_min(self):
        return self.pumpB_min_spinbox.value()

    def get_pumpB_max(self):
        return self.pumpB_max_spinbox.value()
    

#---------- Worker class for background data acquisition----------
class Worker(QObject):
    data_signal = Signal(float, float, float, float, float)
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
        self.RunDateTime = datetime.strftime(datetime.now(), "%Y_%b_%d_%H%M%S")
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
        "RUN_VOLUME (ml)", "Year/Date/Time", "Column_type", "AUFS_setting",
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

        right_label = QLabel("Data Analysis", container)
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

        self.program_mode_button = QPushButton("Program_Method", container)
        self.program_mode_button.setGeometry(50, 460, 100, 30)
        self.program_mode_button.clicked.connect(self.handle_program_mode)

        # Right-side buttons
        self.Peak_ID_button = QPushButton("Peak_ID", container)
        self.Peak_ID_button.setGeometry(874, 100, 100, 30)
        self.Peak_ID_button.clicked.connect(self.handle_Peak_ID_button_click)

        self.Baseline_Corr_button = QPushButton("Baseline_Corr", container)
        self.Baseline_Corr_button.setGeometry(874, 140, 100, 30)
        self.Baseline_Corr_button.clicked.connect(self.handle_Baseline_Corr_button_click)

        self.Peak_Smoothing_button = QPushButton("Peak_Smoothing", container)
        self.Peak_Smoothing_button.setGeometry(874, 180, 100, 30)
        self.Peak_Smoothing_button.clicked.connect(self.handle_Peak_Smoothing_button_click)

        self.desktop_button = QPushButton("Desktop", container)
        self.desktop_button.setGeometry(874, 260, 100, 30)
        self.desktop_button.clicked.connect(self.close_application)

        # Settings and control buttons
        self.system_valve_button = QPushButton("System_Valve", container)
        self.system_valve_button.setGeometry(212, 360, 100, 30)
        self.system_valve_button.clicked.connect(self.open_system_valve_dialog)

        self.FlowRate_button = QPushButton("FlowRate", container)
        self.FlowRate_button.setGeometry(322, 360, 100, 30)
        self.FlowRate_button.clicked.connect(self.open_flowrate_dialog)

        self.run_volume_button = QPushButton("Set Run Volume", container)
        self.run_volume_button.setGeometry(432, 360, 100, 30)
        self.run_volume_button.clicked.connect(self.open_run_volume_dialog)

        self.pump_mode_button = QPushButton("Pump Mode: Isocratic", container)
        self.pump_mode_button.setGeometry(542, 360, 210, 30)
        self.pump_mode_button.clicked.connect(self.open_pump_mode_dialog)
  


        self.column_type_button = QPushButton("Column Type", container)
        self.column_type_button.setGeometry(212, 400, 100, 30)
        self.column_type_button.clicked.connect(self.open_column_type_dialog)

        self.fraction_collector_button = QPushButton("Frac Collect (OFF)", container)
        self.fraction_collector_button.setGeometry(322, 400, 100, 30)
        self.fraction_collector_button.clicked.connect(self.toggle_Fraction_Collector)

        self.UVMonitor_button = QPushButton("UVMonitor", container)
        self.UVMonitor_button.setGeometry(432, 400, 100, 30)
        self.UVMonitor_button.clicked.connect(self.open_UV_Monitor_dialog)
        
        self.divert_valve_button = QPushButton("Diverter(OFF)", container)
        self.divert_valve_button.setGeometry(542, 400, 100, 30)
        self.divert_valve_button.clicked.connect(self.toggle_divert_valve)
               


        # Additional labels
        #settings_label = QLabel("Flow", container)
        #settings_label.setGeometry(136, 360, 100, 30)
        #settings_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        #fraction_collector_label = QLabel("Collection", container)
        #fraction_collector_label.setGeometry(110, 400, 100, 30)
        #fraction_collector_label.setAlignment(Qt.AlignmentFlag.AlignCenter)


        # Pump and valve control buttons
        self.pump_wash_button = QPushButton("Solvent Change", container)
        self.pump_wash_button.setGeometry(874, 360, 100, 30)
        self.pump_wash_button.clicked.connect(self.open_solvent_exchange_dialog)

        self.pump_calibration_button = QPushButton("Pump_Calibration", container)
        self.pump_calibration_button.setGeometry(874, 400, 100, 30)
        self.pump_calibration_button.clicked.connect(self.toggle_pump_calibration)
        
        Pumps_label = QLabel("Pumps", container)
        Pumps_label.setGeometry(360, 680, 100, 30)
        Pumps_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.volume_delivered_progress_bar = QProgressBar(self)
        self.volume_delivered_progress_bar.setGeometry(438, 680, 150, 30)
        self.volume_delivered_progress_bar.setRange(0, 100)
        self.volume_delivered_progress_bar.setValue(0)
        self.volume_delivered_progress_bar.setFormat("Idle")
        self.volume_delivered_progress_bar.setStyleSheet("QProgressBar { color: white; }")

        self.method_editor = MethodEditor(container, main_app=self)
        self.method_editor.setGeometry(70, 480, 870, 180) # Adjust size and position as needed


    def handle_program_mode(self):
        if self.method_editor.steps:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Existing Method Detected")
            msg_box.setText("A method is already loaded. What would you like to do?")
            save_btn = msg_box.addButton("Save", QMessageBox.AcceptRole)
            delete_btn = msg_box.addButton("Delete", QMessageBox.DestructiveRole)
            cancel_btn = msg_box.addButton("Cancel", QMessageBox.RejectRole)
            msg_box.exec()

            if msg_box.clickedButton() == save_btn:
                self.method_editor.save_method()
                self.method_editor.new_method()
                self.method_editor.add_step(0, None)
            elif msg_box.clickedButton() == delete_btn:
                self.method_editor.new_method()
                self.method_editor.add_step(0, None)
            else:
                return# Cancelled

        else:
            dialog = OpenProgramModeDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                if dialog.selected_option == "Open":
                    self.method_editor.load_method()
                    if not self.method_editor.steps:
                        self.method_editor.add_step(0, None)
                elif dialog.selected_option == "Create":
                    self.method_editor.new_method()
                    self.method_editor.add_step(0, None)



    def handle_method_run(self):
        self.method_sequence = self.method_editor.get_method_sequence()
        self.current_step_index = 0
        self.run_next_step()

    def run_next_step(self):
        if self.connection is None or self.connection.fileno() == -1:
            QMessageBox.critical(self, "Connection Error", "FPLC client is not connected. Please wait for connection.")
            print("run_next_step aborted: No connection to client.")
            return
        
        if self.current_step_index >= len(self.method_sequence):
            print("All steps completed.")
            return

        step = self.method_sequence[self.current_step_index]

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

        # Check Frac Collect status for this step
        frac_collect = step.get("Frac Collect", "OFF")
        self.fraction_collector_mode_enabled = frac_collect == "ON"
        self.fraction_collector_button.setText(f"Frac Collect ({frac_collect})")

        # Determine pump mode and prepare run packet
        pump_mode = step.get("Pump Mode", "Isocratic")
        run_packet = {
            "System_Valve_Position": step["System Valve"],
            "FLOWRATE": self.flowrate,
            "VOLUME": self.run_volume,
            "DIVERTER_VALVE": step["Diverter"],
            "START_PUMPS": True
        }
        if self.fraction_collector_mode_enabled:
            run_packet["START_ADC"] = True

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

        if self.fraction_collector_mode_enabled:
            self.run_acquisition()

    def handle_next_step(self):
        if self.current_step_index >= len(self.method_sequence):
            return

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
        print("Method Pause clicked")
        self.open_pause_dialog()
        
    def handle_method_stop(self):
        print("Method Stop clicked")
        if self.connection:
            stop_method_packet = {
                "STOP_PUMPS": True,
                "System_Valve_Position": "LOAD",
                "FLOWRATE": 0.0,
                "PumpA_Volume": 0.0,
                "PumpB_min_percent": 0.0,
                "PumpB_max_percent": 0.0
            }

            if self.fraction_collector_mode_enabled:
                stop_method_packet["STOP_ADC"] = True
                self.fraction_collector_mode_enabled = False
                self.fraction_collector_button.setText("Frac Collect (OFF)")

            if self.divert_valve_mode:
                stop_method_packet["DIVERTER_VALVE"] = False
                self.divert_valve_button.setText("Diverter(OFF)")
                self.divert_valve_mode = False

            try:
                self.connection.sendall(f'METHOD_STOP_JSON:{json.dumps(stop_method_packet)}'.encode('utf-8'))
                print(f"Sent METHOD_STOP_JSON: {stop_method_packet}")
            except socket.error as e:
                print(f"Error sending METHOD_STOP_JSON: {e}")
                self.handle_disconnection()

            self.reset_progress_bar()

            if self.fraction_collector_mode_enabled:
                self.stop_save_acquisition()

    def handle_Peak_ID_button_click(self):
        print("Peak_ID Button clicked")

    def handle_Baseline_Corr_button_click(self):
        print("Baseline_Corr Button, set order of polynomial and iterations of baseline calculation")

    def handle_Peak_Smoothing_button_click(self):
        print("Peak_Smoothing Button, set Savitzky-Golay window length and polyorder values")
   
    def update_manual_controls(self):
        is_connected = self.connection is not None and self.connection.fileno() != -1
        enable_controls = self.manual_mode_enabled and is_connected
        #self.start_button.setEnabled(enable_controls)
        #self.pause_button.setEnabled(enable_controls)
        #self.stop_save_button.setEnabled(enable_controls)

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
                #self.update_manual_controls()
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
        
    def open_pump_mode_dialog(self):
        dialog = PumpModeDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_mode = dialog.get_selected_mode()
            self.elution_method = selected_mode
            self.pump_mode_button.setText(f"Pump Mode: {selected_mode}")
            if self.method_editor.steps:
                self.method_editor.steps[-1]["Pump Mode"] = selected_mode
                self.method_editor.update_table()
        # Open gradient settings dialog if Gradient is selected
        if selected_mode == "Gradient":
            gradient_dialog = gradient_settings_Dialog(self)
            if gradient_dialog.exec() == QDialog.DialogCode.Accepted:
                self.saved_pumpB_min = gradient_dialog.get_pumpB_min()
                self.saved_pumpB_max = gradient_dialog.get_pumpB_max()
                print(f"Gradient PumpB setting: Min = {self.saved_pumpB_min}%, Max = {self.saved_pumpB_max}%")
                if self.method_editor.steps:
                    self.method_editor.steps[-1]["PumpB Min %"] = self.saved_pumpB_min
                    self.method_editor.steps[-1]["PumpB Max %"] = self.saved_pumpB_max
                    self.method_editor.update_table()
            
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

    def open_run_volume_dialog(self):
        dialog = Volume_Dialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_run_volume = dialog.get_run_volume()
            if new_run_volume > 0:
                self.run_volume = new_run_volume
                self.last_run_volume = new_run_volume
                self.plot_widget.setXRange(0, self.run_volume)
                if self.method_editor.steps:
                    self.method_editor.steps[-1]["Run Volume (ml)"] = self.run_volume
                    self.method_editor.update_table()

            else:
                self.run_volume = self.last_run_volume

    def open_flowrate_dialog(self):
        dialog = FlowRateDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_flowrate = round(dialog.get_flowrate(), 2)
            if new_flowrate > 0:
                self.flowrate = new_flowrate
                self.last_flowrate = new_flowrate
                if self.run_volume > 0:
                    self.plot_widget.setXRange(0, self.run_volume)
                self.update_plot_title()
                if self.method_editor.steps:
                    self.method_editor.steps[-1]["Flowrate (ml/min)"] = self.flowrate
                    self.method_editor.update_table()
            else:
                self.flowrate = self.last_flowrate

    def open_system_valve_dialog(self):
        dialog = SystemValveDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.system_valve_position = dialog.combo_box.currentText()
            if self.method_editor.steps:
                self.method_editor.steps[-1]["System Valve"] = self.system_valve_position
                self.method_editor.update_table()            


    def toggle_Fraction_Collector(self):
        # Always toggle to ON first
        self.fraction_collector_mode_enabled = not self.fraction_collector_mode_enabled
        status = "ON" if self.fraction_collector_mode_enabled else "OFF"
        self.fraction_collector_button.setText(f"Frac Collect ({status})")

        # Update method editor if applicable
        if self.method_editor.steps:
            self.method_editor.steps[-1]["Frac Collect"] = status
            self.method_editor.update_table()

        # If turning ON, ensure diverter valve is also ON
        if self.fraction_collector_mode_enabled and not self.divert_valve_mode:
            self.divert_valve_mode = True
            self.divert_valve_button.setText("Diverter(ON)")
            if self.method_editor.steps:
                self.method_editor.steps[-1]["Diverter"] = "ON"
                self.method_editor.update_table()

        # Show AUFS warning if value is invalid
        if self.fraction_collector_mode_enabled and self.selected_AUFS_value <= 0.0:
            aufs_warning_dialog = AUFS_WarningDialog(self)
            if aufs_warning_dialog.exec() == QDialog.DialogCode.Accepted:
                self.open_UV_Monitor_dialog()

    def run_acquisition(self):
        if self.worker is not None and self.worker.is_running:
            print("Acquisition already running.")
            return
        
        self.RunDateTime = datetime.strftime(datetime.now(), "%Y_%b_%d_%H%M%S")
        self.update_plot_title()

        self.worker = Worker(self.logger.append_data_row, self, self.selected_uv_monitor, self.selected_AUFS_value, self.connection)
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
                "RUN_VOLUME (ml)": self.run_volume,
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

        if eluate_volume >= self.run_volume:
            self.stop_save_acquisition()
            # Check if the current step's End Action is "Stop"
            method_sequence = self.method_editor.get_method_sequence()
            if method_sequence and method_sequence[-1].get("End Action") == "Stop":
                self.handle_method_stop()

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
        self.reset_progress_bar()

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
        self.acquisition_stopped = False
        self.clear_data()
        self.plot_widget.clear()
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
        print('Data cleared. Ready for next acquisition.')

    def enable_buttons(self):
        self.run_volume_button.setEnabled(True)
        #self.start_button.setEnabled(True)

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
            if self.connection is None or self.connection.fileno() == -1:
                self.connection = self.server.accept_connection()
            self.connection.sendall('RESUME_ADC'.encode('utf-8'))
            print("RESUME_ADC sent to client")
            if self.worker is not None:
                self.worker.resume()
                
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
        
    def handle_PumpA_error(self, error_message):
        self.pump_errors["A"] = True
        self.show_pump_error_dialog()

    def handle_PumpB_error(self, error_message):
        self.pump_errors["B"] = True
        self.show_pump_error_dialog()

    def handle_PumpA_error_cleared(self, message):
        self.pump_errors["A"] = False
        self.update_or_close_pump_error_dialog()

    def handle_PumpB_error_cleared(self, message):
        self.pump_errors["B"] = False
        self.update_or_close_pump_error_dialog()
        
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
