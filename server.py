from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

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

# ---------------- AUTH (optional) ----------------
VALID_API_KEYS = {
    "key_abc123": "device-1",
    "key_xyz789": "vm-device"
}

# ---------------- CONNECTIONS ----------------
dashboard_connections = set()


# ---------------- AGENT SOCKET ----------------
@app.websocket("/ws/agents")
async def ws_agents(websocket: WebSocket):

    api_key = websocket.query_params.get("api_key")

    if api_key not in VALID_API_KEYS:
        await websocket.close(code=1008)
        return

    device_id = VALID_API_KEYS[api_key]

    await websocket.accept()

    db = SessionLocal()

    try:
        while True:
            data = await websocket.receive_json()

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
                "device_id": device_id,
                "cpu": data["cpu"],
                "memory": data["memory"],
                "disk": data["disk"],
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
        db.close()


# ---------------- DASHBOARD SOCKET ----------------
@app.websocket("/ws/dashboard")
async def ws_dashboard(websocket: WebSocket):

    key = websocket.query_params.get("key")
    if key != "dashboard_secret":
        await websocket.close(code=1008)
        return

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
    <title>Real-Time Monitor</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>

<body style="font-family: Arial; padding: 20px;">

<h2>⚡ Real-Time System Monitor</h2>

<label>Device:</label>
<select id="deviceSelect"></select>

<h3>CPU</h3>
<canvas id="cpu"></canvas>

<h3>Memory</h3>
<canvas id="mem"></canvas>

<h3>Disk</h3>
<canvas id="disk"></canvas>

<script>

const protocol = location.protocol === "https:" ? "wss" : "ws";

const ws = new WebSocket(
    protocol + "://" + location.host + "/ws/dashboard?key=dashboard_secret"
);

const deviceSelect = document.getElementById("deviceSelect");

let store = {};
let initialized = false;

function chart(ctx, label) {
    return new Chart(ctx, {
        type: "line",
        data: {
            labels: [],
            datasets: [{ label, data: [], borderWidth: 2 }]
        },
        options: {
            animation: false,
            scales: { y: { min: 0, max: 100 } }
        }
    });
}

const cpuChart = chart(document.getElementById("cpu"), "CPU %");
const memChart = chart(document.getElementById("mem"), "Memory %");
const diskChart = chart(document.getElementById("disk"), "Disk %");


function updateDropdown() {
    const devices = Object.keys(store);
    const current = deviceSelect.value;

    deviceSelect.innerHTML = "";

    devices.forEach(d => {
        const opt = document.createElement("option");
        opt.value = d;
        opt.text = d;
        deviceSelect.appendChild(opt);
    });

    // 🔥 preserve selection (FIX)
    if (devices.includes(current)) {
        deviceSelect.value = current;
    }
}


function render(device) {
    const data = store[device] || [];

    const labels = data.map(d => {
        const ts = new Date(d.timestamp);
        return isNaN(ts) ? "" : ts.toLocaleTimeString();
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


deviceSelect.onchange = () => render(deviceSelect.value);


ws.onmessage = (event) => {
    const d = JSON.parse(event.data);

    if (!store[d.device_id]) store[d.device_id] = [];

    store[d.device_id].push(d);
    store[d.device_id] = store[d.device_id].slice(-30);

    updateDropdown();

    // 🔥 set default only once
    if (!initialized) {
        deviceSelect.value = d.device_id;
        initialized = true;
    }

    render(deviceSelect.value);
};

</script>

</body>
</html>
"""