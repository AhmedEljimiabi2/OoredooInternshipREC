import socket
import threading
import json
import sqlite3
from datetime import datetime

HOST = "0.0.0.0"
PORT = 5000

# Database setup
conn_db = sqlite3.connect("devices.db", check_same_thread=False)
cursor = conn_db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS device_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_name TEXT,
    ip TEXT,
    cpu REAL,
    memory REAL,
    disk REAL,
    timestamp TEXT
)
""")

conn_db.commit()


def handle_client(conn, addr):
    print(f"[CONNECTED] {addr}")

    while True:
        try:
            data = conn.recv(4096)

            if not data:
                break

            message = data.decode("utf-8")
            device_data = json.loads(message)

            print("\n--- Device Data ---")
            print(f"Device Name: {device_data['device_name']}")
            print(f"IP Address: {device_data['ip']}")
            print(f"CPU: {device_data['cpu']}%")
            print(f"Memory: {device_data['memory']}%")
            print(f"Disk: {device_data['disk']}%")

            cursor.execute("""
            INSERT INTO device_data (device_name, ip, cpu, memory, disk, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                device_data["device_name"],
                device_data["ip"],
                device_data["cpu"],
                device_data["memory"],
                device_data["disk"],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))

            conn_db.commit()

        except Exception as e:
            print(f"[ERROR] {e}")
            break

    conn.close()
    print(f"[DISCONNECTED] {addr}")


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()

print(f"[SERVER STARTED] Listening on port {PORT}")

while True:
    conn, addr = server.accept()
    thread = threading.Thread(target=handle_client, args=(conn, addr))
    thread.start()
    print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")