#!/usr/bin/env python3
"""Build nsoc-status.html — Operations dashboard (offline PCs in red)"""
import json, os, urllib.request, datetime

# ── Auth ──────────────────────────────────────────────────────
def _load_creds():
    env = {}
    for path in ['~/.openclaw/workspace/.nsoc_creds', '~/.nsoc_creds']:
        f = os.path.expanduser(path)
        if os.path.exists(f):
            with open(f) as fh:
                for line in fh:
                    line = line.strip()
                    if line.startswith('export '):
                        line = line[7:]
                    if '=' in line and not line.startswith('#'):
                        k, v = line.split('=', 1)
                        env[k.strip()] = v.strip().strip('"').strip("'")
    return env

_creds = _load_creds()
glpi_url = os.environ.get('GLPI_API_URL') or _creds.get('GLPI_API_URL')
app_token = os.environ.get('GLPI_APP_TOKEN') or _creds.get('GLPI_APP_TOKEN')
user_token = os.environ.get('GLPI_USER_TOKEN') or _creds.get('GLPI_USER_TOKEN')

req = urllib.request.Request(f"{glpi_url}/initSession",
    headers={"App-Token": app_token, "Authorization": f"user_token {user_token}"})
resp = urllib.request.urlopen(req).read()
session_token = json.loads(resp)['session_token']

req2 = urllib.request.Request(
    f"{glpi_url}/search/Computer?expand_dropdowns=true&withplugins=true&range=0-2000",
    headers={"Session-Token": session_token, "App-Token": app_token})
resp2 = urllib.request.urlopen(req2).read()
data = json.loads(resp2)
devices = data.get('data', [])

# ── Parse ─────────────────────────────────────────────────────
GREEN_EMOJI = '🟢'
venues = {
    'Union Coop - Umm Suqeim': {'label': 'Umm Suqeim', 'color': '#3b82f6'},
    'Union Coop - Al Warqa': {'label': 'Al Warqa', 'color': '#8b5cf6'},
    'Lulu Market': {'label': 'Lulu Market', 'color': '#f59e0b'},
}
venue_data = {k: [] for k in venues}

all_pcs = []
for pc in devices:
    name = str(pc.get('1', '') or '')
    location = str(pc.get('3', '') or '').upper()
    screen_name = str(pc.get('16', '') or '')
    tag = str(pc.get('901', '') or '')
    data_str = str(pc.get('76670', '0 %') or '0 %')
    is_online = GREEN_EMOJI in str(pc.get('31', ''))
    try:
        data_val = float(data_str.replace('%', '').replace(',', '.').strip())
    except:
        data_val = 0.0
    p = {'name': name, 'sn': screen_name, 'tag': tag, 'data': data_str.strip(), 'dv': data_val, 'online': is_online}
    all_pcs.append(p)
    if 'UMM' in location and 'SUQEIM' in location:
        venue_data['Union Coop - Umm Suqeim'].append(p)
    elif 'WARQA' in location:
        venue_data['Union Coop - Al Warqa'].append(p)
    elif 'LULU' in location:
        venue_data['Lulu Market'].append(p)

now = (datetime.datetime.utcnow() + datetime.timedelta(hours=4)).strftime('%Y-%m-%d %H:%M GST')

total = len(all_pcs)
online = sum(1 for p in all_pcs if p['online'])
offline = total - online

# Separate offline PCs
offline_pcs = [p for p in all_pcs if not p['online']]

# PCs over thresholds
over80 = [p for p in all_pcs if p['dv'] > 80]
over60 = [p for p in all_pcs if p['dv'] > 60]
over30 = [p for p in all_pcs if p['dv'] > 30]

# ── HTML ──────────────────────────────────────────────────────
html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NSOC Status · Operations</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#080a0e;color:#e0e2e6;font-size:13px;height:100vh;display:flex;flex-direction:column;overflow:hidden}}

