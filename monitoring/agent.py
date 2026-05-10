import socket
import json
import psutil
import time

HOST = '192.168.10.189'
PORT = 9000

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

device_id = input('Device ID: ')

while True:

    data = {
        'device_id': device_id,
        'cpu': psutil.cpu_percent(),
        'memory': psutil.virtual_memory().percent,
        'disk': psutil.disk_usage('/').percent
    }

    sock.sendto(
        json.dumps(data).encode(),
        (HOST, PORT)
    )

    time.sleep(2)