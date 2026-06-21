#!/usr/bin/env python3
"""Build Retail Media Nsoc Players Dashboard"""
import json, os, urllib.request, datetime

# ── Auth (env vars first, then creds file) ───────────────────
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

venues_keys = [
    ('Union Coop - Umm Suqeim', 'Umm Suqeim', '#3b82f6', '#2563eb'),
    ('Union Coop - Al Warqa', 'Al Warqa', '#8b5cf6', '#7c3aed'),
    ('Lulu Market', 'Lulu Market', '#f59e0b', '#d97706'),
]

venue_data = {}
for k, *_ in venues_keys:
    venue_data[k] = []

for pc in devices:
    name = str(pc.get('1', '') or '')
    location = str(pc.get('3', '') or '').upper()
    status_str = str(pc.get('31', '') or '')
    screen_name = str(pc.get('16', '') or '')
    tag = str(pc.get('901', '') or '')
    data_str = str(pc.get('76670', '0 %') or '0 %')
    is_online = GREEN_EMOJI in status_str
    try:
        data_val = float(data_str.replace('%', '').replace(',', '.').strip())
    except:
        data_val = 0.0
    pc_info = {
        'name': name, 'screen_name': screen_name, 'tag': tag,
        'data_str': data_str.strip(), 'data_val': data_val, 'online': is_online,
    }
    if 'UMM' in location and 'SUQEIM' in location:
        venue_data['Union Coop - Umm Suqeim'].append(pc_info)
    elif 'WARQA' in location:
        venue_data['Union Coop - Al Warqa'].append(pc_info)
    elif 'LULU' in location:
        venue_data['Lulu Market'].append(pc_info)

now_dubai = (datetime.datetime.utcnow() + datetime.timedelta(hours=4)).strftime('%Y-%m-%d %H:%M GST')

total_pcs = sum(len(v) for _, v in venue_data.items())
total_online = sum(sum(1 for p in v if p['online']) for _, v in venue_data.items())
total_offline = total_pcs - total_online

all_pcs = []
for v in venue_data.values():
    all_pcs.extend(v)
all_pcs.sort(key=lambda p: p['data_val'], reverse=True)

alert_pcs = [p for p in all_pcs if p['data_val'] > 60]
alert_count = len(alert_pcs)

def dc(val):
    if val > 80: return '#ef4444'
    elif val > 60: return '#f97316'
    elif val > 30: return '#eab308'
    return '#22c55e'

# ── HTML ──────────────────────────────────────────────────────
html = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="600">
<title>Retail Media Nsoc Players</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0a0c10;color:#e0e2e6;font-size:13px;height:100vh;display:flex;flex-direction:column;overflow:hidden}

