/**
 * build-wall-dash.js — wall-dashboard.html from real IoT Admin Console data
 * Only uses data actually scraped: location counts, platform types, offline devices
 */
const fs = require('fs');

const DATA_FILE = '/tmp/rmstatus-light/iot-admin-data.json';
const OUTPUT = '/tmp/rmstatus-light/wall-dashboard.html';

if (!fs.existsSync(DATA_FILE)) {
  console.error(`Data file not found: ${DATA_FILE}`);
  process.exit(1);
}

const data = JSON.parse(fs.readFileSync(DATA_FILE, 'utf-8'));

const now = new Date();
const dateStr = now.toLocaleDateString('en-GB');
const timeStr = now.toLocaleTimeString('en-GB');

function esc(s) { return s ? String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') : ''; }

const locations = data.locations || [];
const rawDevices = data.attentionDevices || [];

let sumLocations = 0, totalJ3011 = 0, totalJNX30 = 0, totalJNX42 = 0;
for (const loc of locations) {
  sumLocations += loc.total || 0;
  totalJ3011 += loc.j3011 || 0;
  totalJNX30 += loc.jnx30 || 0;
  totalJNX42 += loc.jnx42 || 0;
}

// Use real counts from Devices page (more accurate than locations sum)
const totalDeviceCount = (data.deviceCounts && data.deviceCounts.total) || sumLocations;
const trueOffline = (data.deviceCounts && data.deviceCounts.offline) || rawDevices.length;
const totalOffline = trueOffline;
const totalOnline = totalDeviceCount - totalOffline;

// State breakdown — use real data from API
const sb = data.stateBreakdown || {};
const stateReady = sb.ready || 0;
const stateTracking = sb.tracking || 0;
const stateIdle = sb.idle || 0;
const stateUnknown = sb.unknown || 0;

// Build MAC→venue lookup from real scrape data
const macToVenue = {};
if (data.offlineByVenue) {
  for (const [venue, devs] of Object.entries(data.offlineByVenue)) {
    for (const d of devs) {
      if (d.device) macToVenue[d.device] = venue;
    }
  }
}

const offlineRows = rawDevices.map(d => {
  const venue = macToVenue[d.device] || '—';
  return `<tr>
    <td><span class="mac">${esc(d.device)}</span></td>
    <td>${esc(venue)}</td>
    <td><span class="st of">OFFLINE</span></td>
    <td class="age">${esc(d.lastSeen)}</td>
    <td class="cmds">${d.cmds && d.cmds !== '0' ? `<span class="err">${esc(d.cmds)}</span>` : '0'}</td>
  </tr>`;
}).join('');

// Platform donut (real data)
function donutSvg(segments, cx=120, cy=120, r=90, ir=55) {
  const total = segments.reduce((s, s2) => s + s2.value, 0);
  if (total === 0) return `<svg viewBox="0 0 240 240" style="width:100%;height:100%"><text x="120" y="120" text-anchor="middle" fill="#52525b" font-size="14">No data</text></svg>`;
  let offset = 0;
  const circ = 2 * Math.PI * r;
  let slices = '';
  segments.forEach(s => {
    const len = (s.value / total) * circ;
    slices += `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${s.color}" stroke-width="${r - ir}" stroke-dasharray="${len} ${circ - len}" stroke-dashoffset="${offset}" transform="rotate(-90 ${cx} ${cy})"/>`;
    offset -= len;
  });
  const platformSum = totalJ3011 + totalJNX30 + totalJNX42;
  const unassigned = totalDeviceCount - platformSum;
  if (unassigned > 0) {
    const ulen = (unassigned / totalDeviceCount) * circ;
    slices += `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="#27272a" stroke-width="${r - ir}" stroke-dasharray="${ulen} ${circ - ulen}" stroke-dashoffset="${offset}" transform="rotate(-90 ${cx} ${cy})"/>`;
  }
  return `<svg viewBox="0 0 240 240" style="width:100%;height:100%">${slices}<text x="${cx}" y="${cy - 8}" text-anchor="middle" fill="#e2e8f0" font-size="28" font-weight="800">${totalDeviceCount}</text><text x="${cx}" y="${cy + 14}" text-anchor="middle" fill="#64748b" font-size="11">devices</text></svg>`;
}

function legend(data) {
  const total = data.reduce((a, b) => a + b.value, 0);
  return data.map(d => {
    const pct = total > 0 ? ((d.value / total) * 100).toFixed(1) : '0.0';
    return `<div class="leg-item"><div class="leg-dot" style="background:${d.color}"></div><span class="leg-label">${d.label}</span><span class="leg-val">${d.value}<span class="leg-pct">${pct}%</span></span></div>`;
  }).join('');
}

const platformData = [
  { label: 'J3011', value: totalJ3011, color: '#06b6d4' },
  { label: 'JNX30', value: totalJNX30, color: '#22c55e' },
  { label: 'JNX42', value: totalJNX42, color: '#3b82f6' },
];

const platformTotal = totalJ3011 + totalJNX30 + totalJNX42;
if (totalDeviceCount - platformTotal > 0) {
  platformData.push({ label: 'Other', value: totalDeviceCount - platformTotal, color: '#27272a' });
}

// State donut data
const stateData = [
  { label: 'Tracking', value: stateTracking, color: '#3b82f6' },
  { label: 'Ready', value: stateReady, color: '#22c55e' },
  { label: 'Idle', value: stateIdle, color: '#facc15' },
  { label: 'Offline', value: totalOffline, color: '#ef4444' },
  { label: 'Unknown', value: stateUnknown, color: '#52525b' },
];

// Camera type data
const cameraBreakdown = data.cameraBreakdown || {};
const camColors = { 'ZED_2I': '#06b6d4', 'ZED': '#22c55e', 'ZED_2': '#0891b2', 'RTSP': '#3b82f6', 'MULTIPLE_RTSP': '#6366f1', 'USB': '#f59e0b', 'MULTIPLE_ZED': '#14b8a6', 'MULTIPLE_USB': '#8b5cf6', 'Unknown': '#52525b' };
const cameraData = Object.entries(cameraBreakdown).sort((a, b) => b[1] - a[1]).map(([key, val]) => ({
  label: key.replace(/_/g, ' '),
  value: val,
  color: camColors[key] || '#52525b',
}));





const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<meta http-equiv="refresh" content="300">
<title>IOT Dashboard — Wall Display</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:Inter,-apple-system,BlinkMacSystemFont,sans-serif;background:#0d1117;color:#e2e8f0;min-height:100vh;padding:0}

.hdr{padding:16px 24px;border-bottom:1px solid #1e293b;display:flex;align-items:center;justify-content:space-between}
.hdr h1{font-size:18px;font-weight:600;color:#e2e8f0}
.hdr .ts{color:#52525b;font-size:11px;font-family:monospace}

.summary{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;padding:16px 24px}
.sc{background:#161b22;border-radius:10px;border:1px solid #1e293b;padding:14px 16px;text-align:center}
.sc .sv{font-size:32px;font-weight:800;line-height:1.2}
.sc .sl{font-size:11px;color:#64748b;margin-top:4px;text-transform:uppercase;letter-spacing:.5px}
.sc.b .sv{color:#60a5fa}.sc.g .sv{color:#4ade80}.sc.r .sv{color:#f87171}.sc.p .sv{color:#a78bfa}

.grid{display:grid;grid-template-columns:2fr 1fr 1fr;gap:16px;padding:0 24px}

.chart-card{background:#161b22;border-radius:12px;border:1px solid #1e293b;overflow:hidden}
.chart-card .ch{display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid #1e293b}
.chart-card .ch h3{font-size:12px;font-weight:600;color:#e2e8f0}
.chart-card .ch .ch-sub{font-size:10px;color:#64748b}
.chart-body{padding:16px}

.chart-wrap{display:flex;align-items:center;gap:24px;justify-content:center}
.chart-svg{width:160px;height:160px;flex-shrink:0}
.legend{display:flex;flex-direction:column;gap:8px;min-width:90px}
.leg-item{display:flex;align-items:center;gap:8px;font-size:12px}
.leg-dot{width:10px;height:10px;border-radius:3px;flex-shrink:0}
.leg-label{color:#94a3b8;flex:1}
.leg-val{font-weight:700;font-size:14px;color:#e2e8f0}
.leg-pct{font-size:9px;color:#52525b;margin-left:3px}

/* Category bars */
.cat-list{display:flex;flex-direction:column;gap:8px}
/* Category bars */
.cat-list{display:flex;flex-direction:column;gap:8px}
.cc-row{display:flex;align-items:center;gap:10px;font-size:12px}
.cc-name{display:flex;align-items:center;gap:5px;min-width:120px;color:#94a3b8}
.cc-dot{width:8px;height:8px;border-radius:2px;flex-shrink:0}
.cc-val{font-weight:700;color:#e2e8f0;min-width:30px;text-align:right}
.cc-bar{flex:1;height:8px;background:#1e293b;border-radius:4px;overflow:hidden}
.cc-fill{height:100%;border-radius:4px;transition:width .5s}


/* Offline table */
.table-wrap{padding:16px 24px 24px}
.tc{background:#161b22;border-radius:12px;border:1px solid #1e293b;overflow:hidden}
.thdr{padding:14px 18px;font-size:13px;font-weight:600;color:#fca5a5;border-bottom:1px solid #1e293b;display:flex;align-items:center;justify-content:space-between}
.thdr .sub{color:#64748b;font-size:11px;font-weight:400}
table{width:100%;border-collapse:collapse;font-size:12px}
th{padding:10px 16px;color:#64748b;font-size:9px;text-transform:uppercase;letter-spacing:.5px;text-align:left;font-weight:600;border-bottom:1px solid #1e293b;background:#0f172a}
td{padding:10px 16px;border-bottom:1px solid #1e293b}
tr:last-child td{border-bottom:none}
tr:hover{background:#1c2333}
.mac{font-family:'SF Mono',Consolas,monospace;color:#60a5fa;font-size:12px;font-weight:500}
.st{font-size:9px;padding:2px 8px;border-radius:4px;font-weight:600;display:inline-block}
.st.of{background:#450a0a;color:#f87171;border:1px solid #7f1d1d}
.age{color:#64748b;font-size:11px}
.cmds{font-size:11px;color:#64748b}
.cmds .err{color:#f87171;font-weight:700}

.ft{text-align:center;padding:18px;color:#1e293b;font-size:9px}

@media(max-width:1000px){
  .grid{grid-template-columns:1fr;padding:0 12px}
  .summary{grid-template-columns:repeat(2,1fr);padding:12px}
  .table-wrap{padding:12px}
}
@media(min-width:1800px){
  .chart-svg{width:200px;height:200px}
  .grid{padding:0 32px;gap:20px}
  .summary{padding:16px 32px}
  .table-wrap{padding:16px 32px 24px}
}
</style>
</head>
<body>

<div class="hdr">
  <h1>IOT Dashboard — AiOO Tech</h1>
  <div class="ts">${esc(dateStr)} ${esc(timeStr)}</div>
</div>

<div class="summary">
  <div class="sc b"><div class="sv">${totalDeviceCount}</div><div class="sl">Total devices</div></div>
  <div class="sc g"><div class="sv">${totalOnline}</div><div class="sl">Online</div></div>
  <div class="sc r"><div class="sv">${totalOffline}</div><div class="sl">Offline</div></div>
  <div class="sc p"><div class="sv">${locations.length}</div><div class="sl">Venues</div></div>
</div>

<div class="grid">
  <div class="chart-card">
    <div class="ch"><h3>Device by state</h3><span class="ch-sub">${totalDeviceCount} total</span></div>
    <div class="chart-body">
      <div class="chart-wrap">
        <div class="chart-svg">${donutSvg(stateData)}</div>
        <div class="legend">${legend(stateData)}</div>
      </div>
    </div>
  </div>
  <div class="chart-card">
    <div class="ch"><h3>All devices by platform</h3><span class="ch-sub">${totalJ3011} J3011 · ${totalJNX30} JNX30 · ${totalJNX42} JNX42</span></div>
    <div class="chart-body">
      <div class="chart-wrap">
        <div class="chart-svg">${donutSvg(platformData)}</div>
        <div class="legend">${legend(platformData)}</div>
      </div>
    </div>
  </div>
  <div class="chart-card">
    <div class="ch"><h3>Device by camera type</h3><span class="ch-sub">${totalDeviceCount} devices</span></div>
    <div class="chart-body">
      <div class="chart-wrap">
        <div class="chart-svg">${donutSvg(cameraData)}</div>
        <div class="legend">${legend(cameraData)}</div>
      </div>
    </div>
  </div>
</div>

${totalOffline > 0 ? `
<div class="table-wrap">
  <div class="tc">
    <div class="thdr">⚠ Devices needing attention <span class="sub">${rawDevices.length} device${rawDevices.length !== 1 ? 's' : ''}</span></div>
    <table>
      <tr><th>Device</th><th>Venue</th><th>State</th><th>Last seen</th><th>Cmds</th></tr>
      ${offlineRows}
    </table>
  </div>
</div>` : ''}

<div class="ft">IOT Admin Console · AiOO Tech Dubai © · Live data · ${esc(dateStr)} ${esc(timeStr)}</div>
</body>
</html>`;

fs.writeFileSync(OUTPUT, html);
console.log(`OK - ${(Buffer.byteLength(html) / 1024).toFixed(0)} KB — ${totalDeviceCount} devices, ${totalOffline} offline, ${locations.length} venues`);
