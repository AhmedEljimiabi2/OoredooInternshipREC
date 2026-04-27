const API = "http://127.0.0.1:8000";

let cpuChart, memoryChart, diskChart;

async function loadDevices() {
    const res = await fetch(`${API}/devices`);
    const devices = await res.json();

    const select = document.getElementById("deviceSelect");
    select.innerHTML = "";

    devices.forEach(d => {
        const option = document.createElement("option");
        option.value = d.id;
        option.text = d.hostname || d.id;
        select.appendChild(option);
    });

    if (devices.length > 0) {
        loadMetrics(devices[0].id);
    }
}

async function loadMetrics(deviceId) {
    const res = await fetch(`${API}/metrics/${deviceId}`);
    const data = await res.json();

    const labels = data.map(d => d.timestamp);
    const cpu = data.map(d => d.cpu);
    const memory = data.map(d => d.memory);
    const disk = data.map(d => d.disk);

    renderChart("cpuChart", "CPU", labels, cpu, cpuChart, c => cpuChart = c);
    renderChart("memoryChart", "Memory", labels, memory, memoryChart, c => memoryChart = c);
    renderChart("diskChart", "Disk", labels, disk, diskChart, c => diskChart = c);
}

function renderChart(id, label, labels, data, chart, setChart) {
    const ctx = document.getElementById(id);

    if (chart) chart.destroy();

    const newChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: data,
                borderWidth: 2
            }]
        }
    });

    setChart(newChart);
}

document.getElementById("deviceSelect").addEventListener("change", (e) => {
    loadMetrics(e.target.value);
});

async function loadOverview() {
    const res = await fetch(`${API}/overview`);
    const data = await res.json();

    document.getElementById("overview").innerHTML = `
        Devices: ${data.active_devices} <br>
        Avg CPU: ${data.avg_cpu}%
    `;
}

setInterval(() => {
    const id = document.getElementById("deviceSelect").value;
    if (id) loadMetrics(id);
    loadOverview();
}, 5000);

loadDevices();
loadOverview();