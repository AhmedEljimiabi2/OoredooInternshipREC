from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB = "devices.db"

def query(sql, params=()):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return rows

# ---------------- DEVICES ----------------

@app.get("/devices")
def devices():
    rows = query("""
        SELECT DISTINCT device_id, device_name, ip
        FROM device_data
    """)

    return [
        {"device_id": r[0], "device_name": r[1], "ip": r[2]}
        for r in rows
    ]

# ---------------- METRICS ----------------

@app.get("/metrics/{device_id}")
def metrics(device_id: str):
    rows = query("""
        SELECT timestamp, cpu, memory, disk
        FROM device_data
        WHERE device_id=?
        ORDER BY timestamp ASC
        LIMIT 300
    """, (device_id,))

    return [
        {
            "timestamp": r[0],
            "cpu": r[1],
            "memory": r[2],
            "disk": r[3]
        }
        for r in rows
    ]

# ---------------- OVERVIEW ----------------

@app.get("/overview")
def overview():
    rows = query("SELECT AVG(cpu), AVG(memory), AVG(disk) FROM device_data")
    cpu, mem, disk = rows[0]

    return {
        "avg_cpu": round(cpu or 0, 2),
        "avg_memory": round(mem or 0, 2),
        "avg_disk": round(disk or 0, 2)
    }