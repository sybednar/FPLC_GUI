#network.py ver 0.5.0
import socket
import threading

class FPLCServer:
    def __init__(self, host='0.0.0.0', port=5000):
        self.host = host
        self.port = port
        self.sock = None
        self.connection = None

    def start_server(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.listen(1)
        print("Server listening...")
        

    def accept_connection(self):
        self.connection, addr = self.sock.accept()
        print(f"Connected to {addr}")
        return self.connection

    def send(self, message):
        if self.connection:
            self.connection.sendall(message.encode('utf-8'))

    def receive(self):
        if self.connection:
            return self.connection.recv(1024).decode('utf-8')

    def close(self):
        if self.connection:
            self.connection.close()
        if self.sock:
            self.sock.close()
