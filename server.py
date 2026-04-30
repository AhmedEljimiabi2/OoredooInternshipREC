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


# ---------------- BACKGROUND STATUS ----------------
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
async def startup_event():
    asyncio.create_task(monitor_devices())


# ---------------- HISTORY API ----------------
@app.get("/history/{device_id}")
def get_history(device_id: str, minutes: int = 60):
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


# ---------------- AGENT SOCKET ----------------
@app.websocket("/ws/agents")
async def ws_agents(websocket: WebSocket):
    await websocket.accept()

    db = SessionLocal()
    device_id = None

    try:
        init = await websocket.receive_json()
        requested_id = init.get("device_id")

        if not requested_id:
            await websocket.close()
            return

        if requested_id in active_devices:
            await websocket.send_json({
                "status": "error",
                "message": "Device ID already in use"
            })
            await websocket.close()
            return

        device_id = requested_id
        active_devices[device_id] = websocket
        device_last_seen[device_id] = datetime.utcnow()

        await websocket.send_json({"status": "ok"})

        while True:
            data = await websocket.receive_json()

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

    except:
        pass

    finally:
        if device_id:
            active_devices.pop(device_id, None)
        db.close()


# ---------------- DASHBOARD SOCKET ----------------
@app.websocket("/ws/dashboard")
async def ws_dashboard(websocket: WebSocket):
    await websocket.accept()
    dashboard_connections.add(websocket)

    try:
        while True:
            await websocket.receive_text()
    except:
        dashboard_connections.remove(websocket)


# ---------------- DASHBOARD UI ----------------
@app.get("/", response_class=HTMLResponse)
def dashboard():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Monitor</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>

<body style="font-family: Arial; padding: 20px;">

<h2>⚡ System Monitor</h2>

<h3>Status</h3>
<ul id="statusList"></ul>

<label>Device:</label>
<select id="deviceSelect"></select>

<h3>History</h3>
<select id="timeRange">
    <option value="5">5 min</option>
    <option value="30">30 min</option>
    <option value="60" selected>1 hour</option>
    <option value="1440">24 hours</option>
</select>

<button onclick="loadHistory()">Load History</button>
<button onclick="backToLive()">Back to Live</button>

<h3>CPU</h3>
<canvas id="cpu"></canvas>

<h3>Memory</h3>
<canvas id="mem"></canvas>

<h3>Disk</h3>
<canvas id="disk"></canvas>

<script>
const protocol = location.protocol === "https:" ? "wss" : "ws";
const ws = new WebSocket(protocol + "://" + location.host + "/ws/dashboard");

const deviceSelect = document.getElementById("deviceSelect");
const statusList = document.getElementById("statusList");

let store = {};
let deviceStatus = {};
let initialized = false;
let historyMode = false;

function chart(ctx, label) {
    return new Chart(ctx, {
        type: "line",
        data: { labels: [], datasets: [{ label, data: [], tension: 0.3 }] },
        options: { animation: false, scales: { y: { min: 0, max: 100 } } }
    });
}

const cpuChart = chart(document.getElementById("cpu"), "CPU");
const memChart = chart(document.getElementById("mem"), "Memory");
const diskChart = chart(document.getElementById("disk"), "Disk");

function updateDropdown() {
    const current = deviceSelect.value;
    deviceSelect.innerHTML = "";

    Object.keys(store).forEach(d => {
        const opt = document.createElement("option");
        opt.value = d;
        opt.text = d;
        deviceSelect.appendChild(opt);
    });

    if (current && store[current]) deviceSelect.value = current;
}

function render(device) {
    const data = store[device] || [];

    const labels = data.map(d => {
        const t = new Date(d.timestamp);
        return isNaN(t) ? "" : t.toLocaleTimeString();
    });

    cpuChart.data.labels = labels;
    memChart.data.labels = labels;
    diskChart.data.labels = labels;

    cpuChart.data.datasets[0].data = data.map(d => d.cpu);
    memChart.data.datasets[0].data = data.map(d => d.memory);
    diskChart.data.datasets[0].data = data.map(d => d.disk);

    cpuChart.update();
    memChart.update();
    diskChart.update();
}

function renderStatus() {
    statusList.innerHTML = "";

    Object.keys(deviceStatus).forEach(d => {
        const li = document.createElement("li");
        li.textContent = `${d}: ${deviceStatus[d]}`;
        li.style.color = deviceStatus[d] === "online" ? "green" : "red";
        statusList.appendChild(li);
    });
}

async function loadHistory() {
    const device = deviceSelect.value;
    const minutes = document.getElementById("timeRange").value;

    if (!device) return;

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

ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);

    if (msg.type === "status_update") {
        deviceStatus = msg.statuses;
        renderStatus();
        return;
    }

    if (msg.type === "metric") {
        if (historyMode) return;

        const d = msg;

        if (!store[d.device_id]) store[d.device_id] = [];

        store[d.device_id].push(d);
        store[d.device_id] = store[d.device_id].slice(-30);

        updateDropdown();

        if (!initialized) {
            deviceSelect.value = d.device_id;
            initialized = true;
        }

        render(deviceSelect.value);
    }
};
</script>

</body>
</html>
"""