.header{{background:linear-gradient(135deg,#111318,#1c212d);padding:8px 20px;border-bottom:1px solid #1e293b;display:flex;align-items:center;justify-content:space-between;flex-shrink:0}}
.header h1{{font-size:15px;font-weight:700;color:#f1f5f9}}
.header h1 span{{color:#64748b;font-weight:400}}
.header .sub{{color:#5b677b;font-size:10px}}

.summary{{display:flex;gap:6px;padding:6px 20px;background:#0d0f14;border-bottom:1px solid #161b22;flex-shrink:0;flex-wrap:wrap}}
.sc{{background:#141820;border-radius:6px;padding:5px 12px;min-width:80px;flex:1;text-align:center;border:1px solid #1c2330}}
.sc .l{{font-size:9px;text-transform:uppercase;color:#5b677b;letter-spacing:.4px}}
.sc .v{{font-size:16px;font-weight:700;margin-top:1px}}

.body{{flex:1;padding:8px 20px;overflow-y:auto;display:flex;flex-direction:column;gap:10px;min-height:0}}

.section-title{{font-size:12px;font-weight:600;color:#94a3b8;text-transform:uppercase;letter-spacing:.6px;flex-shrink:0}}

/* ── Offline cards ── */
.offline-row{{display:flex;gap:6px;flex-wrap:wrap}}
.off-card{{background:linear-gradient(135deg,rgba(239,68,68,0.1),rgba(239,68,68,0.04));border:1px solid rgba(239,68,68,0.2);border-radius:8px;padding:8px 12px;min-width:180px;flex:1}}
.off-card .oc-hdr{{display:flex;align-items:center;gap:6px;margin-bottom:3px}}
.off-card .oc-hdr .oc-nm{{font-weight:600;font-size:11px;font-family:'SF Mono',Consolas,monospace;flex:1;overflow:hidden;text-overflow:ellipsis;color:#ef4444}}
.off-card .oc-sn{{font-size:9px;color:#6b7c93;overflow:hidden;text-overflow:ellipsis}}

.offline-empty{{display:flex;align-items:center;justify-content:center;flex:1;color:#22c55e;font-size:14px;gap:8px;background:rgba(34,197,94,0.05);border:1px solid rgba(34,197,94,0.15);border-radius:8px;padding:12px}}

/* ── Venue cards ── */
.venue-row{{display:flex;gap:8px;flex-wrap:wrap}}
.vc{{flex:1;min-width:180px;background:#0f1117;border:1px solid #1c2330;border-radius:8px;overflow:hidden}}
.vc-hdr{{display:flex;align-items:center;justify-content:space-between;padding:5px 10px;background:#141820;border-bottom:1px solid #1c2330}}
.vc-hdr h3{{font-size:11px;font-weight:600}}
.vc-hdr .vb{{font-size:9px;color:#64748b}}
.vc-body{{padding:4px 10px 8px}}
.vc-stat{{display:flex;gap:10px;font-size:11px;margin-bottom:4px}}
.vc-stat span{{display:flex;align-items:center;gap:3px}}
.vc-dot{{width:7px;height:7px;border-radius:50%;display:inline-block}}

.vc-alert{{font-size:9px;color:#64748b;display:flex;align-items:center;gap:4px;margin-top:2px}}
.vc-alert .ad{{width:5px;height:5px;border-radius:50%;background:#ef4444;display:inline-block}}

/* ── Data alert table ── */
.alert-table{{width:100%;border-collapse:collapse;font-size:10px}}
.alert-table th{{text-align:left;padding:3px 6px;background:#0d0f14;color:#5b677b;font-weight:500;font-size:8px;text-transform:uppercase;letter-spacing:.3px;border-bottom:1px solid #1c2330;position:sticky;top:0}}
.alert-table td{{padding:2px 6px;border-bottom:1px solid #11151c;white-space:nowrap}}
.alert-table .nm{{font-weight:500;font-family:'SF Mono',Consolas,monospace;font-size:9px}}
.alert-table .sn{{color:#6b7c93;font-size:9px}}
.alert-table .tr{{text-align:right}}
.alert-table .r80{{background:rgba(239,68,68,0.1)}}
.alert-table .r60{{background:rgba(249,115,22,0.08)}}
.db{{display:inline-block;height:4px;border-radius:2px;min-width:2px}}

.footer{{text-align:center;padding:4px;color:#3b4557;font-size:9px;border-top:1px solid #131820;flex-shrink:0}}

::-webkit-scrollbar{{width:4px}}
::-webkit-scrollbar-track{{background:transparent}}
::-webkit-scrollbar-thumb{{background:#1c2330;border-radius:2px}}
</style></head>
<body>'''

html += f'''<div class="header">
<div><h1>NSOC <span>Operations</span></h1></div>
<div class="sub">{now}</div>
</div>'''

html += f'''<div class="summary">
<div class="sc"><div class="l">Total PCs</div><div class="v">{total}</div></div>
<div class="sc"><div class="l">Online</div><div class="v" style="color:#4ade80">{online}</div></div>
<div class="sc"><div class="l">Offline</div><div class="v" style="color:#ef4444">{offline}</div></div>
<div class="sc"><div class="l">Data >80%</div><div class="v" style="color:#ef4444">{len(over80)}</div></div>
<div class="sc"><div class="l">Data >60%</div><div class="v" style="color:#f97316">{len(over60)}</div></div>
<div class="sc"><div class="l">Data >30%</div><div class="v" style="color:#eab308">{len(over30)}</div></div>
</div>'''

html += '<div class="body">'

# ── Offline section ──
html += '<div class="section-title">⚠️ Offline PCs</div>'
if offline_pcs:
    html += '<div class="offline-row">'
    for p in offline_pcs[:20]:
        loc = ''
        for k, v in venue_data.items():
            if p in v:
                loc = venues[k]['label']
                break
        html += f'''<div class="off-card">
<div class="oc-hdr"><span class="oc-nm">{p['name']}</span></div>
<div class="oc-sn">{p['sn'][:50]} · {loc}</div>
</div>'''
    html += '</div>'
    if len(offline_pcs) > 20:
        html += f'<div style="font-size:10px;color:#5b677b;text-align:center">...and {len(offline_pcs)-20} more</div>'
else:
    html += '<div class="offline-empty">✓ All PCs online — nothing to report</div>'

# ── Venue breakdown ──
html += '<div class="section-title" style="margin-top:6px">📍 Venues</div>'
html += '<div class="venue-row">'
for key, info in venues.items():
    pcs = venue_data[key]
    v_online = sum(1 for p in pcs if p['online'])
    v_total = len(pcs)
    v_offline = v_total - v_online
    v_over60 = sum(1 for p in pcs if p['dv'] > 60)
    html += f'''<div class="vc" style="border-top:2px solid {info['color']}">
<div class="vc-hdr"><h3 style="color:{info['color']}">{info['label']}</h3><span class="vb">{v_total} PCs</span></div>
<div class="vc-body">
<div class="vc-stat">
<span><span class="vc-dot" style="background:#4ade80"></span>{v_online} online</span>
<span><span class="vc-dot" style="background:#ef4444"></span>{v_offline} offline</span>
</div>
{f'<div class="vc-alert"><span class="ad"></span>{v_over60} >60% data</div>' if v_over60 > 0 else ''}
</div>
</div>'''
html += '</div>'

# ── High data consumers ──
high_data = [p for p in sorted(all_pcs, key=lambda x: -x['dv']) if p['dv'] > 60]
if high_data:
    html += f'<div class="section-title" style="margin-top:6px">🔥 High Data Consumption (>60%)</div>'
    html += '''<table class="alert-table"><thead><tr><th>Name</th><th>Screen Name</th><th style="width:56px;text-align:right">Data</th></tr></thead><tbody>'''
    for p in high_data:
        cls = ' r80' if p['dv'] > 80 else ' r60'
        dc = '#ef4444' if p['dv'] > 80 else '#f97316'
        bw = max(2, min(p['dv'], 100))
        html += f'''<tr class="{cls}"><td class="nm">{p['name']}</td><td class="sn">{p['sn'][:50]}</td><td class="tr"><div style="display:inline-flex;align-items:center;gap:2px;font-size:9px"><span class="db" style="width:{bw}px;background:{dc}"></span>{p['data']}</div></td></tr>'''
    html += '</tbody></table>'

html += f'''</div>
<div class="footer">NSOC Status · Updated {now} · Data via NSOC</div>
</body>
</html>'''

# ── Write ──
script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()
out_path = os.path.join(script_dir, '..', 'rmstatus-push')
if not os.path.exists(out_path):
    out_path = os.getcwd()
os.makedirs(out_path, exist_ok=True)
out_file = os.path.join(out_path, 'nsoc-status.html')
with open(out_file, 'w') as f:
    f.write(html)
print(f"✅ {out_file} ({len(html)} bytes)")
print(f"   Total: {total} | Online: {online} | Offline: {offline} | >60%: {len(high_data)}")
