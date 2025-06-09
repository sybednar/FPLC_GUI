#listener.py
from PySide6.QtCore import QObject, Signal
import threading
import socket
import time

class ReceiveClientSignalsAndData(QObject):
    pumpA_wash_completed_signal = Signal()
    fraction_collector_error_signal = Signal(str)
    fraction_collector_error_cleared_signal = Signal(str)
    data_received_signal = Signal(str)
    disconnected_signal = Signal()
    stop_save_signal = Signal()
    pumpA_volume_signal = Signal(float)

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

                elif "Fraction Collector error" in message:
                    self.fraction_collector_error_signal.emit(message)

                elif "Fraction Collector Error has been cleared" in message:
                    self.fraction_collector_error_cleared_signal.emit(message)

                elif "STOP_SAVE_ACQUISITION" in message:
                    self.stop_save_signal.emit()
                    
                elif message.startswith("PumpA_running"):
                    try:
                        volume = float(message.split()[1])
                        self.pumpA_volume_signal.emit(volume)
                        print(f"[Listener] PumpA_running {volume} ml")
                    except ValueError:
                        print(f"Invalid PumpA_running message: {message}")
                
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


