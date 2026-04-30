import psutil
import asyncio
import json
import websockets

URL = "wss://footing-generous-proofing.ngrok-free.dev/ws/agents"


async def connect(device_id):
    try:
        ws = await websockets.connect(URL)

        await ws.send(json.dumps({"device_id": device_id}))

        response = json.loads(await ws.recv())

        if response.get("status") != "ok":
            print("❌", response.get("message"))
            await ws.close()
            return None

        print(f"✅ Connected as {device_id}")
        return ws

    except Exception as e:
        print("Connection error:", e)
        return None


async def run():
    while True:
        device_id = input("Enter device ID: ")
        ws = await connect(device_id)

        if ws:
            break

    while True:
        try:
            data = {
                "cpu": psutil.cpu_percent(),
                "memory": psutil.virtual_memory().percent,
                "disk": psutil.disk_usage('/').percent
            }

            await ws.send(json.dumps(data))
            await asyncio.sleep(2)

        except Exception as e:
            print("Disconnected, retrying...", e)
            await asyncio.sleep(2)
            return await run()


asyncio.run(run())