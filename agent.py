import psutil
import asyncio
import json
import websockets
from datetime import datetime
import platform

# Replace with your ngrok WebSocket URL
URL = "wss://footing-generous-proofing.ngrok-free.dev/ws/agents"

# Change this on each computer
DEVICE_ID = "device-2"


async def run():
    while True:
        try:
            async with websockets.connect(URL) as ws:
                print("Connected to server")

                while True:
                    data = {
                        "device_id": DEVICE_ID,
                        "hostname": platform.node(),
                        "cpu": psutil.cpu_percent(interval=1),
                        "memory": psutil.virtual_memory().percent,
                        "disk": psutil.disk_usage("/").percent,
                        "timestamp": datetime.now().isoformat()
                    }

                    await ws.send(json.dumps(data))
                    print("sent:", data)

                    await asyncio.sleep(1)

        except Exception as e:
            print("Disconnected, retrying...", e)
            await asyncio.sleep(3)


asyncio.run(run())