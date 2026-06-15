const fs = require('fs');

const dateStr = new Date().toLocaleDateString('en-GB');
const timeStr = new Date().toLocaleTimeString('en-GB');

const devices = [
  { venue: 'Malls - WAFi Mall', asset: 'FF - West escalator', device: '48:b0:2d:eb:17:d9', last: '1d 15h 29m ago.' },
  { venue: 'Malls - WAFi Mall', asset: 'FF - West escalator', device: '48:b0:2d:eb:16:ff', last: '1d 15h 29m ago.' },
  { venue: 'Malls - Mushrif Mall', asset: 'Screen 3(B) GF MUS-GF-MPI-1A', device: '48:b0:2d:eb:16:ef', last: '12h 26m ago.' },
  { venue: 'Malls - Deerfield Mall', asset: 'Screen 6(A) Garden floor', device: '48:b0:2d:eb:36:45', last: '4h 36m ago.' },
  { venue: 'Malls - Deerfield Mall', asset: 'Screen 4(A) Tafaseel Main level', device: '48:b0:2d:eb:17:11', last: '4h 36m ago.' },
  { venue: 'Malls - Deerfield Mall', asset: 'Screen 6(B) Garden floor', device: '48:b0:2d:eb:16:3d', last: '4h 36m ago.' },
  { venue: 'Malls - Deerfield Mall', asset: 'Screen 1(A) Good feet Main level', device: '48:b0:2d:ea:56:d2', last: '6h 25m ago.' },
];

const rows = devices.map(d => `<tr>
  <td><div class="ven">${d.venue}</div><div class="asst">${d.asset}</div></td>
  <td class="mac">${d.device}</td>
  <td><span class="st of">OFFLINE</span></td>
  <td class="age">${d.last}</td>
</tr>`).join('\n');

function donutSvg(segments, cx=120, cy=120, r=90, ir=55) {
  const total = segments.reduce((s, s2) => s + s2.value, 0);
  let offset = 0;
  const circ = 2 * Math.PI * r;
  let slices = '';
  let labels = '';
  segments.forEach((s, i) => {
    const len = (s.value / total) * circ;
    const dash = len + ' ' + (circ - len);
    const off = offset;
    offset -= len;
    // Slice
    slices += `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${s.color}" stroke-width="${r - ir}" stroke-dasharray="${dash}" stroke-dashoffset="${off}" transform="rotate(-90 ${cx} ${cy})" style="transition:stroke-dashoffset .5s"/>`;
    // Center label
    if (i === 0) {
      labels += `<text x="${cx}" y="${cy - 8}" text-anchor="middle" fill="#e2e8f0" font-size="28" font-weight="800">${total}</text><text x="${cx}" y="${cy + 14}" text-anchor="middle" fill="#64748b" font-size="11">total</text>`;
    }
  });
  return `<svg viewBox="0 0 240 240" style="width:100%;height:100%">${slices}${labels}</svg>`;
}

const platformData = [
  { label: 'J30', value: 308, color: '#06b6d4' },
  { label: 'JNX30', value: 45, color: '#22c55e' },
  { label: 'JNX42', value: 191, color: '#3b82f6' },
];
const stateData = [
  { label: 'TRACKING', value: 412, color: '#06b6d4' },
  { label: 'READY', value: 89, color: '#22c55e' },
  { label: 'IDLE', value: 27, color: '#facc15' },
  { label: 'Offline', value: 16, color: '#ef4444' },
];

const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>IOT Dashboard</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:Inter,-apple-system,BlinkMacSystemFont,sans-serif;background:#0d1117;color:#e2e8f0;min-height:100vh;padding:0}

