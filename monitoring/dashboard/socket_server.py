import socket
import json
import threading

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Metric

from django.utils.timezone import now

# ================= GLOBAL STATE =================

status = {}
ips = {}
last_seen = {}

# ================= UDP SERVER =================


def handle_packet(data, addr):

    try:
        msg = json.loads(data.decode())

        device_id = msg['device_id']

        status[device_id] = 'online'
        ips[device_id] = addr[0]
        last_seen[device_id] = now()

        metric = Metric.objects.create(
            device_id=device_id,
            ip=addr[0],
            cpu=msg['cpu'],
            memory=msg['memory'],
            disk=msg['disk']
        )

        channel_layer = get_channel_layer()

        async_to_sync(channel_layer.group_send)(
            'metrics',
            {
                'type': 'metric_update',
                'data': {
                    'type': 'metric',
                    'device_id': metric.device_id,
                    'cpu': metric.cpu,
                    'memory': metric.memory,
                    'disk': metric.disk,
                    'timestamp': metric.timestamp.isoformat()
                }
            }
        )

        async_to_sync(channel_layer.group_send)(
            'metrics',
            {
                'type': 'metric_update',
                'data': {
                    'type': 'status',
                    'status': status,
                    'ips': ips
                }
            }
        )

    except Exception as e:
        print('Packet error:', e)



def start_udp_server():

    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    server.bind(('0.0.0.0', 9000))

    print('UDP telemetry server listening on port 9000')

    while True:

        data, addr = server.recvfrom(4096)

        threading.Thread(
            target=handle_packet,
            args=(data, addr),
            daemon=True
        ).start()