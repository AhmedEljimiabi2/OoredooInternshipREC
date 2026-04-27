import socket
import json
import time
import psutil
import platform
import uuid
import os

SERVER_IP = "127.0.0.1"   # change on partner device
PORT = 5000

DEVICE_ID_FILE = "device_id.txt"

def get_device_id():
    if os.path.exists(DEVICE_ID_FILE):
        with open(DEVICE_ID_FILE, "r") as f:
            return f.read().strip()
    else:
        device_id = str(uuid.uuid4())
        with open(DEVICE_ID_FILE, "w") as f:
            f.write(device_id)
        return device_id

DEVICE_ID = get_device_id()

def get_device_data():
    return {
        "device_id": DEVICE_ID,
        "device_name": platform.node(),
        "ip": socket.gethostbyname(socket.gethostname()),
        "cpu": psutil.cpu_percent(interval=1),
        "memory": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage("/").percent
    }

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((SERVER_IP, PORT))

while True:
    data = get_device_data()
    message = json.dumps(data) + "\n"   # IMPORTANT
    client.send(message.encode("utf-8"))
    time.sleep(3)