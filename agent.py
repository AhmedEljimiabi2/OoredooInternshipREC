import socket
import json
import psutil
import time

HOST = "192.168.10.189"
PORT = 9000


def connect(device):
    s = socket.socket()
    s.connect((HOST, PORT))

    s.send(json.dumps({"device_id": device}).encode())

    res = json.loads(s.recv(1024).decode())

    if res["status"] != "ok":
        print("ID in use")
        return None

    return s


def run():
    while True:
        d = input("Device ID: ")
        sock = connect(d)
        if sock:
            break

    while True:
        data = {
            "cpu": psutil.cpu_percent(),
            "memory": psutil.virtual_memory().percent,
            "disk": psutil.disk_usage('/').percent
        }

        try:
            sock.send(json.dumps(data).encode())
        except:
            print("Reconnecting...")
            return run()

        time.sleep(2)


run()