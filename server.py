from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime

app = FastAPI()

metrics_db = []

class Metric(BaseModel):
    device_id: str
    cpu: float
    memory: float
    disk: float

@app.post("/metrics")
def receive_metrics(metric: Metric):
    entry = metric.dict()
    entry["timestamp"] = datetime.utcnow().isoformat()
    metrics_db.append(entry)
    return {"status": "ok"}

@app.get("/metrics")
def get_metrics():
    return metrics_db


# 👇 NEW: dashboard page
@app.get("/", response_class=HTMLResponse)
def dashboard():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Live System Monitor</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <h2>CPU Usage (Live)</h2>
    <canvas id="cpuChart" width="800" height="400"></canvas>

    <script>
        const ctx = document.getElementById('cpuChart').getContext('2d');

        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'CPU %',
                        data: [],
                        borderWidth: 2
                    },
                    {
                        label: 'Memory %',
                        data: [],
                        borderWidth: 2
                    },
                    {
                        label: 'Disk %',
                        data: [],
                        borderWidth: 2
                    }
                ]
            },
            options: {
                animation: false,
                scales: {
                    y: {
                        min: 0,
                        max: 100
                    }
                }
            }
        });

        async function fetchData() {
            const res = await fetch('/metrics');
            const data = await res.json();

            const last = data.slice(-20); // last 20 points

            chart.data.labels = last.map(d => d.timestamp.split("T")[1].split(".")[0]);
            chart.data.datasets[0].data = last.map(d => d.cpu);
            chart.data.datasets[1].data = last.map(d => d.memory);
            chart.data.datasets[2].data = last.map(d => d.disk);

            chart.update();
        }

        setInterval(fetchData, 2000);
    </script>
</body>
</html>
"""