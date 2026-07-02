/**
 * build-retailer.js — retailer.html honeycomb dashboard
 * Groups IoT devices by retailer (Union Coop, Lulu, Carrefour)
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

// Group venues into retailers — Union Coop, Lulu, Carrefour
const retailerGroups = {
  'Union Coop': { icon: 'UC', venues: [], color: '#2563eb' },
  'Lulu':       { icon: 'LM', venues: [], color: '#dc2626' },
  'Carrefour':  { icon: 'CR', venues: [], color: '#16a34a' },
};

for (const loc of locations) {
  const name = loc.venue;
  if (/union coop/i.test(name)) {
    retailerGroups['Union Coop'].venues.push(loc);
  } else if (/lulu/i.test(name)) {
    retailerGroups['Lulu'].venues.push(loc);
  } else if (/carrefour/i.test(name)) {
    retailerGroups['Carrefour'].venues.push(loc);
  }
}

// Count offline devices per location by matching venue names
const venueOffline = {};
for (const [fullVenue, devs] of Object.entries(data.offlineByVenue || {})) {
  // Match: offline venue name should start with location venue name
  // e.g. "In-Store - Union Coop UMM SUQEIM IOT_8" starts with "In-Store - Union Coop UMM SUQEIM"
  // Find which location this matches
  let matched = false;
  for (const loc of locations) {
    if (fullVenue.startsWith(loc.venue)) {
      venueOffline[loc.venue] = (venueOffline[loc.venue] || 0) + devs.length;
      matched = true;
      break;
    }
  }
  if (!matched) {
    // Try broader match
    const name = fullVenue.split(/\s{2,}| In Store| IOT_| TOTEM| Screen/)[0].trim();
    for (const loc of locations) {
      if (name.startsWith(loc.venue)) {
        venueOffline[loc.venue] = (venueOffline[loc.venue] || 0) + devs.length;
        break;
      }
    }
  }
}

// Build retailer data
const retailers = Object.entries(retailerGroups)
  .map(([name, g]) => {
    const isPlaceholder = g.venues.length === 0;
    const totalDevices = g.venues.reduce((s, v) => s + v.total, 0);
    const storeList = g.venues.map(v => {
      let storeName = v.venue
        .replace(/^(In-Store - )?(Outdoor - )?(Union Coop )?/, '')
        .replace(/\s*\(.*?\)\s*/g, '')
        .trim();
      const offlineCount = venueOffline[v.venue] || 0;
      const tracking = (v.total || 0) - offlineCount;
      return {
        name: storeName,
        total: v.total || 0,
        tracking,
        offline: offlineCount,
        hasErrors: offlineCount > 0,
        hasWarnings: false,
      };
    });
    
    let health = 'ok';
    for (const s of storeList) {
      if (s.hasErrors) health = 'error';
      else if (s.hasWarnings && health === 'ok') health = 'warning';
    }
    if (isPlaceholder) health = 'placeholder';
    
    const totalOffline = storeList.reduce((s, v) => s + v.offline, 0);
    
    return { 
      name, icon: g.icon, totalDevices, stores: storeList.length, 
      storeList, health, totalOffline, isPlaceholder,
    };
  });

let totalDevices = 0;
let totalVenues = 0;
let grandTotalOffline = 0;
for (const r of retailers) {
  totalDevices += r.totalDevices;
  totalVenues += r.stores;
  grandTotalOffline += r.totalOffline;
}

// Colors
const hexColors = { 
  ok: '#166534', warning: '#5c4a00', error: '#7f1d1d', placeholder: '#27272a' 
};
const hexBgColors = { 
  ok: '#0a2e1a', warning: '#2a2000', error: '#2a0a0a', placeholder: '#0f0f14' 
};
const hexBorderColors = { 
  ok: '#22c55e', warning: '#eab308', error: '#ef4444', placeholder: '#3f3f46' 
};

