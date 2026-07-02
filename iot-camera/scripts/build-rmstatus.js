/**
 * build-rmstatus.js — retailmedia.html exact original design from commit 3f9cf7f
 * Union Coop + Lulu only, live data from IoT Admin Console
 */
const fs = require('fs');

const DATA_FILE = '/tmp/rmstatus-light/iot-admin-data.json';
const OUTPUT = '/tmp/rmstatus-light/rmstatus.html';

if (!fs.existsSync(DATA_FILE)) {
  console.error(`Data file not found: ${DATA_FILE}`);
  process.exit(1);
}
const data = JSON.parse(fs.readFileSync(DATA_FILE, 'utf-8'));

const now = new Date();
const pad2 = n => String(n).padStart(2, '0');
const dateStr = `${pad2(now.getDate())}/${pad2(now.getMonth()+1)}/${now.getFullYear()}, ${pad2(now.getHours())}:${pad2(now.getMinutes())}:${pad2(now.getSeconds())}`;

function esc(s) { return s ? String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') : ''; }

// Location lookup
const locMap = {};
for (const loc of data.locations || []) locMap[loc.venue.toLowerCase()] = loc;
function getV(name, matches) {
  for (const m of matches) {
    const f = locMap[m.toLowerCase()];
    if (f) return f;
  }
  return { venue: name, total: 0, j3011: 0, jnx30: 0, jnx42: 0 };
}
const u = getV('Umm Suqeim', ['in-store - union coop umm suqeim', 'union coop umm suqeim', 'umm suqeim']);
const a = getV('Al Warqa', ['union coop al warqa', 'al warqa']);
const l = getV('Lulu Al Wahda', ['lulu al wahda']);

const VENUES = [
  { name: 'Al Warqa', parent: 'Union Coop', totalDevices: a.total || 0, trackingDevices: 0, warningDevices: 0, errorDevices: 0 },
  { name: 'Umm Suqeim', parent: 'Union Coop', totalDevices: u.total || 0, trackingDevices: 0, warningDevices: 0, errorDevices: 0 },
  { name: 'Lulu Al Wahda', parent: 'Lulu Market', totalDevices: l.total || 0, trackingDevices: 0, warningDevices: 0, errorDevices: 0 },
];

// Build mapping from location venue names to VENUES names
const locToVenue = {};
const VENUE_PATTERNS = { 'Al Warqa': /al warqa/i, 'Umm Suqeim': /umm suqeim|um suqeim/i, 'Lulu Al Wahda': /lulu al wahda|lulu/i };
for (const loc of data.locations) {
  for (const [vname, pat] of Object.entries(VENUE_PATTERNS)) {
    if (pat.test(loc.venue)) {
      locToVenue[loc.venue] = vname;
      break;
    }
  }
}

// Count offline devices per venue from real scrape data
const venueOffline = {};
for (const [fullVenue, devs] of Object.entries(data.offlineByVenue || {})) {
  for (const loc of data.locations) {
    if (fullVenue.startsWith(loc.venue)) {
      const key = locToVenue[loc.venue] || loc.venue;
      venueOffline[key] = (venueOffline[key] || 0) + devs.length;
      break;
    }
  }
}

// Attention devices (complete list, not filtered)
const attention = data.attentionDevices || [];

// Mark errors per venue from offline data
let totalErrors = 0;
for (const v of VENUES) {
  v.errorDevices = venueOffline[v.name] || 0;
  totalErrors += v.errorDevices;
}

// Tracking = total - errors
let totalDevices = 0, totalTracking = 0, totalWarnings = 0;
for (const v of VENUES) {
  v.trackingDevices = v.totalDevices - v.errorDevices;
  totalDevices += v.totalDevices;
  totalTracking += v.trackingDevices;
  totalWarnings += v.warningDevices;
}

// Build brand columns
const BRANDS = {
  'Union Coop': { cls: 'uc', venues: VENUES.filter(v => v.parent === 'Union Coop') },
  'Lulu Market': { cls: 'lm', venues: VENUES.filter(v => v.parent === 'Lulu Market') },
};

let brandCols = '';
for (const [brand, b] of Object.entries(BRANDS)) {
  let brandTotal = 0, brandTrack = 0, brandWarn = 0, brandErr = 0;
  let subVenues = '';
  for (const v of b.venues) {
    brandTotal += v.totalDevices;
    brandTrack += v.trackingDevices;
    brandWarn += v.warningDevices;
    brandErr += v.errorDevices;

    const err = v.errorDevices > 0;
    const warn = v.warningDevices > 0;
    let svCls = 'gr';
    if (err) svCls = 're';
    else if (warn) svCls = 'ye';

    let tCls = 'gr', wCls = 'gr', eCls = 'gr';
    if (err) eCls = 're';
    if (warn) wCls = 'ye';

    subVenues += `      <div class="sv ${svCls}">
        <div class="svh"><span class="sn">${esc(v.name)} <span class="loc">${esc(v.parent)}</span></span><span class="sc">${v.totalDevices}</span></div>
        <div class="sg">
          <div class="si"><div class="il">Tracking</div><div class="iv ${tCls}">${v.trackingDevices}</div></div>
          <div class="si"><div class="il">Warnings</div><div class="iv ${wCls}">${v.warningDevices}</div></div>
          <div class="si"><div class="il">Errors</div><div class="iv ${eCls}">${v.errorDevices}</div></div>
        </div>
      </div>`;
  }

  brandCols += `  <div class="bc">
    <div class="bh"><div class="bl ${b.cls}">${brand === 'Union Coop' ? 'U' : 'L'}</div><h2>${esc(brand)}</h2><div class="bs"><b>${brandTotal}</b> devices · <b class="gr">${brandTrack}</b> ok</div></div>
    <div class="bb">
${subVenues}
    </div>
  </div>`;
}

// Build MAC→venue lookup from offlineByVenue
const macToVenue = {};
if (data.offlineByVenue) {
  for (const [venue, devs] of Object.entries(data.offlineByVenue)) {
    for (const d of devs) {
      if (d.device) macToVenue[d.device] = venue;
    }
  }
}

// Attention table — filter to only retail media venues (Union Coop + Lulu)
const retaiFiltered = attention.filter(d => {
  const full = macToVenue[d.device] || '';
  return /union coop|lulu/i.test(full);
});
const attTotal = retaiFiltered.length;

function getVenueName(mac) {
  const full = macToVenue[mac];
  if (!full) return '—';
  // Match full venue name to VENUES simplified name
  for (const v of VENUES) {
    const pat = VENUE_PATTERNS[v.name];
    if (pat && pat.test(full)) return v.name;
  }
  // Fallback: show clean abbreviated name
  return full.split(/\s{2,}| IOT_| In Store/)[0].trim().replace(/^In-Store - /,'').replace(/^Outdoor - /,'');
}

function getParent(mac) {
  const vn = getVenueName(mac);
  const v = VENUES.find(x => x.name === vn);
  return v ? v.parent : '';
}

const attRows = attTotal > 0 ? retaiFiltered.map(d => {
  const vn = getVenueName(d.device);
  return `    <tr>
      <td><div style="font-weight:500;color:#e2e8f0;font-size:clamp(9px,0.7vw,11px)">${esc(vn)}</div></td>
      <td style="font-family:'SF Mono',Consolas,monospace;color:#94a3b8;font-size:clamp(8px,0.65vw,10px)">${esc(d.device)}</td>
      <td><span class="st" style="color:#f87171">Offline</span></td>
      <td style="color:#64748b">${esc(d.lastSeen)}</td>
    </tr>`;
}).join('\n') : '';

const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Retail Media · IoT Status</title>
<meta http-equiv="refresh" content="300">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{height:100%;overflow:hidden}
body{font-family:'Inter',-apple-system,sans-serif;background:#08080e;color:#f1f5f9;display:flex;flex-direction:column;font-size:clamp(12px,1.1vw,16px)}
.d{display:flex;flex-direction:column;padding:clamp(10px,1.2vh,20px) clamp(16px,2vw,32px);gap:clamp(6px,0.8vh,14px);max-width:1920px;margin:0 auto;width:100%;height:100vh}
.hd{display:flex;align-items:center;justify-content:space-between;flex-shrink:0}
.hd h1{font-size:clamp(16px,1.8vw,26px);font-weight:700;color:#e2e8f0;letter-spacing:-.3px}
.hd h1 span{color:#52525b;font-weight:400}
.hd .ts{font-size:clamp(9px,0.8vw,12px);color:#52525b;font-family:monospace}
.mr{display:grid;grid-template-columns:repeat(6,1fr);gap:clamp(4px,0.5vw,10px);flex-shrink:0}
.mi{background:#111827;border:1px solid #1e293b;border-radius:8px;padding:clamp(8px,1vh,16px) clamp(10px,1vw,18px)}
.mi .mv{font-size:clamp(20px,2.5vw,36px);font-weight:800;line-height:1}
.mi .ml{font-size:clamp(8px,0.7vw,10px);color:#64748b;text-transform:uppercase;letter-spacing:.5px;margin-top:4px;font-weight:500}
.mi:nth-child(1) .mv{color:#60a5fa}
.mi:nth-child(2) .mv{color:#4ade80}
.mi:nth-child(3) .mv{color:#facc15}
.mi:nth-child(4) .mv{color:#f87171}
.mi:nth-child(5) .mv{color:#a78bfa}
.mi:nth-child(6) .mv{color:#f472b6}
.br{display:grid;grid-template-columns:1fr 1fr;gap:clamp(4px,0.5vw,10px);flex:1;min-height:0}
.bc{border-radius:10px;overflow:hidden;border:1px solid #1e293b;display:flex;flex-direction:column}
.bc .bh{display:flex;align-items:center;padding:clamp(8px,0.8vh,14px) clamp(12px,1.2vw,18px);background:#111827;gap:8px;flex-shrink:0}
.bc .bh .bl{width:clamp(22px,1.8vw,30px);height:clamp(22px,1.8vw,30px);border-radius:5px;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:clamp(11px,0.9vw,14px);color:#fff;flex-shrink:0}
.bc .bh .uc{background:#2563eb}.bc .bh .lm{background:#dc2626}
.bc .bh h2{font-size:clamp(12px,1vw,16px);font-weight:700;color:#e2e8f0}
.bc .bh .bs{margin-left:auto;font-size:clamp(9px,0.7vw,11px);color:#64748b}
.bc .bh .bs b{color:#e2e8f0;font-weight:700}
.bc .bh .bs .gr{color:#4ade80}
.bc .bb{flex:1;overflow-y:auto;padding:clamp(8px,0.6vh,12px) clamp(12px,1.2vw,18px);background:#0f1117;display:flex;flex-direction:column;gap:clamp(6px,0.5vh,10px)}
.sv{border-radius:8px;padding:clamp(8px,0.6vh,12px) clamp(10px,0.8vw,14px);border:1px solid #1e293b}
.sv.ye{border-color:#5c4a00;background:linear-gradient(135deg,#2a2000 0%,#1a1500 100%)}
.sv.re{border-color:#7f1d1d;background:linear-gradient(135deg,#2a0a0a 0%,#1a0808 100%)}
.sv.gr{border-color:#166534;background:linear-gradient(135deg,#0a2e1a 0%,#0a1f12 100%)}
.sv .svh{display:flex;align-items:center;justify-content:space-between;margin-bottom:clamp(4px,0.3vh,6px)}
.sv .svh .sn{font-size:clamp(11px,0.9vw,14px);font-weight:600;color:#e2e8f0}
.sv .svh .sn .loc{display:block;font-size:clamp(8px,0.6vw,10px);color:#64748b;font-weight:400;margin-top:1px}
.sv .svh .sc{font-size:clamp(11px,0.9vw,14px);font-weight:700;color:#94a3b8}
.sv .sg{display:grid;grid-template-columns:1fr 1fr 1fr;gap:4px}
.sv .si{background:rgba(15,17,23,.5);border-radius:6px;padding:clamp(5px,0.4vh,8px) 0;text-align:center;border:1px solid rgba(45,55,72,.4)}
.sv .si .il{font-size:clamp(7px,0.55vw,9px);text-transform:uppercase;color:#64748b;letter-spacing:.5px}
.sv .si .iv{font-size:clamp(16px,1.4vw,22px);font-weight:800;margin-top:1px;line-height:1}
.sv .si .iv.gr{color:#4ade80}.sv .si .iv.ye{color:#facc15}.sv .si .iv.re{color:#f87171}
.al{flex-shrink:0;border-top:1px solid #1e293b;padding:clamp(6px,0.5vh,10px) 0 0}
.al .ah{display:flex;align-items:center;gap:6px;font-size:clamp(10px,0.8vw,12px);font-weight:600;color:#f87171;margin-bottom:clamp(4px,0.3vh,6px)}
.al .ah .ac{margin-left:auto;background:#1a0a0a;color:#f87171;padding:0 10px;border-radius:10px;font-size:clamp(8px,0.65vw,10px)}
.al table{width:100%;border-collapse:collapse;font-size:clamp(9px,0.7vw,11px)}
.al th{padding:clamp(3px,0.2vh,5px) clamp(6px,0.5vw,10px);color:#52525b;font-weight:500;text-align:left;font-size:clamp(7px,0.55vw,9px);text-transform:uppercase;letter-spacing:.3px;border-bottom:1px solid #1e293b}
.al td{padding:clamp(3px,0.2vh,5px) clamp(6px,0.5vw,10px);border-bottom:1px solid rgba(255,255,255,.03);color:#94a3b8}
.al .st{color:#4ade80;font-weight:600}
.al .ec{color:#f87171;font-weight:600}.al .wc{color:#facc15;font-weight:600}
@media(max-width:900px){.mr{grid-template-columns:repeat(3,1fr)}.br{grid-template-columns:1fr}}
@media(min-width:1800px){.br{grid-template-columns:1fr 1fr}}
</style>
</head>
<body>
<div class="d">
<div class="hd"><h1>Retail Media <span>· IoT Status</span></h1><div class="ts" id="ts">${esc(dateStr)}</div></div>

<div class="mr">
  <div class="mi"><div class="mv">${totalDevices}</div><div class="ml">Total Devices · ${VENUES.length} venues</div></div>
  <div class="mi"><div class="mv">${totalTracking}</div><div class="ml">Tracking OK</div></div>
  <div class="mi"><div class="mv">${totalWarnings}</div><div class="ml">Warnings</div></div>
  <div class="mi"><div class="mv">${totalErrors}</div><div class="ml">Errors</div></div>
  <div class="mi"><div class="mv">~${totalDevices > 0 ? Math.round(totalTracking / totalDevices * 100) : 0}%</div><div class="ml">Avg Uptime</div></div>
  <div class="mi"><div class="mv">J30</div><div class="ml">Platform</div></div>
</div>

<div class="br">
${brandCols}
</div>

<div class="al">
  <div class="ah">⚠ Devices needing attention <span class="ac">${attTotal}</span></div>
  
  <table>
    <tr><th>Venue / Asset</th><th>Device</th><th>State</th><th>Last seen</th></tr>
${attRows}
  </table>
  
</div>
</div>
</body>
</html>`;

fs.writeFileSync(OUTPUT, html);
console.log(`OK - ${(Buffer.byteLength(html) / 1024).toFixed(0)} KB — ${totalDevices} devices, ${totalErrors} errors, ${attTotal} attention`);
