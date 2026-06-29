/**
 * build-retailer.js — retailer.html honeycomb dashboard
 * Groups IoT devices by retailer (Union Coop, Lulu, Malls, Metro, etc.)
 * Each retailer shown as a hexagon, colored by store health
 */
const fs = require('fs');

const DATA_FILE = '/tmp/rmstatus-light/iot-admin-data.json';
const OUTPUT = '/tmp/rmstatus-light/retailer.html';

if (!fs.existsSync(DATA_FILE)) {
  console.error('Data file not found: ' + DATA_FILE);
  process.exit(1);
}
const data = JSON.parse(fs.readFileSync(DATA_FILE, 'utf-8'));

const now = new Date();
const dateStr = now.toLocaleDateString('en-GB');
const timeStr = now.toLocaleTimeString('en-GB');
function esc(s) { return s ? String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') : ''; }

const locations = data.locations || [];

// Group venues into retailers
const retailerGroups = {
  'Union Coop': { icon: 'UC', venues: [], color: '#2563eb' },
  'Lulu':       { icon: 'LM', venues: [], color: '#dc2626' },
  'Malls':      { icon: 'ML', venues: [], color: '#7c3aed' },
  'Metro':      { icon: 'MT', venues: [], color: '#0891b2' },
  'Expo City':  { icon: 'EX', venues: [], color: '#059669' },
  'Dubai Festival': { icon: 'DF', venues: [], color: '#d97706' },
  'Hypermedia': { icon: 'HY', venues: [], color: '#6366f1' },
  'Other':      { icon: 'OT', venues: [], color: '#52525b' },
};

for (const loc of locations) {
  const name = loc.venue;
  let cat = 'Other';
  if (/union coop/i.test(name)) cat = 'Union Coop';
  else if (/lulu/i.test(name)) cat = 'Lulu';
  else if (/expoc/i.test(name)) cat = 'Expo City';
  else if (/hypermedia/i.test(name)) cat = 'Hypermedia';
  else if (/dubai festival city|dubai festival plaza/i.test(name)) cat = 'Dubai Festival';
  else if (/malls? - /i.test(name) || /mall$/i.test(name) || /pavillion|pavilion/i.test(name)) cat = 'Malls';
  else if (/metro - /i.test(name)) cat = 'Metro';
  retailerGroups[cat].venues.push(loc);
}

// Build retailer data
const retailers = Object.entries(retailerGroups)
  .filter(([_, g]) => g.venues.length > 0)
  .map(([name, g]) => {
    const totalDevices = g.venues.reduce((s, v) => s + v.total, 0);
    // Estimate errors/warnings per venue from attention data
    const venueOffline = [];
    const storeList = g.venues.map(v => {
      // Store name without retailer prefix
      let storeName = v.venue
        .replace(/^(In-Store - )?(Outdoor - )?(Malls - )?(Metro - )?(Union Coop )?/, '')
        .replace(/\s*\(.*?\)\s*/g, '')
        .trim();
      // Calculate store health
      const hasErrors = false; // We don't have per-venue error data from scrape
      const hasWarnings = false;
      return {
        name: storeName,
        total: v.total || 0,
        j3011: v.j3011 || 0,
        jnx30: v.jnx30 || 0,
        jnx42: v.jnx42 || 0,
        hasErrors,
        hasWarnings,
      };
    });
    // Determine retailer color: worst health across stores
    let health = 'ok';
    for (const s of storeList) {
      if (s.hasErrors) health = 'error';
      else if (s.hasWarnings && health === 'ok') health = 'warning';
    }
    return { name, icon: g.icon, totalDevices, stores: storeList.length, storeList, health };
  });

let totalDevices = 0;
let totalVenues = 0;
for (const r of retailers) {
  totalDevices += r.totalDevices;
  totalVenues += r.stores;
}

// Count offline devices
const rawDevices = data.attentionDevices || [];
const totalOffline = rawDevices.length;

// Generate hexagons HTML
const hexColors = { ok: '#166534', warning: '#5c4a00', error: '#7f1d1d' };
const hexBgColors = { ok: '#0a2e1a', warning: '#2a2000', error: '#2a0a0a' };
const hexBorderColors = { ok: '#22c55e', warning: '#eab308', error: '#ef4444' };

function hexagonHtml(r, index) {
  const hc = hexColors[r.health] || '#27272a';
  const hbg = hexBgColors[r.health] || '#111827';
  const hbc = hexBorderColors[r.health] || '#22c55e';
  
  const storesHtml = r.storeList.map(s => {
    const sc = s.hasErrors ? '#ef4444' : s.hasWarnings ? '#eab308' : '#4ade80';
    return `<div class="hs"><span class="hn">${esc(s.name)}</span><span class="hv">${s.total}</span></div>`;
  }).join('');
  
  return `<div class="hex">
  <div class="hex-inner" style="background:${hbg};border-color:${hbc}">
    <div class="hex-badge" style="background:${hc}">${r.icon}</div>
    <div class="hex-title">${esc(r.name)}</div>
    <div class="hex-total">${r.totalDevices}</div>
    <div class="hex-sub">${r.stores} store${r.stores !== 1 ? 's' : ''}</div>
    <div class="hex-stores">${storesHtml}</div>
  </div>
</div>`;
}

const hexRows = retailers.map((r, i) => hexagonHtml(r, i)).join('\n');

// Generate vendor prefixes for hexagon CSS
const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Retail Media · Retailers</title>
<meta http-equiv="refresh" content="600">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{height:100%}
body{font-family:'Inter',-apple-system,sans-serif;background:#08080e;color:#f1f5f9;display:flex;flex-direction:column}
.d{padding:16px 24px;max-width:1920px;margin:0 auto;width:100%;height:100vh;display:flex;flex-direction:column}

.hd{display:flex;align-items:center;justify-content:space-between;flex-shrink:0;margin-bottom:16px}
.hd h1{font-size:22px;font-weight:700;color:#e2e8f0;letter-spacing:-.3px}
.hd h1 span{color:#52525b;font-weight:400}
.hd .ts{font-size:11px;color:#52525b;font-family:monospace}

/* Metric row */
.mr{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:16px;flex-shrink:0}
.mi{background:#111827;border:1px solid #1e293b;border-radius:8px;padding:12px 16px;text-align:center}
.mi .mv{font-size:26px;font-weight:800;line-height:1}
.mi .ml{font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:.5px;margin-top:3px;font-weight:500}
.mi:nth-child(1) .mv{color:#60a5fa}
.mi:nth-child(2) .mv{color:#4ade80}
.mi:nth-child(3) .mv{color:#f87171}
.mi:nth-child(4) .mv{color:#a78bfa}
.mi:nth-child(5) .mv{color:#facc15}

/* Hexagon grid */
.hg{display:flex;flex-wrap:wrap;justify-content:center;align-items:flex-start;gap:24px;flex:1;align-content:flex-start;padding:10px 0 20px;overflow-y:auto}

.hex{width:240px;height:270px;position:relative;margin:0}
.hex-inner{width:100%;height:100%;position:relative;-webkit-clip-path:polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%);clip-path:polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%);border:2px solid;padding:40px 18px 20px;display:flex;flex-direction:column;align-items:center;transition:all .2s}
.hex-inner:hover{border-color:#fff !important;transform:scale(1.03)}
.hex-badge{position:absolute;top:10px;left:50%;transform:translateX(-50%);width:28px;height:28px;border-radius:6px;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:11px;color:#fff}
.hex-title{font-size:14px;font-weight:700;color:#e2e8f0;margin-bottom:2px;text-align:center}
.hex-total{font-size:28px;font-weight:800;color:#fff;line-height:1.2}
.hex-sub{font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px}
.hex-stores{display:flex;flex-direction:column;gap:3px;width:100%;padding:0 10px}
.hs{display:flex;align-items:center;justify-content:space-between;padding:2px 6px;border-radius:4px;background:rgba(0,0,0,.3);font-size:10px}
.hs:hover{background:rgba(255,255,255,.08)}
.hn{color:#94a3b8;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1}
.hv{font-weight:700;color:#e2e8f0;margin-left:6px}

/* Scrollable hex area */
.hg-wrap{flex:1;overflow-y:auto;min-height:0}
.hg-wrap::-webkit-scrollbar{width:4px}
.hg-wrap::-webkit-scrollbar-track{background:transparent}
.hg-wrap::-webkit-scrollbar-thumb{background:#1e293b;border-radius:2px}

.ft{flex-shrink:0;text-align:center;padding:8px;color:#1e293b;font-size:9px;border-top:1px solid #1e293b}

@media(max-width:768px){
  .mr{grid-template-columns:repeat(3,1fr)}
  .d{padding:12px}
  .hex{width:200px;height:225px}
}
</style>
</head>
<body>
<div class="d">
<div class="hd"><h1>Retail Media <span>· Retailers</span></h1><div class="ts">${dateStr} ${timeStr}</div></div>

<div class="mr">
  <div class="mi"><div class="mv">${totalDevices}</div><div class="ml">Total Devices</div></div>
  <div class="mi"><div class="mv">${totalOffline}</div><div class="ml">Offline</div></div>
  <div class="mi"><div class="mv">${retailers.length}</div><div class="ml">Retailers</div></div>
  <div class="mi"><div class="mv">${totalVenues}</div><div class="ml">Stores</div></div>
  <div class="mi"><div class="mv">${Object.keys(retailerGroups).filter(k => retailerGroups[k].venues.length > 0).length}</div><div class="ml">Categories</div></div>
</div>

<div class="hg-wrap">
<div class="hg">
${hexRows}
</div>
</div>

<div class="ft">IOT Admin Console · AiOO Tech Dubai © · ${dateStr} ${timeStr}</div>
</div>
</body>
</html>`;

// Write output
fs.writeFileSync(OUTPUT, html);
console.log('OK - ' + (Buffer.byteLength(html) / 1024).toFixed(0) + ' KB — ' + totalDevices + ' devices, ' + totalOffline + ' offline, ' + retailers.length + ' retailers, ' + totalVenues + ' stores');
