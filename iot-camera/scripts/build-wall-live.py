#!/usr/bin/env python3
"""Build wall-live-api.html — static (no JS templates), same wall IOT design"""
import json, os

DATA_FILE = '/tmp/rmstatus-light/iot-admin-data.json'
OUTPUT = '/tmp/rmstatus-light/wall-live-api.html'

with open(DATA_FILE) as f:
    data = json.load(f)

devices = data.get('devices', data)
if isinstance(devices, dict):
    devices = data.get('devices', [])

# States
from collections import Counter
states = Counter()
platforms = Counter()
cameras = Counter()
offline = []

for d in devices:
    s = d.get('state','Unknown')
    states[s] += 1
    p = (d.get('platform','unknown').lower())
    platforms[p] += 1
    c = d.get('camera','')
    if c: cameras[c] += 1
    if s == 'Offline': offline.append(d)

total = sum(states.values())
offCount = states.get('Offline',0)

# Top 14 recent offline
offline.sort(key=lambda d: (d.get('last_seen') or ''), reverse=True)
attention = offline[:14]

# Compute venue count
venues = set()
for d in devices:
    v = (d.get('venue','') or '').split('|')[0].strip()
    if v: venues.add(v)

def donut_svg(data, total):
    if not total: return ''
    R, cx, cy = 90, 120, 120
    circ = 2 * 3.14159 * R
    cur = 0
    arcs = []
    for item in data:
        pct = item['v'] / total
        length = max(circ * pct, 0.5)
        offset = -(cur / total) * circ
        cur += pct
        arcs.append(f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="{item["c"]}" stroke-width="35" stroke-dasharray="{length} {circ-length}" stroke-dashoffset="{offset}" transform="rotate(-90 {cx} {cy})"/>')
    arcs_str = ''.join(arcs)
    return f'''<svg viewBox="0 0 240 240">
<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="#27272a" stroke-width="35"/>
{arcs_str}
<text x="{cx}" y="{cy+6}" text-anchor="middle" fill="#e2e8f0" font-size="28" font-weight="800">{total}</text>
<text x="{cx}" y="{cy+28}" text-anchor="middle" fill="#64748b" font-size="11">devices</text>
</svg>'''

# Colors
state_colors = {'Ready':'#4ade80','Tracking':'#3b82f6','Idle':'#facc15','Offline':'#ef4444','Unknown':'#52525b'}
state_order = ['Ready','Tracking','Idle','Offline','Unknown']
state_data = [{'l':s,'v':states[s],'c':state_colors[s]} for s in state_order if states.get(s,0)>0]

plat_palette = ['#06b6d4','#22c55e','#3b82f6','#6366f1','#f59e0b','#14b8a6','#8b5cf6','#0891b2','#52525b']
plat_order = sorted(platforms.items(), key=lambda x:-x[1])
plat_data = [{'l':p.upper(),'v':c,'c':plat_palette[i%len(plat_palette)]} for i,(p,c) in enumerate(plat_order)]

cam_palette = ['#06b6d4','#22c55e','#3b82f6','#6366f1','#f59e0b','#14b8a6','#52525b']
cam_order = sorted(cameras.items(), key=lambda x:-x[1])
cam_data = [{'l':c.replace('_',' '),'v':n,'color':cam_palette[i%len(cam_palette)]} for i,(c,n) in enumerate(cam_order)]

def legend(data):
    return ''.join(f'''<div class="leg-item"><div class="leg-dot" style="background:{d['c']}"></div><span class="leg-label">{d['l']}</span><span class="leg-val">{d['v']}</span><span class="leg-pct">{(d['v']/total*100):.1f}%</span></div>''' for d in data)

def donut_card(title, data, t):
    svg = donut_svg([{'v':d['v'],'c':d['c']} for d in data], t)
    leg = legend(data)
    return f'''<div class="chart-card"><div class="ch"><h3>{title}</h3><span class="ch-sub">{t} total</span></div><div class="chart-body"><div class="chart-wrap"><div class="chart-svg">{svg}</div><div class="legend">{leg}</div></div></div></div>'''

html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<meta http-equiv="refresh" content="300">
<title>IOT Dashboard — Wall Display (Live API)</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:Inter,-apple-system,BlinkMacSystemFont,sans-serif;background:#0d1117;color:#e2e8f0;min-height:100vh;padding:0}}
.hdr{{padding:16px 24px;border-bottom:1px solid #1e293b;display:flex;align-items:center;justify-content:space-between}}
.hdr h1{{font-size:18px;font-weight:600;color:#e2e8f0}}
.hdr .ts{{color:#52525b;font-size:11px;font-family:monospace}}
.summary{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;padding:16px 24px}}
.sc{{background:#161b22;border-radius:10px;border:1px solid #1e293b;padding:14px 16px;text-align:center}}
.sc .sv{{font-size:32px;font-weight:800;line-height:1.2}}
.sc .sl{{font-size:11px;color:#64748b;margin-top:4px;text-transform:uppercase;letter-spacing:.5px}}
.sc.b .sv{{color:#60a5fa}}.sc.g .sv{{color:#4ade80}}.sc.r .sv{{color:#f87171}}
.grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;padding:0 24px}}
@media(max-width:1200px){{.grid{{grid-template-columns:1fr}}}}
.chart-card{{background:#161b22;border-radius:12px;border:1px solid #1e293b;overflow:hidden}}
.chart-card .ch{{display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid #1e293b}}
.chart-card .ch h3{{font-size:12px;font-weight:600;color:#e2e8f0}}
.chart-card .ch .ch-sub{{font-size:10px;color:#64748b}}
.chart-body{{padding:16px}}
.chart-wrap{{display:flex;align-items:center;gap:24px;justify-content:center}}
.chart-svg{{width:160px;height:160px;flex-shrink:0}}
.legend{{display:flex;flex-direction:column;gap:8px;min-width:110px}}
.leg-item{{display:flex;align-items:center;gap:8px;font-size:12px}}
.leg-dot{{width:10px;height:10px;border-radius:3px;flex-shrink:0}}
.leg-label{{color:#94a3b8;flex:1;white-space:nowrap}}
.leg-val{{font-weight:700;font-size:14px;color:#e2e8f0}}
.leg-pct{{font-size:9px;color:#52525b;margin-left:3px}}
.table-wrap{{padding:16px 24px 24px}}
.tc{{background:#161b22;border-radius:12px;border:1px solid #1e293b;overflow:hidden}}
.thdr{{padding:14px 18px;font-size:13px;font-weight:600;color:#fca5a5;border-bottom:1px solid #1e293b;display:flex;align-items:center;justify-content:space-between}}
.thdr .sub{{color:#64748b;font-size:11px;font-weight:400}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{padding:10px 16px;text-align:left;color:#64748b;font-weight:600;font-size:10px;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid #1e293b}}
td{{padding:10px 16px;border-bottom:1px solid #1e293b;color:#94a3b8}}
tr:hover td{{background:#1e293b40}}
.st-o{{color:#f87171;font-weight:700}}
</style>
</head>
<body>
<div class="hdr"><h1>IOT Dashboard — Wall Display</h1><span class="ts">Last update: (auto)</span></div>
<div class="summary"><div class="sc b"><div class="sv">{total}</div><div class="sl">Total devices</div></div><div class="sc g"><div class="sv">{total-offCount}</div><div class="sl">Online</div></div><div class="sc r"><div class="sv">{offCount}</div><div class="sl">OFFLINE</div></div><div class="sc b"><div class="sv">{len(venues)}</div><div class="sl">Venues</div></div></div>
<div class="grid" id="content">
{donut_card('Devices by state', state_data, total)}
{donut_card('All devices by platform', plat_data, total)}
{donut_card('Device by camera type', cam_data, total)}
</div>
<div class="table-wrap"><div class="tc"><div class="thdr">⚠ Devices needing attention <span class="sub">{len(attention)} device{"s" if len(attention)!=1 else ""}</span></div>
<table><thead><tr><th>Device</th><th>Venue</th><th>Location</th><th>State</th><th>Last seen</th></tr></thead>
<tbody>{"".join(f'<tr><td style="font-family:monospace">{d.get("aioo_id") or d.get("mac") or d.get("device") or "—"}</td><td>{(d.get("venue") or "—").split("|")[0].strip()}</td><td>{"|".join(((d.get("venue") or "—").split("|")[1:])).strip() or "—"}</td><td class="st-o">OFFLINE</td><td>{d.get("last_seen") or "—"}</td></tr>' for d in attention)}</tbody></table></div></div>
<script>setTimeout(function(){{location.reload()}},300000)</script>
</body>
</html>'''

os.makedirs(os.path.dirname(OUTPUT) or '.', exist_ok=True)
with open(OUTPUT, 'w') as f:
    f.write(html)

kb = len(html) / 1024
print(f'OK - {kb:.0f} KB — {total} devices, {offCount} offline, {len(venues)} venues')
