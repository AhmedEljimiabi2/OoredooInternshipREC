"""
server.py — Central Socket Server
Listens for incoming device connections, receives JSON metrics,
and stores them in a SQLite database. Uses threads to handle
multiple devices at the same time.
"""

import socket
import threading
import json
import sqlite3
import datetime

HOST = "0.0.0.0"   # Listen on all interfaces
PORT = 9000        # Port agents connect to
DB_PATH = "devices.db"


# ── Database setup ──────────────────────────────────────────────────────────

def init_db():
    """Create the metrics table if it doesn't already exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metrics (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            device_name TEXT    NOT NULL,
            ip          TEXT    NOT NULL,
            cpu         REAL    NOT NULL,
            memory      REAL    NOT NULL,
            disk        REAL    NOT NULL,
            timestamp   TEXT    NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    print("[DB] Database ready.")


def save_metric(data: dict):
    """Insert one metric record into the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO metrics (device_name, ip, cpu, memory, disk, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        data["device_name"],
        data["ip"],
        data["cpu"],
        data["memory"],
        data["disk"],
        data.get("timestamp", datetime.datetime.now().isoformat())
    ))
    conn.commit()
    conn.close()


# ── Client handler ───────────────────────────────────────────────────────────

def handle_client(conn: socket.socket, addr):
    """
    Runs in its own thread for each connected agent.
    Reads newline-delimited JSON messages until the agent disconnects.
    """
    print(f"[+] Device connected: {addr}")
    buffer = ""
    try:
        while True:
            chunk = conn.recv(4096).decode("utf-8")
            if not chunk:
                break                       # Agent disconnected
            buffer += chunk
            # An agent may send multiple messages; split on newlines
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    save_metric(data)
                    print(f"  [metric] {data['device_name']} — "
                          f"CPU {data['cpu']}% | MEM {data['memory']}% | DISK {data['disk']}%")
                except json.JSONDecodeError as e:
                    print(f"  [!] Bad JSON from {addr}: {e}")
    except ConnectionResetError:
        pass
    finally:
        conn.close()
        print(f"[-] Device disconnected: {addr}")


# ── Main server loop ─────────────────────────────────────────────────────────

def start_server():
    init_db()
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((HOST, PORT))
    server_sock.listen(10)
    print(f"[Server] Listening on {HOST}:{PORT} ...")

    while True:
        conn, addr = server_sock.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
        thread.start()


if __name__ == "__main__":
    start_server()
