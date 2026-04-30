import psutil
import asyncio
import json
import websockets

URL = "wss://footing-generous-proofing.ngrok-free.dev/ws/agents"


async def run():
    device_id = input("Enter device ID: ")

    ws = await websockets.connect(URL)
    await ws.send(json.dumps({"device_id": device_id}))

    resp = json.loads(await ws.recv())

    if resp.get("status") != "ok":
        print("❌", resp.get("message"))
        return

    print("Connected")

    while True:
        data = {
            "cpu": psutil.cpu_percent(),
            "memory": psutil.virtual_memory().percent,
            "disk": psutil.disk_usage("/").percent
        }

        await ws.send(json.dumps(data))
        await asyncio.sleep(2)


asyncio.run(run())