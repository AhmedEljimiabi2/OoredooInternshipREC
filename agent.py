"""
agent.py — Device Agent (Client)
Collects system metrics every 3 seconds using psutil and sends
them as JSON to the central socket server.

Usage:
    python agent.py
    python agent.py --host 192.168.1.10   # if server is on another machine
"""

import socket
import json
import time
import platform
import argparse
import datetime

import psutil

# ── Config ───────────────────────────────────────────────────────────────────

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9000
SEND_INTERVAL = 3          # seconds between each metric snapshot
DEVICE_NAME = platform.node()   # hostname of this machine


# ── Helpers ──────────────────────────────────────────────────────────────────

def get_local_ip() -> str:
    """Return the machine's primary LAN IP address."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def collect_metrics() -> dict:
    """Gather CPU, memory and disk stats and return as a dict."""
    return {
        "device_name": DEVICE_NAME,
        "ip":          get_local_ip(),
        "cpu":         psutil.cpu_percent(interval=1),   # 1-second sample
        "memory":      psutil.virtual_memory().percent,
        "disk":        psutil.disk_usage("/").percent,
        "timestamp":   datetime.datetime.now().isoformat(),
    }


# ── Main loop ────────────────────────────────────────────────────────────────

def run_agent(host: str, port: int):
    print(f"[Agent] Device: {DEVICE_NAME}")
    print(f"[Agent] Connecting to server at {host}:{port} ...")

    while True:          # reconnect loop — keeps retrying if server is down
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((host, port))
                print(f"[Agent] Connected. Sending metrics every {SEND_INTERVAL}s.")
                while True:
                    metrics = collect_metrics()
                    message = json.dumps(metrics) + "\n"   # newline = message delimiter
                    sock.sendall(message.encode("utf-8"))
                    print(f"  [sent] CPU={metrics['cpu']}% | "
                          f"MEM={metrics['memory']}% | DISK={metrics['disk']}%")
                    time.sleep(SEND_INTERVAL)

        except (ConnectionRefusedError, ConnectionResetError, OSError) as e:
            print(f"[Agent] Connection error: {e}. Retrying in 5 s...")
            time.sleep(5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Device Monitoring Agent")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Server IP address")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Server port")
    args = parser.parse_args()

    run_agent(args.host, args.port)
