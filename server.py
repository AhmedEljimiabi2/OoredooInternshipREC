import socket
import threading
import json
import sqlite3
from datetime import datetime

HOST = "0.0.0.0"
PORT = 5000

# ---------------- DB ----------------

conn_db = sqlite3.connect("devices.db", check_same_thread=False)
cursor = conn_db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS device_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT,
    device_name TEXT,
    ip TEXT,
    cpu REAL,
    memory REAL,
    disk REAL,
    timestamp TEXT
)
""")

conn_db.commit()

# ---------------- CLIENT HANDLER ----------------

def handle_client(conn, addr):
    print(f"[CONNECTED] {addr}")

    buffer = ""

    while True:
        try:
            data = conn.recv(4096)
            if not data:
                break

            buffer += data.decode("utf-8")

            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)

                if not line.strip():
                    continue

                d = json.loads(line)

                cursor.execute("""
                INSERT INTO device_data (
                    device_id, device_name, ip,
                    cpu, memory, disk, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    d["device_id"],
                    d["device_name"],
                    d["ip"],
                    d["cpu"],
                    d["memory"],
                    d["disk"],
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))

                conn_db.commit()

        except Exception as e:
            print("[ERROR]", e)
            break

    conn.close()
    print(f"[DISCONNECTED] {addr}")

# ---------------- SERVER ----------------

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()

print(f"[SERVER STARTED] {PORT}")

while True:
    conn, addr = server.accept()
    thread = threading.Thread(target=handle_client, args=(conn, addr))
    thread.start()