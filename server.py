from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse

app = FastAPI()

# connected clients
agent_connections = set()
dashboard_connections = set()


# -------------------------
# AGENT WEBSOCKET
# -------------------------
@app.websocket("/ws/agents")
async def ws_agents(websocket: WebSocket):
    await websocket.accept()
    agent_connections.add(websocket)

    try:
        while True:
            data = await websocket.receive_json()

            # broadcast to dashboards
            dead_dashboards = set()

            for conn in dashboard_connections:
                try:
                    await conn.send_json(data)
                except:
                    dead_dashboards.add(conn)

            dashboard_connections.difference_update(dead_dashboards)

    except:
        agent_connections.remove(websocket)


# -------------------------
# DASHBOARD WEBSOCKET
# -------------------------
@app.websocket("/ws/dashboard")
async def ws_dashboard(websocket: WebSocket):
    await websocket.accept()
    dashboard_connections.add(websocket)

    try:
        while True:
            await websocket.receive_text()  # keep alive
    except:
        dashboard_connections.remove(websocket)


# -------------------------
# DASHBOARD UI
# -------------------------
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

<h2>⚡ Real-Time System Monitor (WebSocket)</h2>

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

function makeChart(ctx, label) {
    return new Chart(ctx, {
        type: "line",
        data: { labels: [], datasets: [{ label, data: [], borderWidth: 2 }] },
        options: { animation: false, scales: { y: { min: 0, max: 100 } } }
    });
}

const cpuChart = makeChart(document.getElementById("cpu"), "CPU %");
const memChart = makeChart(document.getElementById("mem"), "Memory %");
const diskChart = makeChart(document.getElementById("disk"), "Disk %");

let store = {};

function updateDropdown() {
    const devices = Object.keys(store);

    deviceSelect.innerHTML = "";

    devices.forEach(d => {
        const opt = document.createElement("option");
        opt.value = d;
        opt.text = d;
        deviceSelect.appendChild(opt);
    });
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