const API = "http://127.0.0.1:8000";

let cpuChart, memoryChart, diskChart;

async function loadDevices() {
    const res = await fetch(`${API}/devices`);
    const devices = await res.json();

    const select = document.getElementById("deviceSelect");
    select.innerHTML = "";

    devices.forEach(d => {
        const opt = document.createElement("option");
        opt.value = d.device_id;
        opt.text = `${d.device_name} (${d.ip})`;
        select.appendChild(opt);
    });

    if (devices.length > 0) {
        loadMetrics(devices[0].device_id);
    }
}

async function loadMetrics(id) {
    const res = await fetch(`${API}/metrics/${id}`);
    const data = await res.json();

    const labels = data.map(d => d.timestamp);
    const cpu = data.map(d => d.cpu);
    const mem = data.map(d => d.memory);
    const disk = data.map(d => d.disk);

    render("cpuChart", "CPU %", labels, cpu, c => cpuChart = c);
    render("memoryChart", "Memory %", labels, mem, c => memoryChart = c);
    render("diskChart", "Disk %", labels, disk, c => diskChart = c);
}

function render(id, label, labels, data, setChart) {
    const ctx = document.getElementById(id);

    const chart = new Chart(ctx, {
        type: "line",
        data: {
            labels,
            datasets: [{
                label,
                data,
                borderWidth: 2
            }]
        }
    });

    setChart(chart);
}

async function loadOverview() {
    const res = await fetch(`${API}/overview`);
    const d = await res.json();

    document.getElementById("overview").innerHTML = `
        Avg CPU: ${d.avg_cpu}% <br>
        Avg Memory: ${d.avg_memory}% <br>
        Avg Disk: ${d.avg_disk}%
    `;
}

document.getElementById("deviceSelect").addEventListener("change", e => {
    loadMetrics(e.target.value);
});

setInterval(() => {
    loadOverview();
    const id = document.getElementById("deviceSelect").value;
    if (id) loadMetrics(id);
}, 5000);

loadDevices();
loadOverview();