.header{background:linear-gradient(135deg,#111318,#1c212d);padding:7px 20px;border-bottom:1px solid #1e293b;display:flex;align-items:center;justify-content:space-between;flex-shrink:0}
.header h1{font-size:14px;font-weight:700;background:linear-gradient(90deg,#3b82f6,#8b5cf6);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.header .sub{color:#5b677b;font-size:9px}

/* ── big donuts ── */
.donut-big-row{display:flex;gap:20px;padding:12px 28px;background:#0d0f14;border-bottom:1px solid #161b22;flex-shrink:0;flex-wrap:wrap;justify-content:center;align-items:stretch}
.donut-group{display:flex;flex-direction:column;gap:6px;flex:2;min-width:360px;background:linear-gradient(135deg,rgba(59,130,246,0.08),rgba(139,92,246,0.04));border:1px solid rgba(59,130,246,0.15);border-radius:16px;padding:12px 16px;box-shadow:0 2px 16px rgba(59,130,246,0.06)}
.donut-group-label{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.8px;color:#3b82f6;padding:0 4px}
.donut-group-inner{display:flex;gap:20px;flex:1;min-width:0}
.donut-big-card{display:flex;flex-direction:column;align-items:center;gap:8px;background:linear-gradient(145deg,#1a1e2b,#11131f);border:1px solid #2a3348;border-radius:16px;padding:18px 28px;min-width:200px;flex:1;box-shadow:0 4px 24px rgba(0,0,0,0.3),inset 0 1px 0 rgba(255,255,255,0.04)}
.donut-big-card .dlbl{font-size:15px;font-weight:600;letter-spacing:.3px}
.donut-big{width:148px;height:148px;border-radius:50%;position:relative;flex-shrink:0;box-shadow:0 0 20px rgba(34,197,94,0.2),inset 0 0 8px rgba(255,255,255,0.03)}
.donut-big-inner{position:absolute;inset:14px;border-radius:50%;background:radial-gradient(circle at 35% 35%,#1c2330,#0f1117);display:flex;flex-direction:column;align-items:center;justify-content:center;border:1px solid rgba(255,255,255,0.04)}
.donut-big-num{font-size:36px;font-weight:800;line-height:1;background:linear-gradient(180deg,#e8eaed 60%,#94a3b8);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.donut-big-label{font-size:11px;color:#5b677b;margin-top:2px}
.donut-big-stats{display:flex;gap:20px;font-size:14px;padding:4px 16px;background:rgba(0,0,0,0.2);border-radius:20px}
.st{display:flex;align-items:center;gap:5px}
.st .d{width:10px;height:10px;border-radius:50%;box-shadow:0 0 6px currentColor}
.st .n{font-family:'SF Mono',Consolas,monospace;font-weight:700;font-size:16px}
.donut-alert{font-size:11px;color:#64748b;display:flex;align-items:center;gap:4px}
.donut-alert .ad{width:6px;height:6px;border-radius:50%;background:#ef4444}

/* ── dash body ── */
.dash-body{flex:1;padding:6px 20px;display:flex;flex-direction:column;gap:6px;overflow:hidden;min-height:0}
.venue-row{display:flex;gap:8px;min-height:0;flex:1}
.venue-card{flex:1;min-width:0;background:#0f1117;border:1px solid #1c2330;border-radius:8px;display:flex;flex-direction:column;overflow:hidden;min-height:0}
.vc-header{display:flex;align-items:center;justify-content:space-between;padding:4px 8px;background:#141820;border-bottom:1px solid #1c2330;flex-shrink:0}
.vc-header h3{font-size:11px;font-weight:600}
.vc-header .badge{font-size:9px;color:#64748b}
.scroll-t{overflow-y:auto;flex:1;min-height:0}
.scroll-t::-webkit-scrollbar{width:4px}
.scroll-t::-webkit-scrollbar-track{background:transparent}
.scroll-t::-webkit-scrollbar-thumb{background:#1c2330;border-radius:2px}
.pc-t{width:100%;border-collapse:collapse;font-size:10px}
.pc-t th{text-align:left;padding:2px 6px;background:#0d0f14;color:#5b677b;font-weight:500;font-size:8px;text-transform:uppercase;letter-spacing:.3px;border-bottom:1px solid #1c2330}
.pc-t td{padding:2px 6px;border-bottom:1px solid #131820;white-space:nowrap}
.pc-t tr:hover td{background:#141820}
.pc-t .nm{font-weight:500;font-family:'SF Mono',Consolas,monospace;font-size:9px;max-width:90px;overflow:hidden;text-overflow:ellipsis}
.pc-t .sn{color:#6b7c93;font-size:9px;max-width:170px;overflow:hidden;text-overflow:ellipsis}
.pc-t .tg{color:#6b7c93;font-size:8px}
.pc-t .tr{text-align:right}
.pc-t .r60{background:linear-gradient(90deg,rgba(249,115,22,0.08),transparent)}
.pc-t .r80{background:linear-gradient(90deg,rgba(239,68,68,0.12),transparent)}
.dc{display:inline-flex;align-items:center;gap:2px;font-family:'SF Mono',Consolas,monospace;font-size:9px}
.db{display:inline-block;height:4px;border-radius:2px;min-width:2px}
.dc{display:inline-flex;align-items:center;gap:2px;font-family:'SF Mono',Consolas,monospace;font-size:9px}
.db{display:inline-block;height:4px;border-radius:2px;min-width:2px}
.ic{display:inline-flex;align-items:center;justify-content:center;width:12px;height:12px;border-radius:50%;font-size:6px;font-weight:700;flex-shrink:0}
.ic.ok{background:#052e16;color:#4ade80;border:1px solid #166534}
.ic.ko{background:#450a0a;color:#ef4444;border:1px solid #7f1d1d}





.footer{text-align:center;padding:4px;color:#3b4557;font-size:9px;border-top:1px solid #131820;flex-shrink:0}
</style></head>
<body>'''

html += f'''<div class="header">
<div><h1>Retail Media Nsoc Players</h1></div>
<div class="sub">{now_dubai}</div>
</div>'''

# ── Big donuts per venue (UnionCoop grouped) ──
def make_donut(key, label, color):
    pcs = venue_data[key]
    online = sum(1 for p in pcs if p['online'])
    total = len(pcs)
    offline = total - online
    pct = round((online / total) * 100) if total else 0
    bg = f'conic-gradient(#22c55e 0% {pct}%, #ef4444 {pct}% 100%)' if offline > 0 else 'conic-gradient(#22c55e 0% 100%)'
    v_alert = sum(1 for p in pcs if p['data_val'] > 60)
    alert_html = f'<div class="donut-alert"><span class="ad"></span>{v_alert} >60%</div>' if v_alert > 0 else ''
    return f'''<div class="donut-big-card">
<div class="dlbl" style="color:{color}">{label}</div>
<div class="donut-big" style="background:{bg}"><div class="donut-big-inner">
<div class="donut-big-num">{total}</div><div class="donut-big-label">PCs</div>
</div></div>
<div class="donut-big-stats">
<div class="st"><span class="d" style="background:#22c55e"></span><span class="n">{online}</span></div>
<div class="st"><span class="d" style="background:#ef4444"></span><span class="n">{offline}</span></div>
</div>
{alert_html}</div>'''

html += '<div class="donut-big-row">'
# UnionCoop group
html += '<div class="donut-group"><div class="donut-group-label">Union Coop</div><div class="donut-group-inner">'
html += make_donut('Union Coop - Umm Suqeim', 'Umm Suqeim', '#3b82f6')
html += make_donut('Union Coop - Al Warqa', 'Al Warqa', '#8b5cf6')
html += '</div></div>'
# Lulu Market standalone
html += make_donut('Lulu Market', 'Lulu Market', '#f59e0b')
html += '</div>'

# ── Body ──
html += '<div class="dash-body">'

# Alert — big red box with player IDs
if alert_pcs:
    alert_sorted = sorted(alert_pcs, key=lambda p: p['data_val'], reverse=True)
    alert_items = ''
    for i, p in enumerate(alert_sorted):
        tag = p['tag'] if p['tag'] else '—'
        loc_name = ''
        for key, label, *_ in venues_keys:
            if p in venue_data[key]:
                loc_name = label
                break
        dcc = dc(p['data_val'])
        alert_items += f'''<div style="background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.15);border-radius:5px;padding:6px 12px;min-width:200px;flex:1">
<div style="display:flex;align-items:center;gap:6px">
<span style="font-weight:700;color:#ef4444;font-size:12px">#{i+1}</span>
<span style="font-weight:600;font-size:12px;font-family:'SF Mono',Consolas,monospace">{p['name']}</span>
<span style="font-weight:700;font-size:14px;color:{dcc};margin-left:auto">{p['data_str'] if p['data_str'] else '0%'}</span>
</div>
<div style="display:flex;gap:10px;font-size:9px;color:#6b7c93;margin-top:1px">
<span>ID: {tag}</span>
<span>{loc_name}</span>
</div>
</div>'''
    html += f'<div style="background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.2);border-radius:6px;padding:8px 14px;flex-shrink:0;display:flex;flex-direction:column;gap:5px"><div style="display:flex;align-items:center;gap:6px"><span style="width:8px;height:8px;border-radius:50%;background:#ef4444;flex-shrink:0"></span><span style="font-weight:700;color:#ef4444;font-size:14px">{alert_count}</span><span style="font-size:11px;color:#94a3b8">PCs exceeding 60% data consumption</span></div><div style="display:flex;gap:6px;flex-wrap:wrap">{alert_items}</div></div>'

# Venue cards with tables
html += '<div class="venue-row">'
for key, label, color, accent in venues_keys:
    pcs = venue_data[key]
    online = sum(1 for p in pcs if p['online'])
    pcs_sorted = sorted(pcs, key=lambda p: p['data_val'], reverse=True)
    top5 = pcs_sorted[:5]
    
    rows = ''
    for p in pcs_sorted:
        ic = '<span class="ic ok">✓</span>' if p['online'] else '<span class="ic ko">✗</span>'
        dt = p['data_str'] or '0%'
        dcc = dc(p['data_val'])
        bw = max(2, min(p['data_val'], 100))
        sn = p['screen_name'] if p['screen_name'] else '—'
        tag = p['tag'] if p['tag'] else '—'
        cls = ' r80' if p['data_val'] > 80 else (' r60' if p['data_val'] > 60 else '')
        dt = p['data_str'] or '0%'
        dcc = dc(p['data_val'])
        bw = max(2, min(p['data_val'], 100))
        rows += f'''<tr class="{cls}"><td>{ic}</td><td class="sn" title="{sn}">{sn}</td><td class="tg">{tag}</td><td class="tr"><div class="dc"><span class="db" style="width:{bw}px;background:{dcc}"></span>{dt}</div></td></tr>'''
    
    html += f'''<div class="venue-card" style="border-top:2px solid {accent}">
<div class="vc-header"><h3 style="color:{color}">{label}</h3><span class="badge">{len(pcs)} PCs · {online} online</span></div>
<div class="scroll-t"><table class="pc-t"><thead><tr><th style="width:14px">S</th><th>Screen Name</th><th style="width:40px">Tag</th><th style="width:56px;text-align:right">Data</th></tr></thead><tbody>{rows}</tbody></table></div>
</div>'''
html += '</div>'



html += f'''</div>
<div class="footer">Retail Media Nsoc Players · Updated {now_dubai} · Data via NSOC</div>
<script>
(function(){{
 var scrollers = document.querySelectorAll('.scroll-t');
 if(scrollers.length >= 3){{
   var lulu = scrollers[2]; // 3rd scroll container = Lulu
   var scrollSpeed = 1; // px per tick
   var interval = 80; // ms
   var timer = null;
   var paused = false;
   function doScroll(){{
     if(!paused){{
       lulu.scrollTop += scrollSpeed;
       if(lulu.scrollTop >= lulu.scrollHeight - lulu.clientHeight){{
         lulu.scrollTop = 0;
       }}
     }}
     timer = setTimeout(doScroll, interval);
   }}
   lulu.addEventListener('mouseenter', function(){{ paused = true; }});
   lulu.addEventListener('mouseleave', function(){{ paused = false; }});
   doScroll();
 }}
}})();
</script>
</body>
</html>'''

# Use rmstatus-push if exists (local NUC), else cwd (GitHub Actions)
out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rmstatus-push')
if not os.path.exists(out_path):
    out_path = os.getcwd()
os.makedirs(out_path, exist_ok=True)
with open(os.path.join(out_path, 'Retail-Media-Nsoc-Players.html'), 'w') as f:
    f.write(html)
print(f"✅ Done ({len(html)} bytes) | {total_pcs} PCs | {alert_count} >60% | {now_dubai}")
