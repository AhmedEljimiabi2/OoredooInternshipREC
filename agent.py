import psutil
import asyncio
import json
import websockets

# IMPORTANT: replace with your ngrok ws URL
URL = "wss://footing-generous-proofing.ngrok-free.dev/ws/agents"

DEVICE_ID = "device-1"  # change on each computer


async def run():
    while True:
        try:
            async with websockets.connect(URL) as ws:

                while True:
                    data = {
                        "device_id": DEVICE_ID,
                        "cpu": psutil.cpu_percent(),
                        "memory": psutil.virtual_memory().percent,
                        "disk": psutil.disk_usage('/').percent,
                        "timestamp": ""
                    }

                    await ws.send(json.dumps(data))
                    print("sent:", data)

                    await asyncio.sleep(2)

        except Exception as e:
            print("Disconnected, retrying...", e)
            await asyncio.sleep(3)


asyncio.run(run())