function hexagonHtml(r) {
  const hc = hexColors[r.health] || '#27272a';
  const hbg = hexBgColors[r.health] || '#111827';
  const hbc = hexBorderColors[r.health] || '#22c55e';
  
  let storesHtml;
  let subtitle;
  
  if (r.isPlaceholder) {
    storesHtml = `<div class="ph"><span class="ph-icon">📦</span><span class="ph-text">No retail data</span></div>`;
    subtitle = `<span style="color:#52525b">no data</span>`;
  } else {
    storesHtml = r.storeList.map(s => {
      let storeBorder = '#166534';
      let storeBg = '#0a2e1a';
      let storeColor = '#4ade80';
      if (s.hasErrors) {
        storeBorder = '#7f1d1d';
        storeBg = '#2a0a0a';
        storeColor = '#f87171';
      } else if (s.hasWarnings) {
        storeBorder = '#5c4a00';
        storeBg = '#2a2000';
        storeColor = '#eab308';
      }
      const val = s.offline > 0 
        ? `<span class="hv" style="color:#f87171">${s.offline} offline</span>` 
        : `<span class="hv" style="color:#4ade80">${s.tracking} ok</span>`;
      return `<div class="hs" style="border-color:${storeBorder};background:${storeBg}"><span class="hn">${esc(s.name)}</span>${val}</div>`;
    }).join('');
    subtitle = `${r.stores} store${r.stores !== 1 ? 's' : ''} · <span style="color:${r.totalOffline > 0 ? '#f87171' : '#4ade80'}">${r.totalOffline > 0 ? r.totalOffline + ' offline' : 'all ok'}</span>`;
  }
  
  return `<div class="hex${r.isPlaceholder ? ' ph-hex' : ''}">
  <div class="hex-inner${r.isPlaceholder ? ' ph-inner' : ''}" style="background:${hbg};border-color:${hbc}">
    <div class="hex-glow" style="background:${hbc}"></div>
    <div class="hex-badge" style="background:${hc}">${r.icon}</div>
    <div class="hex-title">${esc(r.name)}</div>
    <div class="hex-total">${r.totalDevices || (r.isPlaceholder ? '—' : '0')}</div>
    <div class="hex-sub">${subtitle}</div>
    <div class="hex-stores">${storesHtml}</div>
    ${r.isPlaceholder ? '' : `<div class="hex-track"><div class="hex-dot"></div><div class="hex-dot"></div><div class="hex-dot"></div></div>`}
  </div>
</div>`;
}

const hexRows = retailers.map(r => hexagonHtml(r)).join('\n');

