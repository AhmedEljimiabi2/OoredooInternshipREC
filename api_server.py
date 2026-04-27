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

DB_NAME = "devices.db"

def query_db(query, params=()):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows

# ------------------ ROUTES ------------------

@app.get("/devices")
def get_devices():
    rows = query_db("""
        SELECT DISTINCT device_name, ip
        FROM device_data
    """)

    return [
        {"device_name": r[0], "ip": r[1]}
        for r in rows
    ]


@app.get("/metrics/{device_name}")
def get_metrics(device_name: str):
    rows = query_db("""
        SELECT timestamp, cpu, memory, disk
        FROM device_data
        WHERE device_name=?
        ORDER BY timestamp ASC
        LIMIT 200
    """, (device_name,))

    return [
        {
            "timestamp": r[0],
            "cpu": r[1],
            "memory": r[2],
            "disk": r[3]
        }
        for r in rows
    ]


@app.get("/overview")
def overview():
    devices = query_db("SELECT COUNT(DISTINCT device_name) FROM device_data")[0][0]
    avg_cpu = query_db("SELECT AVG(cpu) FROM device_data")[0][0] or 0

    return {
        "active_devices": devices,
        "avg_cpu": round(avg_cpu, 2)
    }