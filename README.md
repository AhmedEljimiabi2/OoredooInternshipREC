# Device Monitoring System

A real-time system that collects metrics from multiple devices and displays
them in a live web dashboard. Built with Python sockets, FastAPI, SQLite, and Chart.js.

```
┌─────────────┐        TCP/9000        ┌──────────────┐
│  agent.py   │  ──── JSON metrics ──► │  server.py   │
│  (device 1) │                        │  (saves to   │
└─────────────┘                        │  devices.db) │
┌─────────────┐        TCP/9000        │              │
│  agent.py   │  ──── JSON metrics ──► │              │
│  (device 2) │                        └──────┬───────┘
└─────────────┘                               │ reads
                                              ▼
                                       ┌──────────────┐
                                       │   api.py     │  HTTP/8000
                                       │  (FastAPI)   │ ◄──────────
                                       └──────────────┘           │
                                                         ┌────────────────┐
                                                         │  index.html    │
                                                         │  (dashboard)   │
                                                         └────────────────┘
```

---

## Project Structure

```
device_monitor/
├── server.py          ← Socket server (stores metrics in DB)
├── agent.py           ← Device client (collects & sends metrics)
├── api.py             ← FastAPI REST API (reads from DB)
├── devices.db         ← SQLite database (auto-created)
├── requirements.txt   ← Python dependencies
└── frontend/
    ├── index.html     ← Dashboard UI
    └── app.js         ← Chart.js + API calls
```

---

## Setup (one-time)

```bash
pip install -r requirements.txt
```

---

## Running the System

Open **4 separate terminal windows** (all in the `device_monitor/` folder).

### Terminal 1 — Start the Socket Server
```bash
python server.py
```
Listens on port 9000. Saves every metric to `devices.db`.

### Terminal 2 — Start the REST API
```bash
uvicorn api:app --reload --port 8000
```
Serves data on http://127.0.0.1:8000
API docs at http://127.0.0.1:8000/docs

### Terminal 3 — Run the Agent (this machine)
```bash
python agent.py
```
Collects CPU / memory / disk every 3 seconds and sends to the server.

### Terminal 4 — Run a Second Agent (simulate another device)
```bash
# On another machine on the same network:
python agent.py --host <server-ip>

# Or on the same machine (metrics will be the same but device_name differs if you rename):
python agent.py
```

### Open the Dashboard
Open `frontend/index.html` directly in your browser.
No web server needed — it calls the API at localhost:8000.

```
frontend/index.html  →  double-click or drag into browser
```

---

## API Reference

| Endpoint                  | Description                            |
|---------------------------|----------------------------------------|
| `GET /devices`            | List all unique device names           |
| `GET /metrics/{name}`     | Last 50 records for a device           |
| `GET /overview`           | Total devices + average CPU            |
| `GET /docs`               | Interactive Swagger UI                 |

---

## Notes

- The dashboard auto-refreshes every 5 seconds.
- To simulate multiple devices from one PC, open multiple terminals and run `agent.py` — each will use the same hostname, but you can edit `DEVICE_NAME` in `agent.py` to give them unique names.
- `devices.db` is created automatically when `server.py` starts.
- All code requires Python 3.10+.