const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Retail Media · Retailers</title>
<meta http-equiv="refresh" content="300">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{height:100%}
body{font-family:'Inter',-apple-system,sans-serif;background:radial-gradient(ellipse at 50% 30%, #0f1219 0%, #08080e 70%);color:#f1f5f9;display:flex;flex-direction:column}
.d{padding:16px 24px;max-width:1920px;margin:0 auto;width:100%;height:100vh;display:flex;flex-direction:column}

/* Header */
.hd{display:flex;align-items:center;justify-content:space-between;flex-shrink:0;margin-bottom:10px;padding-bottom:10px;border-bottom:1px solid rgba(255,255,255,.04)}
.hd h1{font-size:20px;font-weight:700;color:#e2e8f0;letter-spacing:-.3px}
.hd h1 span{color:#52525b;font-weight:400}
.hd .ts{font-size:10px;color:#52525b;font-family:monospace;background:#111827;padding:3px 10px;border-radius:6px;border:1px solid #1e293b}

/* Metric row */
.mr{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:14px;flex-shrink:0}
.mi{background:linear-gradient(135deg,#111827 0%,#0f1119 100%);border:1px solid #1e293b;border-radius:10px;padding:10px 14px;text-align:center;position:relative;overflow:hidden}
.mi::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;border-radius:10px 10px 0 0}
.mi:nth-child(1)::before{background:linear-gradient(90deg,#3b82f6,#60a5fa)}
.mi:nth-child(2)::before{background:linear-gradient(90deg,#16a34a,#4ade80)}
.mi:nth-child(3)::before{background:linear-gradient(90deg,#dc2626,#f87171)}
.mi:nth-child(4)::before{background:linear-gradient(90deg,#7c3aed,#a78bfa)}
.mi .mv{font-size:24px;font-weight:800;line-height:1}
.mi .ml{font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:.5px;margin-top:3px;font-weight:500}

/* Hexagon grid */
.hg{display:flex;flex-wrap:nowrap;justify-content:center;align-items:center;gap:12px;flex:1;padding:10px 0}

.hex{width:320px;height:360px;position:relative;margin:0;flex-shrink:0;filter:drop-shadow(0 4px 20px rgba(0,0,0,.4))}
.hex-inner{width:100%;height:100%;position:relative;-webkit-clip-path:polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%);clip-path:polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%);border:2px solid;padding:50px 22px 18px;display:flex;flex-direction:column;align-items:center;transition:all .3s cubic-bezier(.4,0,.2,1)}
.hex-inner:hover{transform:scale(1.04);border-color:#fff !important;filter:brightness(1.15)}
.hex-glow{position:absolute;top:2px;left:2px;right:2px;height:8px;opacity:.3;border-radius:0;}

.hex-badge{position:absolute;top:14px;left:50%;transform:translateX(-50%);width:30px;height:30px;border-radius:7px;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:12px;color:#fff;box-shadow:0 2px 8px rgba(0,0,0,.3)}
.hex-title{font-size:15px;font-weight:700;color:#e2e8f0;margin-bottom:2px;text-align:center}
.hex-total{font-size:32px;font-weight:800;color:#fff;line-height:1.2;letter-spacing:-1px}
.hex-sub{font-size:9px;color:#94a3b8;text-transform:uppercase;letter-spacing:.6px;margin-bottom:8px}
.hex-stores{display:flex;flex-direction:column;gap:3px;width:100%;padding:0 12px;flex:1;overflow-y:auto}
.hex-stores::-webkit-scrollbar{width:2px}
.hex-stores::-webkit-scrollbar-thumb{background:#1e293b;border-radius:1px}
.hs{display:flex;align-items:center;justify-content:space-between;padding:3px 8px;border-radius:5px;border:1px solid;font-size:11px;transition:all .2s}
.hs:hover{background:rgba(255,255,255,.1) !important}
.hn{color:#e2e8f0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;font-weight:500}
.hv{font-weight:700;margin-left:6px}

/* Placeholder hex */
.ph-hex{opacity:.6}
.ph-inner{border-style:dashed !important}
.ph{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;padding:20px 0;color:#52525b}
.ph-icon{font-size:28px}
.ph-text{font-size:11px;color:#64748b;text-align:center;font-style:italic}

/* Decorative dots */
.hex-track{display:flex;gap:4px;position:absolute;bottom:14px;left:50%;transform:translateX(-50%)}
.hex-dot{width:4px;height:4px;border-radius:50%;background:rgba(255,255,255,.06)}

.ft{flex-shrink:0;text-align:center;padding:6px;color:#1e293b;font-size:9px;border-top:1px solid #1e293b;letter-spacing:.3px}

@media(max-width:900px){
  .mr{grid-template-columns:repeat(2,1fr)}
  .d{padding:12px}
  .hg{flex-wrap:wrap;gap:8px}
  .hex{width:260px;height:300px}
}
</style>
</head>
<body>
<div class="d">
<div class="hd"><h1>Retail Media <span>· Retailers</span></h1><div class="ts">${dateStr} ${timeStr}</div></div>

<div class="mr">
  <div class="mi"><div class="mv">${totalDevices}</div><div class="ml">Total Devices</div></div>
  <div class="mi"><div class="mv">${grandTotalOffline}</div><div class="ml">Offline</div></div>
  <div class="mi"><div class="mv">${retailers.filter(r => !r.isPlaceholder).length}</div><div class="ml">Active Retailers</div></div>
  <div class="mi"><div class="mv">${totalVenues}</div><div class="ml">Stores</div></div>
</div>

<div class="hg">
${hexRows}
</div>

<div class="ft">IOT Admin Console · AiOO Tech Dubai © · ${dateStr} ${timeStr}</div>
</div>
</body>
</html>`;

fs.writeFileSync(OUTPUT, html);
console.log('OK - ' + (Buffer.byteLength(html) / 1024).toFixed(0) + ' KB — ' + totalDevices + ' devices, ' + grandTotalOffline + ' offline');
