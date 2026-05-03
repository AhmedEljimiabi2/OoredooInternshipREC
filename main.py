import socket
import threading
import json
from datetime import datetime, timedelta

from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import asyncio

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

# ================= DATABASE =================
engine = create_engine(
    "sqlite:///metrics.db",
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Metric(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True)
    device_id = Column(String)
    ip = Column(String)
    cpu = Column(Float)
    memory = Column(Float)
    disk = Column(Float)
    timestamp = Column(DateTime)


Base.metadata.create_all(bind=engine)

# ================= STATE =================
devices = {}
status = {}
ips = {}
last_seen = {}

clients = set()

app = FastAPI()


# ================= SOCKET SERVER =================
def handle_client(conn, addr):
    db = SessionLocal()
    device_id = None

    try:
        init = json.loads(conn.recv(1024).decode())
        device_id = init["device_id"]

        devices.setdefault(device_id, {
            "cpu": [],
            "memory": [],
            "disk": [],
            "time": []
        })

        status[device_id] = "Online"
        ips[device_id] = addr[0]

        conn.send(json.dumps({"status": "ok"}).encode())

        while True:
            data = conn.recv(1024)
            if not data:
                break

            msg = json.loads(data.decode())
            now = datetime.utcnow()

            last_seen[device_id] = now
            status[device_id] = "Online"

            entry = Metric(
                device_id=device_id,
                ip=addr[0],
                cpu=msg["cpu"],
                memory=msg["memory"],
                disk=msg["disk"],
                timestamp=now
            )

            db.add(entry)
            db.commit()

            d = devices[device_id]

            d["cpu"].append(msg["cpu"])
            d["memory"].append(msg["memory"])
            d["disk"].append(msg["disk"])
            d["time"].append(now.strftime("%H:%M:%S"))

            for k in d:
                d[k] = d[k][-50:]

            point = {
                "type": "metric",
                "device_id": device_id,
                "cpu": msg["cpu"],
                "memory": msg["memory"],
                "disk": msg["disk"],
                "timestamp": now.isoformat()
            }

            for c in list(clients):
                try:
                    asyncio.run(c.send_json(point))
                except:
                    clients.remove(c)

    finally:
        status[device_id] = "Offline"
        conn.close()
        db.close()


def start_socket():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", 9000))
    server.listen()

    print("Socket server running on 9000")

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


# ================= STATUS LOOP =================
async def status_loop():
    while True:
        now = datetime.utcnow()

        for d in list(last_seen.keys()):
            if (now - last_seen[d]).seconds > 5:
                status[d] = "Offline"

        for c in list(clients):
            try:
                await c.send_json({
                    "type": "status",
                    "status": status,
                    "ips": ips
                })
            except:
                clients.remove(c)

        await asyncio.sleep(2)


# ================= HISTORY API =================
@app.get("/history/{device_id}")
def history(device_id: str, minutes: int = 60):
    db = SessionLocal()
    cutoff = datetime.utcnow() - timedelta(minutes=minutes)

    rows = db.query(Metric)\
        .filter(Metric.device_id == device_id)\
        .filter(Metric.timestamp >= cutoff)\
        .order_by(Metric.timestamp.asc())\
        .all()

    db.close()

    return [
        {
            "cpu": r.cpu,
            "memory": r.memory,
            "disk": r.disk,
            "timestamp": r.timestamp.isoformat()
        }
        for r in rows
    ]


# ================= WEBSOCKET =================
@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)

    try:
        while True:
            await websocket.receive_text()
    except:
        clients.remove(websocket)


