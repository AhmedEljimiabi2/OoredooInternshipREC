import psutil
import requests
import time

URL = "https://footing-generous-proofing.ngrok-free.dev/metrics"
DEVICE_ID = "test-device"

while True:
    data = {
        "device_id": DEVICE_ID,
        "cpu": psutil.cpu_percent(),
        "memory": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage('/').percent
    }

    try:
        requests.post(URL, json=data)
        print("Sent:", data)
    except Exception as e:
        print("Error:", e)

    time.sleep(2)