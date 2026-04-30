from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timedelta
import asyncio

app = FastAPI()

# ---------------- DATABASE ----------------
engine = create_engine(
    "sqlite:///metrics.db",
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class MetricDB(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True)
    device_id = Column(String)
    cpu = Column(Float)
    memory = Column(Float)
    disk = Column(Float)
    timestamp = Column(DateTime)


Base.metadata.create_all(bind=engine)


# ---------------- STATE ----------------
dashboard_connections = set()
active_devices = {}
device_last_seen = {}

TIMEOUT_SECONDS = 5


# ---------------- DEVICE STATUS ----------------
async def monitor_devices():
    while True:
        now = datetime.utcnow()
        statuses = {}

        for device_id, last_seen in device_last_seen.items():
            delta = (now - last_seen).total_seconds()
            statuses[device_id] = "online" if delta < TIMEOUT_SECONDS else "offline"

        dead = set()

        for conn in dashboard_connections:
            try:
                await conn.send_json({
                    "type": "status_update",
                    "statuses": statuses
                })
            except:
                dead.add(conn)

        dashboard_connections.difference_update(dead)

        await asyncio.sleep(2)


@app.on_event("startup")
async def startup():
    asyncio.create_task(monitor_devices())


# ---------------- HISTORY ----------------
@app.get("/history/{device_id}")
def history(device_id: str, minutes: int = 60):
    db = SessionLocal()
    cutoff = datetime.utcnow() - timedelta(minutes=minutes)

    rows = db.query(MetricDB)\
        .filter(MetricDB.device_id == device_id)\
        .filter(MetricDB.timestamp >= cutoff)\
        .order_by(MetricDB.timestamp.asc())\
        .all()

    db.close()

    return [
        {
            "device_id": r.device_id,
            "cpu": r.cpu,
            "memory": r.memory,
            "disk": r.disk,
            "timestamp": r.timestamp.isoformat()
        }
        for r in rows
    ]


# ---------------- AGENTS ----------------
@app.websocket("/ws/agents")
async def agents(ws: WebSocket):
    await ws.accept()

    db = SessionLocal()
    device_id = None

    try:
        init = await ws.receive_json()
        requested = init.get("device_id")

        if not requested:
            await ws.close()
            return

        if requested in active_devices:
            await ws.send_json({"status": "error", "message": "Device ID in use"})
            await ws.close()
            return

        device_id = requested
        active_devices[device_id] = ws
        device_last_seen[device_id] = datetime.utcnow()

        await ws.send_json({"status": "ok"})

        while True:
            data = await ws.receive_json()

            device_last_seen[device_id] = datetime.utcnow()

            entry = MetricDB(
                device_id=device_id,
                cpu=data["cpu"],
                memory=data["memory"],
                disk=data["disk"],
                timestamp=datetime.utcnow()
            )

            db.add(entry)
            db.commit()

            payload = {
                "type": "metric",
                "device_id": device_id,
                "cpu": entry.cpu,
                "memory": entry.memory,
                "disk": entry.disk,
                "timestamp": entry.timestamp.isoformat()
            }

            dead = set()

            for conn in dashboard_connections:
                try:
                    await conn.send_json(payload)
                except:
                    dead.add(conn)

            dashboard_connections.difference_update(dead)

    finally:
        if device_id:
            active_devices.pop(device_id, None)
        db.close()


# ---------------- DASHBOARD ----------------
@app.websocket("/ws/dashboard")
async def dashboard_ws(ws: WebSocket):
    await ws.accept()
    dashboard_connections.add(ws)

    try:
        while True:
            await ws.receive_text()
    except:
        dashboard_connections.remove(ws)


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return """
<!DOCTYPE html>
<html>
<head>
<title>System Monitor</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<style>
body {
    font-family: -apple-system, sans-serif;
    margin: 0;
    background: #f5f5f7;
    color: #1d1d1f;
}

header {
    padding: 18px;
    background: #fafafc;
    border-bottom: 1px solid #e5e5ea;
    font-weight: 600;
}

.container { padding: 20px; }

.grid {
    display: grid;
    grid-template-columns: 260px 1fr;
    gap: 20px;
}

.card {
    background: #fafafc;
    padding: 15px;
    border-radius: 14px;
    border: 1px solid #e5e5ea;
}

select, button {
    width: 100%;
    margin-top: 10px;
    padding: 10px;
    border-radius: 10px;
    border: 1px solid #e5e5ea;
    background: #fafafc;
    color: #1d1d1f;
}

button { cursor: pointer; }

.status-online { color: #16a34a; }
.status-offline { color: #dc2626; }
</style>
</head>

<body>

<header>⚡ System Monitoring Dashboard</header>

<div class="container">
<div class="grid">

<div class="card">
<h3>Devices</h3>
<ul id="statusList"></ul>

<select id="deviceSelect"></select>

<h3>History</h3>

<select id="timeRange">
<option value="5">5 min</option>
<option value="30">30 min</option>
<option value="60">1 hour</option>
<option value="1440">24 hours</option>
</select>

<button onclick="loadHistory()">Load History</button>
<button onclick="backToLive()">Back to Live</button>

</div>

<div class="card">
<h3>CPU</h3>
<canvas id="cpu"></canvas>

<h3>Memory</h3>
<canvas id="mem"></canvas>

<h3>Disk</h3>
<canvas id="disk"></canvas>
</div>

</div>
</div>

<script>
const ws = new WebSocket((location.protocol === "https:" ? "wss" : "ws") + "://" + location.host + "/ws/dashboard");

const deviceSelect = document.getElementById("deviceSelect");
const statusList = document.getElementById("statusList");

let store = {};
let deviceStatus = {};
let historyMode = false;
let initialized = false;

function makeChart(ctx) {
    return new Chart(ctx, {
        type: "line",
        data: { labels: [], datasets: [{ data: [], tension: 0.35, fill: true }] },
        options: {
            animation: false,
            scales: { y: { min: 0, max: 100 } }
        }
    });
}

const cpuChart = makeChart(document.getElementById("cpu"));
const memChart = makeChart(document.getElementById("mem"));
const diskChart = makeChart(document.getElementById("disk"));

function gradient(chart, values) {
    const ctx = chart.ctx;
    const g = ctx.createLinearGradient(0, 0, 0, 300);

    g.addColorStop(0, "#dc2626"); // red top
    g.addColorStop(0.5, "#facc15"); // yellow middle
    g.addColorStop(1, "#16a34a"); // green bottom

    chart.data.datasets[0].borderColor = g;
    chart.data.datasets[0].backgroundColor = "rgba(22,163,74,0.08)";
}

function render(device) {
    const data = store[device] || [];

    const labels = data.map(d => new Date(d.timestamp).toLocaleTimeString());

    const cpu = data.map(d => d.cpu);
    const mem = data.map(d => d.memory);
    const disk = data.map(d => d.disk);

    cpuChart.data.labels = labels;
    memChart.data.labels = labels;
    diskChart.data.labels = labels;

    cpuChart.data.datasets[0].data = cpu;
    memChart.data.datasets[0].data = mem;
    diskChart.data.datasets[0].data = disk;

    gradient(cpuChart, cpu);
    gradient(memChart, mem);
    gradient(diskChart, disk);

    cpuChart.update();
    memChart.update();
    diskChart.update();
}

function updateDropdown() {
    const cur = deviceSelect.value;
    deviceSelect.innerHTML = "";

    Object.keys(store).forEach(d => {
        const opt = document.createElement("option");
        opt.value = d;
        opt.text = d;
        deviceSelect.appendChild(opt);
    });

    if (cur && store[cur]) deviceSelect.value = cur;
}

function renderStatus() {
    statusList.innerHTML = "";

    Object.keys(deviceStatus).forEach(d => {
        const li = document.createElement("li");
        li.innerHTML = `<b>${d}</b> - <span class="${deviceStatus[d] === "online" ? "status-online" : "status-offline"}">${deviceStatus[d]}</span>`;
        statusList.appendChild(li);
    });
}

async function loadHistory() {
    const device = deviceSelect.value;
    const minutes = document.getElementById("timeRange").value;

    historyMode = true;

    const res = await fetch(`/history/${device}?minutes=${minutes}`);
    const data = await res.json();

    store[device] = data;
    render(device);
}

function backToLive() {
    historyMode = false;
}

deviceSelect.onchange = () => render(deviceSelect.value);

ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);

    if (msg.type === "status_update") {
        deviceStatus = msg.statuses;
        renderStatus();
        return;
    }

    if (msg.type === "metric") {
        if (historyMode) return;

        if (!store[msg.device_id]) store[msg.device_id] = [];

        store[msg.device_id].push(msg);
        store[msg.device_id] = store[msg.device_id].slice(-30);

        updateDropdown();

        if (!initialized) {
            deviceSelect.value = msg.device_id;
            initialized = true;
        }

        render(deviceSelect.value);
    }
};
</script>

</body>
</html>
"""