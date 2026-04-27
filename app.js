/* app.js — Dashboard Logic
   - Fetches the device list and populates the dropdown
   - Draws/updates Chart.js line charts for CPU, Memory, Disk
   - Shows an overview card (device count + avg CPU)
   - Auto-refreshes everything every 5 seconds
*/

const API = "http://127.0.0.1:8000";

let cpuChart, memChart, diskChart;

// ── Chart factory ────────────────────────────────────────────────────────────

function makeChart(canvasId, label, color) {
  const ctx = document.getElementById(canvasId).getContext("2d");
  return new Chart(ctx, {
    type: "line",
    data: {
      labels: [],
      datasets: [{
        label,
        data: [],
        borderColor: color,
        backgroundColor: color + "22",
        borderWidth: 2.5,
        pointRadius: 3,
        pointHoverRadius: 5,
        tension: 0.35,
        fill: true,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 400 },
      scales: {
        y: {
          min: 0, max: 100,
          ticks: { callback: v => v + "%" },
          grid: { color: "#ffffff15" },
        },
        x: {
          ticks: {
            maxRotation: 30,
            color: "#aaa",
            font: { size: 10 },
          },
          grid: { color: "#ffffff10" },
        }
      },
      plugins: {
        legend: { labels: { color: "#ddd", font: { size: 12 } } },
        tooltip: {
          callbacks: { label: ctx => ` ${ctx.parsed.y.toFixed(1)}%` }
        }
      }
    }
  });
}

// ── Bootstrap ────────────────────────────────────────────────────────────────

function initCharts() {
  cpuChart  = makeChart("cpuChart",  "CPU Usage",    "#f97316");
  memChart  = makeChart("memChart",  "Memory Usage", "#3b82f6");
  diskChart = makeChart("diskChart", "Disk Usage",   "#22c55e");
}

// ── Populate device dropdown ─────────────────────────────────────────────────

async function loadDevices() {
  try {
    const res = await fetch(`${API}/devices`);
    const devices = await res.json();
    const select = document.getElementById("deviceSelect");

    // Keep current selection if possible
    const current = select.value;
    select.innerHTML = devices.length
      ? devices.map(d => `<option value="${d}">${d}</option>`).join("")
      : `<option value="">— No devices yet —</option>`;

    if (current && devices.includes(current)) select.value = current;
  } catch {
    console.error("Could not reach the API.");
  }
}

// ── Update charts for selected device ────────────────────────────────────────

function shortTime(iso) {
  // "2024-05-01T14:23:45.123456" → "14:23:45"
  return iso.substring(11, 19);
}

function updateChart(chart, rows, field) {
  chart.data.labels   = rows.map(r => shortTime(r.timestamp));
  chart.data.datasets[0].data = rows.map(r => r[field]);
  chart.update();
}

async function loadMetrics() {
  const device = document.getElementById("deviceSelect").value;
  if (!device) return;

  try {
    const res  = await fetch(`${API}/metrics/${encodeURIComponent(device)}`);
    if (!res.ok) return;
    const rows = await res.json();

    updateChart(cpuChart,  rows, "cpu");
    updateChart(memChart,  rows, "memory");
    updateChart(diskChart, rows, "disk");

    // Show last-known values in stat badges
    if (rows.length) {
      const last = rows[rows.length - 1];
      document.getElementById("statCpu").textContent  = last.cpu.toFixed(1) + "%";
      document.getElementById("statMem").textContent  = last.memory.toFixed(1) + "%";
      document.getElementById("statDisk").textContent = last.disk.toFixed(1) + "%";
      document.getElementById("statIp").textContent   = last.ip;
    }
  } catch (e) {
    console.error("Metrics fetch failed:", e);
  }
}

// ── Overview card ─────────────────────────────────────────────────────────────

async function loadOverview() {
  try {
    const res  = await fetch(`${API}/overview`);
    const data = await res.json();
    document.getElementById("overviewDevices").textContent = data.total_devices;
    document.getElementById("overviewCpu").textContent     = data.avg_cpu.toFixed(1) + "%";
  } catch {
    /* silently ignore if API is temporarily down */
  }
}

// ── Refresh cycle ─────────────────────────────────────────────────────────────

async function refresh() {
  await loadDevices();
  await loadMetrics();
  await loadOverview();
}

// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  initCharts();
  refresh();                              // first load immediately
  setInterval(refresh, 5000);            // then every 5 s

  document.getElementById("deviceSelect")
    .addEventListener("change", loadMetrics);
});
