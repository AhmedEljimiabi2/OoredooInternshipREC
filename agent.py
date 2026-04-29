import psutil
import asyncio
import json
import websockets

URL = "wss://footing-generous-proofing.ngrok-free.dev/ws/agents"
DEVICE_ID = "device-1"

async def run():
    while True:
        try:
            async with websockets.connect(URL) as ws:
                while True:
                    data = {
                        "cpu": psutil.cpu_percent(),
                        "memory": psutil.virtual_memory().percent,
                        "disk": psutil.disk_usage('/').percent
                    }

                    await ws.send(json.dumps(data))
                    await asyncio.sleep(2)

        except Exception as e:
            print("reconnecting...", e)
            await asyncio.sleep(3)

asyncio.run(run())