.hdr{padding:16px 24px;border-bottom:1px solid #1e293b;display:flex;align-items:center;justify-content:space-between}
.hdr h1{font-size:18px;font-weight:600;color:#e2e8f0}
.hdr .aioo{display:flex;align-items:center;gap:6px;color:#64748b;font-size:12px;font-weight:600}
.hdr .aioo img{height:20px;border-radius:3px}

.alert{background:linear-gradient(90deg,#1e293b,#0f172a);padding:10px 24px;border-bottom:1px solid #1e293b;font-size:13px;color:#facc15;font-weight:600;display:flex;align-items:center;gap:8px}
.alert::before{content:'⚠';font-size:16px}

/* 3 charts side by side for 1080p */
.grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;padding:16px 24px}
.chart-card{background:#161b22;border-radius:12px;border:1px solid #1e293b;padding:20px 16px 16px}
.chart-card h3{font-size:11px;font-weight:600;color:#64748b;margin-bottom:12px;text-transform:uppercase;letter-spacing:1px}
.chart-wrap{display:flex;align-items:center;gap:24px;justify-content:center}
.chart-svg{width:180px;height:180px;flex-shrink:0}
.legend{display:flex;flex-direction:column;gap:10px;min-width:100px}
.leg-item{display:flex;align-items:center;gap:8px;font-size:13px}
.leg-dot{width:12px;height:12px;border-radius:3px;flex-shrink:0}
.leg-label{color:#94a3b8;flex:1}
.leg-val{font-weight:700;font-size:15px;color:#e2e8f0}
.leg-pct{font-size:10px;color:#52525b;margin-left:4px}

/* Table full width */
.table-section{padding:0 24px}
.table-card{background:#161b22;border-radius:12px;border:1px solid #1e293b;overflow:hidden}
.thdr{padding:14px 18px;font-size:14px;font-weight:600;color:#fca5a5;border-bottom:1px solid #1e293b;display:flex;align-items:center;gap:8px}
.thdr::before{content:'⚠';font-size:16px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{padding:10px 16px;color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:.5px;text-align:left;font-weight:600;border-bottom:1px solid #1e293b;background:#0f172a}
td{padding:10px 16px;border-bottom:1px solid #1e293b;vertical-align:middle}
tr:last-child td{border-bottom:none}
tr:hover{background:#1c2333}
.ven{font-weight:500;color:#e2e8f0;font-size:13px}
.asst{color:#64748b;font-size:12px;margin-top:2px}
.mac{font-family:'SF Mono',Consolas,monospace;color:#94a3b8;font-size:12px}
.st{font-size:10px;padding:2px 10px;border-radius:4px;font-weight:600;display:inline-block}
.st.of{background:#450a0a;color:#f87171;border:1px solid #7f1d1d}
.age{color:#64748b;font-size:12px}

.pagination{padding:12px 18px;display:flex;align-items:center;justify-content:space-between;border-top:1px solid #1e293b;color:#64748b;font-size:12px}
.pagination .btns{display:flex;gap:4px}
.pagination .btns button{background:#1e293b;border:1px solid #334155;border-radius:4px;padding:4px 10px;cursor:pointer;color:#94a3b8;font-size:12px}
.pagination .btns button:disabled{opacity:.4;cursor:default}

.ft{text-align:center;padding:20px;color:#1e293b;font-size:10px}

/* 1080p optimization */
@media(min-width:1800px){
  .chart-svg{width:220px;height:220px}
  .grid{padding:20px 32px;gap:20px}
  .table-section{padding:0 32px}
}
@media(max-width:900px){
  .grid{grid-template-columns:1fr;padding:12px}
  .chart-svg{width:160px;height:160px}
  .chart-wrap{gap:16px}
  .table-section{padding:0 12px}
}
</style>
</head>
<body>

<div class="hdr">
  <h1>IOT Dashboard</h1>
  <div class="aioo"><img src="aioo-logo.jpg" alt="">AiOO Tech Dubai</div>
</div>

<div class="alert">14 devices are currently in need of attention.</div>

<div class="grid">
  <div class="chart-card">
    <h3>Devices by platform</h3>
    <div class="chart-wrap">
      <div class="chart-svg">${donutSvg(platformData)}</div>
      <div class="legend">
        ${(s => platformData.map(d => {
          const pct = ((d.value / s) * 100).toFixed(1);
          return `<div class="leg-item"><div class="leg-dot" style="background:${d.color}"></div><span class="leg-label">${d.label}</span><span class="leg-val">${d.value}<span class="leg-pct">${pct}%</span></span></div>`;
        }).join(''))(platformData.reduce((a, b) => a + b.value, 0))}
      </div>
    </div>
  </div>
  <div class="chart-card">
    <h3>Devices by state</h3>
    <div class="chart-wrap">
      <div class="chart-svg">${donutSvg(stateData)}</div>
      <div class="legend">
        ${(s => stateData.map(d => {
          const pct = ((d.value / s) * 100).toFixed(1);
          return `<div class="leg-item"><div class="leg-dot" style="background:${d.color}"></div><span class="leg-label">${d.label}</span><span class="leg-val">${d.value}<span class="leg-pct">${pct}%</span></span></div>`;
        }).join(''))(stateData.reduce((a, b) => a + b.value, 0))}
      </div>
    </div>
  </div>
  <div class="chart-card">
    <h3>Device by location</h3>
    <div class="chart-wrap" style="flex-direction:column;align-items:stretch;gap:10px">
      <div class="leg-item"><div class="leg-dot" style="background:#06b6d4"></div><span class="leg-label">Union Coop Umm Suqeim</span><span class="leg-val">27</span></div>
      <div class="leg-item"><div class="leg-dot" style="background:#22c55e"></div><span class="leg-label">Union Coop Al Warqa</span><span class="leg-val">33</span></div>
      <div class="leg-item"><div class="leg-dot" style="background:#3b82f6"></div><span class="leg-label">Lulu Al Wahda</span><span class="leg-val">37</span></div>
      <div class="leg-item"><div class="leg-dot" style="background:#facc15"></div><span class="leg-label">Carrefour</span><span class="leg-val">—</span></div>
      <div class="leg-item"><div class="leg-dot" style="background:#52525b"></div><span class="leg-label">Other venues</span><span class="leg-val">447</span></div>
    </div>
  </div>
</div>

<div class="table-section">
  <div class="table-card">
    <div class="thdr">Devices that may need attention</div>
    <table>
      <tr><th>Venue / Asset</th><th>Device</th><th>State</th><th>Last seen</th></tr>
      ${rows}
    </table>
    <div class="pagination">
      <span>Items per page: 7</span>
      <span>1 – 7 of 14</span>
      <div class="btns">
        <button disabled>‹</button>
        <button disabled>‹‹</button>
        <button>›</button>
        <button>››</button>
      </div>
    </div>
  </div>
</div>

<div class="ft">IOT Admin Console (v4.1) · AiOO Tech Dubai © · ${dateStr} ${timeStr}</div>
</body>
</html>`;

fs.writeFileSync('/tmp/rmstatus-light/wall-dashboard.html', html);
console.log('OK - ' + (Buffer.byteLength(html) / 1024).toFixed(0) + ' KB');
