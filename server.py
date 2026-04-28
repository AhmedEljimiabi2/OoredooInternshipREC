from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

app = FastAPI()

# ---------------- DB ----------------
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


# ---------------- CONNECTIONS ----------------
dashboard_connections = set()


# ---------------- AGENT WEBSOCKET ----------------
@app.websocket("/ws/agents")
async def ws_agents(websocket: WebSocket):
    await websocket.accept()

    db = SessionLocal()

    try:
        while True:
            data = await websocket.receive_json()

            # 🧠 SERVER generates timestamp (FIX for Invalid Date)
            entry = MetricDB(
                device_id=data["device_id"],
                cpu=data["cpu"],
                memory=data["memory"],
                disk=data["disk"],
                timestamp=datetime.utcnow()
            )

            db.add(entry)
            db.commit()

            payload = {
                "device_id": entry.device_id,
                "cpu": entry.cpu,
                "memory": entry.memory,
                "disk": entry.disk,
                "timestamp": entry.timestamp.isoformat()
            }

            # 🚀 broadcast to dashboard
            dead = set()

            for conn in dashboard_connections:
                try:
                    await conn.send_json(payload)
                except:
                    dead.add(conn)

            dashboard_connections.difference_update(dead)

    except:
        db.close()


# ---------------- DASHBOARD WEBSOCKET ----------------
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
    <title>Real-Time Monitor</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>

<body style="font-family: Arial; padding: 20px;">

<h2>System Monitor</h2>

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
const ws = new WebSocket(protocol + "://" + location.host + "/ws/dashboard");

const deviceSelect = document.getElementById("deviceSelect");

function chart(ctx, label) {
    return new Chart(ctx, {
        type: "line",
        data: { labels: [], datasets: [{ label, data: [], borderWidth: 2 }] },
        options: {
            animation: false,
            scales: { y: { min: 0, max: 100 } }
        }
    });
}

const cpuChart = chart(document.getElementById("cpu"), "CPU %");
const memChart = chart(document.getElementById("mem"), "Memory %");
const diskChart = chart(document.getElementById("disk"), "Disk %");

let store = {};

function updateDropdown() {
    deviceSelect.innerHTML = "";

    Object.keys(store).forEach(device => {
        const opt = document.createElement("option");
        opt.value = device;
        opt.text = device;
        deviceSelect.appendChild(opt);
    });
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

    if (!deviceSelect.value) {
        deviceSelect.value = d.device_id;
    }

    render(deviceSelect.value);
};
</script>

</body>
</html>
"""