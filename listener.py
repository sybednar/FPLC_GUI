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
                    continue

                message = data.decode('utf-8').strip()
                print(f"[Listener] Received: {message}")

                if "PUMP_A_WASH_COMPLETED" in message:
                    self.pumpA_wash_completed_signal.emit()

                elif "Fraction Collector error" in message:
                    self.fraction_collector_error_signal.emit(message)

                elif "Fraction Collector Error has been cleared" in message:
                    self.fraction_collector_error_cleared_signal.emit(message)

                elif "HEARTBEAT" in message:
                    self.last_heartbeat = time.time()
                    print("[Listener] Heartbeat received.")

                else:
                    self.data_received_signal.emit(message)

            except socket.timeout:
                # Check for heartbeat timeout (optional)
                if time.time() - self.last_heartbeat > 10:
                    print("[Listener] Warning: No heartbeat received in 10 seconds.")
                continue

            except socket.error as e:
                print(f"[Listener] Socket error: {e}")
                break

        print("[Listener] Stopped listening.")


