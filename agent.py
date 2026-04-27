import socket
import json
import time
import psutil
import platform

SERVER_IP = "127.0.0.1"
PORT = 5000

def get_device_data():
    return {
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
    message = json.dumps(data)
    client.send(message.encode("utf-8"))
    time.sleep(3)
    