# ================= LIGHT APPLE UI =================
@app.get("/", response_class=HTMLResponse)
def ui():
    return """
<!DOCTYPE html>
<html>
<head>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<style>
body {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: #f5f6fa;
    color: #1c1c1e;
}

.header {
    padding: 20px;
    font-size: 22px;
    font-weight: 600;
}

.panel {
    margin: 20px;
    padding: 20px;
    border-radius: 18px;
    background: rgba(255,255,255,0.9);
    backdrop-filter: blur(15px);
    box-shadow: 0 8px 20px rgba(0,0,0,0.08);
    border: 1px solid rgba(0,0,0,0.05);
}

select {
    padding: 10px;
    border-radius: 12px;
    border: 1px solid #ddd;
    background: white;
    color: #1c1c1e;
}

button {
    padding: 10px 14px;
    border-radius: 12px;
    border: none;
    background: #007aff;
    color: white;
    cursor: pointer;
}

button:hover {
    background: #005fdb;
}

table {
    width: 100%;
    margin-top: 10px;
    border-collapse: collapse;
}

td, th {
    padding: 10px;
    border-bottom: 1px solid #eee;
    text-align: center;
}

canvas {
    margin-top: 20px;
}
</style>
</head>

<body>

<div class="header">Device Monitor</div>

<div class="panel">

<select id="devices"></select>

<select id="range">
    <option value="5">5 min</option>
    <option value="30">30 min</option>
    <option value="60" selected>1 hour</option>
</select>

<button onclick="loadHistory()">History</button>
<button onclick="liveMode()">Live</button>

<table>
<tr><th>Device ID</th><th>Status</th><th>IP Address</th></tr>
<tbody id="table"></tbody>
</table>

</div>

<div class="panel">
<h3>CPU</h3>
<canvas id="cpu"></canvas>
</div>

<div class="panel">
<h3>Memory</h3>
<canvas id="mem"></canvas>
</div>

<div class="panel">
<h3>Disk</h3>
<canvas id="disk"></canvas>
</div>

<script>

const ws = new WebSocket("ws://" + location.host + "/ws");

let store = {};
let status = {};
let ips = {};
let historyMode = false;

const select = document.getElementById("devices");

function chart(id, label) {
    return new Chart(document.getElementById(id), {
        type: "line",
        data: { labels: [], datasets: [{ label, data: [] }] }
    });
}

const cpu = chart("cpu", "% Utilized");
const mem = chart("mem", "% Used");
const disk = chart("disk", "% Used");

ws.onmessage = e => {
    const msg = JSON.parse(e.data);

    if (msg.type === "metric") {
        if (historyMode) return;

        if (!store[msg.device_id]) {
            store[msg.device_id] = {
                cpu: [], memory: [], disk: [], time: []
            };
        }

        let d = store[msg.device_id];

        d.cpu.push(msg.cpu);
        d.memory.push(msg.memory);
        d.disk.push(msg.disk);
        d.time.push(new Date(msg.timestamp).toLocaleTimeString());

        if (d.cpu.length > 50) {
            d.cpu.shift();
            d.memory.shift();
            d.disk.shift();
            d.time.shift();
        }

        updateDropdown();
        render(select.value);
    }

    if (msg.type === "status") {
        status = msg.status;
        ips = msg.ips;
        renderTable();
    }
};

function updateDropdown() {
    const cur = select.value;
    select.innerHTML = "";

    Object.keys(store).forEach(d => {
        let o = document.createElement("option");
        o.value = d;
        o.text = d;
        select.appendChild(o);
    });

    select.value = cur;
}

select.onchange = () => render(select.value);

function render(device) {
    if (!store[device]) return;

    let d = store[device];

    cpu.data.labels = d.time;
    cpu.data.datasets[0].data = d.cpu;

    mem.data.labels = d.time;
    mem.data.datasets[0].data = d.memory;

    disk.data.labels = d.time;
    disk.data.datasets[0].data = d.disk;

    cpu.update();
    mem.update();
    disk.update();
}

function renderTable() {
    let t = document.getElementById("table");
    t.innerHTML = "";

    Object.keys(status).forEach(d => {
        t.innerHTML += `
        <tr>
        <td>${d}</td>
        <td style="color:${status[d]=='Online'?'green':'red'}">${status[d]}</td>
        <td>${ips[d] || ''}</td>
        </tr>`;
    });
}

async function loadHistory() {
    historyMode = true;

    let d = select.value;
    let r = document.getElementById("range").value;

    let res = await fetch(`/history/${d}?minutes=${r}`);
    let data = await res.json();

    store[d] = { cpu: [], memory: [], disk: [], time: [] };

    data.forEach(x => {
        store[d].cpu.push(x.cpu);
        store[d].memory.push(x.memory);
        store[d].disk.push(x.disk);
        store[d].time.push(new Date(x.timestamp).toLocaleTimeString());
    });

    render(d);
}

function liveMode() {
    historyMode = false;
}

</script>

</body>
</html>
"""


# ================= START =================
@app.on_event("startup")
def startup():
    threading.Thread(target=start_socket, daemon=True).start()
    asyncio.create_task(status_loop())