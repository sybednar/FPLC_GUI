#listener.py ver 0.4.8
from PySide6.QtCore import QObject, Signal
import threading
import socket
import time

class ReceiveClientSignalsAndData(QObject):
    pumpA_wash_completed_signal = Signal()
    pumpB_wash_completed_signal = Signal()
    fraction_collector_error_signal = Signal(str)
    fraction_collector_error_cleared_signal = Signal(str)
    pumpA_error_signal = Signal(str)
    pumpA_error_cleared_signal = Signal(str)
    pumpB_error_signal = Signal(str)
    pumpB_error_cleared_signal = Signal(str)
    data_received_signal = Signal(str)
    disconnected_signal = Signal()
    stop_save_signal = Signal()
    pumpA_volume_signal = Signal(float)
    gradient_volume_signal = Signal(float)
    valve_error_signal = Signal(str)
    valve_position_signal = Signal(str)

    def __init__(self, connection):
        super().__init__()
        self.connection = connection
        self._running = True
        self.last_heartbeat = time.time()
        self.thread = threading.Thread(target=self.listen, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self._running = False

    def listen(self):
        self.connection.settimeout(1.0)# Prevents blocking indefinitely
        while self._running:
            try:
                data = self.connection.recv(1024)
                if not data:
                    print("[Listener] Client disconnected.")
                    self.disconnected_signal.emit()
                    break

                message = data.decode('utf-8').strip()
                print(f"[Listener] Received: {message}")

                if "PUMP_A_WASH_COMPLETED" in message:
                    self.pumpA_wash_completed_signal.emit()
                    
                elif "PUMP_B_WASH_COMPLETED" in message:
                    self.pumpB_wash_completed_signal.emit()

                elif "Fraction Collector error" in message:
                    self.fraction_collector_error_signal.emit("Frac-200 error has occurred.<br>Clear the error before continuing....")

                elif "Fraction Collector Error has been cleared" in message:
                    self.fraction_collector_error_cleared_signal.emit(message)

                elif "PumpA error" in message:
                    self.pumpA_error_signal.emit("Pump A error has occurred.<br>Clear the error before continuing....")

                elif "PumpA Error has been cleared" in message:
                    self.pumpA_error_cleared_signal.emit(message)
                    
                elif "PumpB error" in message:
                    self.pumpB_error_signal.emit("Pump B error has occurred.<br>Clear the error before continuing....")

                elif "PumpB Error has been cleared" in message:
                    self.pumpB_error_cleared_signal.emit(message)    

                elif "STOP_SAVE_ACQUISITION" in message:
                    self.stop_save_signal.emit()
                    
                elif message.startswith("PumpA_running"):
                    try:
                        volume = float(message.split()[1])
                        self.pumpA_volume_signal.emit(volume)
                        print(f"[Listener] PumpA_running {volume} ml")
                    except ValueError:
                        print(f"Invalid PumpA_running message: {message}")

                elif message.startswith("Gradient_running"):
                    try:
                        volume = float(message.split()[1])
                        self.gradient_volume_signal.emit(volume)
                        print(f"[Listener] Gradient_running {volume} ml")
                    except ValueError:
                        print(f"Invalid Gradient_running message: {message}")

                elif message == "Valve Malfunction":
                    print("Debug: Received Valve Malfunction message")
                    self.valve_error_signal.emit("Valve failed to reach target position.<br>Run aborted")

                elif message.startswith("VALVE_POSITION:"):       
                    print(f"Debug: Received VALVE_POSITION message with position: {message.split(':', 1)[1]}")
                    position = message.split(":", 1)[1]
                    self.valve_position_signal.emit(position)

                elif "HEARTBEAT" in message:
                    self.last_heartbeat = time.time()
                    print("[Listener] Heartbeat received.")

                else:
                    self.data_received_signal.emit(message)

            except socket.timeout:
                pass 

            except socket.error as e:
                print(f"[Listener] Socket error: {e}")
                self.disconnected_signal.emit()
                break
            
            if time.time() - self.last_heartbeat > 10:
                print("[Listener] Warning: No heartbeat received in 10 seconds.")
                

        print("[Listener] Stopped listening.")


