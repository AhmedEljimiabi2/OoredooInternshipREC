from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import sqlite3
import threading

app = FastAPI()

agent_connections = set()
dashboard_connections = set()

db_lock = threading.Lock()

conn = sqlite3.connect("metrics.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT,
    hostname TEXT,
    cpu REAL,
    memory REAL,
    disk REAL,
    timestamp TEXT
)
""")
conn.commit()


def save_metric(data):
    with db_lock:
        cursor.execute(
            """
            INSERT INTO metrics (device_id, hostname, cpu, memory, disk, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("device_id"),
                data.get("hostname"),
                data.get("cpu"),
                data.get("memory"),
                data.get("disk"),
                data.get("timestamp")
            )
        )
        conn.commit()


@app.websocket("/ws/agents")
async def ws_agents(websocket: WebSocket):
    await websocket.accept()
    agent_connections.add(websocket)
    print("Agent connected")

    try:
        while True:
            data = await websocket.receive_json()

            save_metric(data)

            dead_dashboards = set()

            for conn_dash in dashboard_connections:
                try:
                    await conn_dash.send_json(data)
                except:
                    dead_dashboards.add(conn_dash)

            dashboard_connections.difference_update(dead_dashboards)

    except Exception as e:
        print("Agent disconnected:", e)
        agent_connections.discard(websocket)


@app.websocket("/ws/dashboard")
async def ws_dashboard(websocket: WebSocket):
    await websocket.accept()
    dashboard_connections.add(websocket)
    print("Dashboard connected")

    try:
        while True:
            await websocket.receive_text()

    except Exception as e:
        print("Dashboard disconnected:", e)
        dashboard_connections.discard(websocket)


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

<h3>CPU Usage</h3>
<canvas id="cpu"></canvas>

<h3>Memory Usage</h3>
<canvas id="mem"></canvas>

<h3>Disk Usage</h3>
<canvas id="disk"></canvas>

<script>
const protocol = location.protocol === "https:" ? "wss" : "ws";
const ws = new WebSocket(protocol + "://" + location.host + "/ws/dashboard");

const deviceSelect = document.getElementById("deviceSelect");

function makeChart(ctx, label) {
    return new Chart(ctx, {
        type: "line",
        data: {
            labels: [],
            datasets: [{
                label: label,
                data: [],
                borderWidth: 2
            }]
        },
        options: {
            animation: false,
            responsive: true,
            scales: {
                y: {
                    min: 0,
                    max: 100
                }
            }
        }
    });
}

const cpuChart = makeChart(document.getElementById("cpu"), "CPU %");
const memChart = makeChart(document.getElementById("mem"), "Memory %");
const diskChart = makeChart(document.getElementById("disk"), "Disk %");

let store = {};

function updateDropdown() {
    const selected = deviceSelect.value;
    const devices = Object.keys(store);

    deviceSelect.innerHTML = "";

    devices.forEach(device => {
        const opt = document.createElement("option");
        opt.value = device;
        opt.text = device;
        deviceSelect.appendChild(opt);
    });

    if (devices.includes(selected)) {
        deviceSelect.value = selected;
    }
}

function render(device) {
    const data = store[device] || [];

    const labels = data.map(d =>
        new Date(d.timestamp).toLocaleTimeString()
    );

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

deviceSelect.onchange = () => {
    render(deviceSelect.value);
};

ws.onmessage = (event) => {
    const d = JSON.parse(event.data);

    if (!store[d.device_id]) {
        store[d.device_id] = [];
    }

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