import socket
import json
import threading
import time

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Metric

from django.utils.timezone import now

# ================= GLOBAL STATE =================

status = {}
ips = {}
last_seen = {}

TIMEOUT_SECONDS = 5

# ================= WEBSOCKET BROADCAST =================

def broadcast(data):

    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        'metrics',
        {
            'type': 'metric_update',
            'data': data
        }
    )

# ================= STATUS BROADCAST =================

def broadcast_status():

    broadcast({
        'type': 'status',
        'status': status,
        'ips': ips
    })

# ================= PACKET HANDLER =================

def handle_packet(data, addr):

    try:
        msg = json.loads(data.decode())

        device_id = msg['device_id']

        # UPDATE HEARTBEAT
        last_seen[device_id] = time.time()

        # MARK ONLINE
        status[device_id] = 'Online'

        ips[device_id] = addr[0]

        metric = Metric.objects.create(
            device_id=device_id,
            ip=addr[0],
            cpu=msg['cpu'],
            memory=msg['memory'],
            disk=msg['disk']
        )

        # LIVE METRIC BROADCAST
        broadcast({
            'type': 'metric',
            'device_id': metric.device_id,
            'cpu': metric.cpu,
            'memory': metric.memory,
            'disk': metric.disk,
            'timestamp': metric.timestamp.isoformat()
        })

        # STATUS BROADCAST
        broadcast_status()

    except Exception as e:
        print('Packet error:', e)

# ================= OFFLINE MONITOR =================

def offline_monitor():

    while True:

        current = time.time()

        changed = False

        for device_id in list(last_seen.keys()):

            elapsed = current - last_seen[device_id]

            if elapsed > TIMEOUT_SECONDS:

                if status.get(device_id) != 'Offline':

                    status[device_id] = 'Offline'

                    changed = True

        if changed:
            broadcast_status()

        time.sleep(1)

# ================= UDP SERVER =================

def start_udp_server():

    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    server.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    server.bind(('0.0.0.0', 9000))

    print('UDP telemetry server listening on port 9000')

    # START OFFLINE DETECTOR
    threading.Thread(
        target=offline_monitor,
        daemon=True
    ).start()

    while True:

        data, addr = server.recvfrom(4096)

        threading.Thread(
            target=handle_packet,
            args=(data, addr),
            daemon=True
        ).start()