"""
api.py — FastAPI REST API
Reads from devices.db and exposes three endpoints for the dashboard:
  GET /devices                → unique device list
  GET /metrics/{device_name} → last 50 records for a device
  GET /overview              → total devices + average CPU

Usage:
    uvicorn api:app --reload --port 8000
"""

import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

DB_PATH = "devices.db"

app = FastAPI(title="Device Monitor API")

# Allow the frontend (any origin) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── DB helper ─────────────────────────────────────────────────────────────────

def query(sql: str, params: tuple = ()) -> list[dict]:
    """Run a SELECT and return rows as a list of dicts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # lets us access columns by name
    cursor = conn.cursor()
    cursor.execute(sql, params)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/devices")
def get_devices():
    """Return a list of all unique device names seen so far."""
    rows = query("SELECT DISTINCT device_name FROM metrics ORDER BY device_name")
    return [r["device_name"] for r in rows]


@app.get("/metrics/{device_name}")
def get_metrics(device_name: str):
    """Return the last 50 metric records for the given device."""
    rows = query(
        """
        SELECT id, device_name, ip, cpu, memory, disk, timestamp
        FROM   metrics
        WHERE  device_name = ?
        ORDER  BY id DESC
        LIMIT  50
        """,
        (device_name,)
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Device not found")
    # Return in chronological order (oldest first) for the chart
    return list(reversed(rows))


@app.get("/overview")
def get_overview():
    """Return total unique devices and overall average CPU across all devices."""
    device_count = query("SELECT COUNT(DISTINCT device_name) AS cnt FROM metrics")
    avg_cpu = query("SELECT ROUND(AVG(cpu), 2) AS avg_cpu FROM metrics")
    return {
        "total_devices": device_count[0]["cnt"],
        "avg_cpu":       avg_cpu[0]["avg_cpu"] or 0,
    }


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "Device Monitor API is running"}
