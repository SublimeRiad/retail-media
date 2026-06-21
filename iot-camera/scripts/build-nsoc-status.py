#!/usr/bin/env python3
"""Build nsoc-status.html — 4 stats, 2 maps, 2 offline tables, data gauge"""
import json, os, urllib.request, datetime, urllib.parse, sys

def _load_creds():
    env = {}
    for p in ['~/.openclaw/workspace/.nsoc_creds', '~/.nsoc_creds']:
        f = os.path.expanduser(p)
        if os.path.exists(f):
            with open(f) as fh:
                for line in fh:
                    line = line.strip()
                    if line.startswith('export '): line = line[7:]
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

url = f"{glpi_url}/search/Computer?expand_dropdowns=true&withplugins=true&range=0-2000"
req2 = urllib.request.Request(url, headers={"Session-Token": session_token, "App-Token": app_token})
resp2 = urllib.request.urlopen(req2).read()
data = json.loads(resp2)
all_devices = data.get('data', [])

GREEN = '🟢'
total_all = data.get('totalcount', 0)
online_all = sum(1 for pc in all_devices if GREEN in str(pc.get('31', '')))
offline_all = total_all - online_all

# Fetch locations for map coordinates
url_locs = f"{glpi_url}/Location?range=0-2000"
req_locs = urllib.request.Request(url_locs, headers={"Session-Token": session_token, "App-Token": app_token})
resp_locs = urllib.request.urlopen(req_locs).read()
locs = json.loads(resp_locs)

loc_coords = {}
for l in locs:
    name = str(l.get('completename', '') or l.get('name', '') or '').strip()
    lat = l.get('latitude') or ''
    lng = l.get('longitude') or ''
    if name and lat and lng:
        try: loc_coords[name.upper()] = (float(lat), float(lng))
        except: pass
# Fallbacks
for k, v in {'ENOC':(25.25,55.30),'ENOC SHARJAH':(25.33,55.41),'ENOC ABU DHABI':(24.48,54.37)}.items():
    loc_coords[k] = v

# Parse PCs
all_pcs = []
tag_groups = {}
for pc in all_devices:
    name = str(pc.get('1', '') or '')
    screen_name = str(pc.get('16', '') or '')
    tag = str(pc.get('901', '') or '')
    data_str = str(pc.get('76670', '0 %') or '0 %')
    is_online = GREEN in str(pc.get('31', ''))
    try: data_val = float(data_str.replace('%', '').replace(',', '.').strip())
    except: data_val = 0.0
    phone = str(pc.get('76666', '') or '').strip()
    loc = str(pc.get('3', '') or '')
    raw_tag = pc.get('10500', 'Undefined')
    gn = str(raw_tag).strip() if raw_tag and str(raw_tag).strip() else 'Undefined'
    if isinstance(raw_tag, list): gn = ' + '.join(raw_tag)

    # Coordinates
    lat_lng = loc_coords.get(loc.upper(), (0,0))
    
    p = {'name': name, 'sn': screen_name, 'tag': tag, 'data': data_str.strip(),
         'dv': data_val, 'online': is_online, 'loc': loc, 'group': gn,
         'lat': lat_lng[0], 'lng': lat_lng[1], 'phone': phone}
    all_pcs.append(p)
    tag_groups.setdefault(gn, []).append(p)

group_order = sorted(tag_groups.keys(), key=lambda g: -len(tag_groups[g]))
tag_colors = {'Malls':('#3b82f6','#2563eb'),'Convenience Stores':('#f59e0b','#d97706'),
    'Metro':('#8b5cf6','#7c3aed'),'In-Store':('#22c55e','#16a34a'),'Outdoor':('#f97316','#ea580c'),
    'Undefined':('#64748b','#475569')}

now = (datetime.datetime.utcnow() + datetime.timedelta(hours=4)).strftime('%Y-%m-%d %H:%M GST')
alert_pcs = sorted([p for p in all_pcs if p['dv'] > 60], key=lambda x: -x['dv'])
alert_count = len(alert_pcs)

# Offline PCs per city
offline_pcs = [p for p in all_pcs if not p['online']]
dubai_off = sorted([p for p in offline_pcs if p['lat'] > 25.1], key=lambda x: x['loc'])
abu_off = sorted([p for p in offline_pcs if p['lat'] > 24.0 and p['lat'] <= 25.1], key=lambda x: x['loc'])

def fmt_phone(phone):
    if not phone or phone == 'Not Found': return ''
    p = phone.replace(' ','').replace('-','').replace('+','')
    if p.startswith('971') and len(p) >= 10:
        return '0' + p[3:]
    return phone
cons_top = [{'label': f"{fmt_phone(p['phone'])+' - ' if fmt_phone(p['phone']) else ''}{p['name'][:20]} [{p['loc'][:15]}]", 'value': round(p['dv']/100,2)} for p in alert_pcs]
def off_table_rows_rm(pcs):
    rows = ''
    for i, p in enumerate(pcs):
        ic = '<span class="ic ko">✗</span>'
        rows += f'<tr><td>{ic}</td><td class="otnm">{p["name"][:25]}</td><td class="otsn">{p["sn"]}</td><td class="otloc">{p["loc"][:20]}</td><td class="otpid">{p["tag"][:15]}</td></tr>'
    return rows

all_off_rows_rm = off_table_rows_rm(offline_pcs)

# Alert PCs HTML (Retail-Media-Nsoc-Players style)
alert_cards = ''
for i, p in enumerate(alert_pcs):
    dcc = '#ef4444' if p['dv'] > 80 else '#f97316'
    alert_cards += f'''<div style="background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.15);border-radius:5px;padding:4px 8px;flex-shrink:0">
<div style="display:flex;align-items:center;gap:4px">
<span style="font-weight:700;color:#ef4444;font-size:10px">#{i+1}</span>
<span style="font-weight:600;font-size:10px;font-family:'SF Mono',Consolas,monospace;flex:1;overflow:hidden;text-overflow:ellipsis">{p['name']}</span>
<span style="font-weight:700;font-size:11px;color:{dcc};margin-left:auto">{p['data']}</span>
</div>
<div style="display:flex;gap:8px;font-size:8px;color:#6b7c93;margin-top:1px">
<span>ID: {p['tag']}</span>
<span>{p['loc'][:25]}</span>
</div>
</div>'''

# Tag summary for 4th stat card
tag_summary = ' · '.join(f'<span style="font-size:9px;color:{tag_colors.get(g,("#94a3b8","#94a3b8"))[0]}">{g}: {len(tag_groups[g])}</span>' for g in group_order[:5])

# ── HTML ──
html = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="600">
<title>NSOC Status</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{height:100%;overflow:hidden}
body{background:#0b1120;color:#e2e8f0;font-family:'Inter',-apple-system,sans-serif;font-size:clamp(12px,1.1vw,16px)}
.d{flex:1;display:flex;flex-direction:column;padding:clamp(6px,0.8vh,12px) clamp(10px,1.2vw,18px);gap:clamp(3px,0.4vh,8px);max-width:1920px;margin:0 auto;width:100%;height:100vh}
.hd{display:flex;align-items:center;gap:clamp(8px,1vw,14px);padding:clamp(4px,0.6vh,10px) clamp(10px,1.2vw,18px);background:#111827;border-radius:8px;border:1px solid #1f2b3e;flex-shrink:0}
.hd .l{width:30px;height:30px;border-radius:6px;background:linear-gradient(135deg,#38bdf8,#a78bfa);display:flex;flex-direction:column;font-weight:800;font-size:12px;color:#fff;flex-shrink:0}
.hd h1{font-size:clamp(13px,1.4vw,18px);font-weight:700;color:#e2e8f0}
.hd .sub{font-size:clamp(9px,0.8vw,12px);color:#64748b;margin-left:auto}
.st{display:grid;grid-template-columns:repeat(4,1fr);gap:clamp(3px,0.4vw,8px);flex-shrink:0}
.sc{background:#111827;border-radius:6px;padding:clamp(5px,0.8vh,12px) clamp(8px,1vw,14px);border:1px solid #1f2b3e;position:relative;overflow:hidden}
.sc::before{content:'';position:absolute;top:0;left:0;right:0;height:2px}
.sc-r::before{background:#ef4444}.sc-g::before{background:#22c55e}.sc-b::before{background:#3b82f6}.sc-p::before{background:#a78bfa}
.sc .l{font-size:clamp(8px,0.7vw,10px);font-weight:500;text-transform:uppercase;letter-spacing:.4px;color:#64748b;margin-bottom:1px}
.sc .v{font-size:clamp(18px,2.2vw,28px);font-weight:700;letter-spacing:-1px;line-height:1.1}
.sc-r .v{color:#ef4444}.sc-g .v{color:#22c55e}.sc-b .v{color:#3b82f6}.sc-p .v{color:#a78bfa}
.sc .m{font-size:clamp(8px,0.6vw,10px);color:#64748b;margin-top:1px}
.sc .m .s{font-size:clamp(10px,1vw,14px)}
.sc .ts{margin-top:3px;display:flex;gap:4px;flex-wrap:wrap}
.maps-row{display:flex;gap:clamp(3px,0.4vw,8px);flex-shrink:0;height:clamp(250px,35vh,500px)}
.mp{flex:1;display:flex;flex-direction:column;background:#111827;border-radius:6px;border:1px solid #1f2b3e;overflow:hidden}
.mp .ph{padding:clamp(2px,0.3vh,4px) clamp(6px,0.8vw,10px);border-bottom:1px solid #1f2b3e;flex-shrink:0}
.mp .ph h3{font-size:clamp(8px,0.6vw,10px);font-weight:600;color:#94a3b8;text-transform:uppercase;letter-spacing:.3px}
.mp .mc{flex:1;min-height:0;width:100%}
.mp .leaflet-container{background:#0b1120}
.leaflet-tooltip.tt-dark{background:#111827;color:#e2e8f0;border:1px solid #1f2b3e;border-radius:4px;padding:3px 6px;font-size:10px;font-family:Inter,sans-serif}
.mid-row{display:flex;gap:clamp(3px,0.4vw,8px);flex:1;min-height:0}
.mid-row .col{flex:1;display:flex;flex-direction:column;min-width:0}
.pa{background:#111827;border-radius:6px;border:1px solid #1f2b3e;display:flex;flex-direction:column;overflow:hidden;flex:1}
.pa .ph{padding:clamp(2px,0.3vh,4px) clamp(6px,0.8vw,10px);border-bottom:1px solid #1f2b3e;flex-shrink:0}
.pa .ph h3{font-size:clamp(8px,0.6vw,10px);font-weight:600;color:#94a3b8;text-transform:uppercase;letter-spacing:.3px}
.pa .pb{flex:1;overflow-y:auto;min-height:0}
.ot{width:100%;border-collapse:collapse;table-layout:auto;font-size:9px}
.ot th{text-align:left;padding:2px 4px;background:#0d0f14;color:#5b677b;font-weight:500;font-size:7px;text-transform:uppercase;border-bottom:1px solid #1f2b3e;position:sticky;top:0}
.ot td{padding:2px 4px;border-bottom:1px solid rgba(255,255,255,.03);white-space:nowrap}
.otsn{font-family:'SF Mono',Consolas,monospace;font-size:8px}
.otpid{color:#6b7c93;font-size:7px}
.otloc{color:#5b677b;font-size:7px;max-width:70px;overflow:hidden;text-overflow:ellipsis}
.otnm{font-weight:500;font-family:'SF Mono',Consolas,monospace;font-size:8px;max-width:80px;overflow:hidden;text-overflow:ellipsis}
.ic{display:inline-flex;flex-direction:column;width:12px;height:12px;border-radius:50%;font-size:6px;font-weight:700;flex-shrink:0;background:#450a0a;color:#ef4444;border:1px solid #7f1d1d}
.r60 td{background:rgba(249,115,22,0.06)}
.r80 td{background:rgba(239,68,68,0.1)}
.gr{display:flex;align-items:center;gap:4px}
.gr .lb{font-size:9px;color:#94a3b8;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}
.gr .tk{flex:2;height:8px;background:#1a2332;border-radius:6px;overflow:hidden;flex-shrink:0}
.gr .fl{height:100%;border-radius:6px;transition:width .6s;background:linear-gradient(90deg,#3b82f6,#38bdf8)}
.gr .fl.o{background:linear-gradient(90deg,#f59e0b,#f97316)}
.gr .fl.r{background:linear-gradient(90deg,#ef4444,#dc2626)}
.gr .pc{min-width:28px;text-align:right;font-size:clamp(7px,0.5vw,9px);font-weight:600;color:#64748b;flex-shrink:0}
.footer{text-align:center;padding:3px;color:#3b4557;font-size:8px;border-top:1px solid #131820;flex-shrink:0}
</style></head>
<body>
<div class="d">
  <div class="hd">
    <div class="l">N</div>
    <h1>NSOC Status</h1>
    <div style="margin-left:10px;background:rgba(239,68,68,0.15);color:#ef4444;font-weight:700;font-size:clamp(10px,0.9vw,13px);padding:2px 8px;border-radius:4px;white-space:nowrap">''' + str(alert_count) + ''' >60%</div>
    <div class="sub">''' + now + '''</div>
  </div>
  <div class="st">
    <div class="sc sc-r"><div class="l">Offline</div><div class="v">''' + str(offline_all) + '''</div><div class="m">Computers</div></div>
    <div class="sc sc-g"><div class="l">Online</div><div class="v">''' + str(online_all) + '''</div><div class="m">Computers</div></div>
    <div class="sc sc-b"><div class="l">Total</div><div class="v">''' + str(total_all) + '''</div><div class="m">Devices</div></div>
    <div class="sc sc-p"><div class="l">By Tag</div><div class="v" style="font-size:clamp(11px,1vw,14px);letter-spacing:0">''' + str(len(group_order)) + '''</div><div class="m ts">''' + tag_summary + '''</div></div>
  </div>
  <div class="maps-row">
    <div class="mp"><div class="ph"><h3>Dubai</h3></div><div id="dMap" class="mc"></div></div>
    <div class="mp"><div class="ph"><h3>Abu Dhabi</h3></div><div id="aMap" class="mc"></div></div>
  </div>
  <div class="mid-row">
    <div class="col" style="flex:1.2">
      <div class="pa" style="border-top:2px solid #ef4444"><div class="ph" style="background:linear-gradient(90deg,rgba(239,68,68,0.1),transparent)"><h3 style="color:#ef4444">Offline PCs (''' + str(len(offline_pcs)) + ''')</h3></div><div class="pb"><table class="ot"><thead><tr><th style="width:16px">S</th><th>Name</th><th>Screen Name</th><th>Location</th><th style="width:40px">ID</th></tr></thead><tbody>''' + all_off_rows_rm + '''</tbody></table></div></div>
    </div>
    <div class="col">
      <div class="pa" style="border-top:2px solid #ef4444;flex:1"><div class="ph" style="background:linear-gradient(90deg,rgba(239,68,68,0.1),transparent)"><h3 style="color:#ef4444">Data >60% (''' + str(alert_count) + ''')</h3></div><div class="pb" style="display:flex;flex-direction:column;gap:3px;padding:3px 6px;overflow-y:auto">''' + alert_cards + '''<div id="dataGauge" style="margin-top:auto;padding-top:4px"></div></div></div>
    </div>
  </div>
  </div>
  <div class="footer">NSOC Status · Updated ''' + now + ''' · Data via NSOC</div>
</div>
<script>
const CONS = ''' + json.dumps(cons_top) + ''';
function renderGauge(items) {
  const el = document.getElementById('dataGauge');
  if(!items||!items.length){el.innerHTML='<div style=\"color:#64748b;font-size:11px;text-align:center;padding:8px\">No PCs exceed 60%</div>';return;}
  el.innerHTML = items.map(d => {
    const cls = d.value > 0.8 ? 'r' : d.value > 0.6 ? 'o' : '';
    return '<div class=\"gr\"><span class=\"lb\">'+d.label+'</span><div class=\"tk\"><div class=\"fl '+cls+'\" style=\"width:'+(d.value*100).toFixed(0)+'%\"></div></div><span class=\"pc\">'+(d.value*100).toFixed(0)+'%</span></div>';
  }).join('');
}
renderGauge(CONS);
function initMaps(){
  window.dMap = L.map('dMap',{center:[25.2,55.3],zoom:9,layers:[L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',{subdomains:'abcd',maxZoom:19})],zoomControl:false,attributionControl:false});
  window.aMap = L.map('aMap',{center:[24.45,54.35],zoom:9,layers:[L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',{subdomains:'abcd',maxZoom:19})],zoomControl:false,attributionControl:false});
}
const PCS = ''' + json.dumps([{'n':p['name'],'lat':p['lat'],'lng':p['lng'],'sn':p['sn'],'loc':p['loc']} for p in all_pcs if not p['online'] and p['lat'] and p['lng']]) + ''';
function loadMaps(){
  setTimeout(function(){
    window.dMap.invalidateSize(); window.aMap.invalidateSize();
    PCS.filter(p=>p.lat>25.1).forEach(p=>{L.circleMarker([p.lat,p.lng],{radius:4,fillColor:'#ef4444',color:'#ff6666',weight:2,opacity:1,fillOpacity:0.7}).addTo(window.dMap).bindTooltip('<b>'+p.n+'</b><br>'+p.loc,{direction:'top',className:'tt-dark'});});
    PCS.filter(p=>p.lat>24.0&&p.lat<=25.1).forEach(p=>{L.circleMarker([p.lat,p.lng],{radius:4,fillColor:'#ef4444',color:'#ff6666',weight:2,opacity:1,fillOpacity:0.7}).addTo(window.aMap).bindTooltip('<b>'+p.n+'</b><br>'+p.loc,{direction:'top',className:'tt-dark'});});
  }, 300);
}
initMaps(); loadMaps();
setTimeout(function(){var t=document.querySelector(".pa .pb");if(t){var s=1;setInterval(function(){t.scrollTop+=s;if(t.scrollTop>=t.scrollHeight-t.clientHeight){t.scrollTop=0}},80)}},1000);
</script>
</body>
</html>'''

script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()
out_path = os.path.join(script_dir, '..', 'rmstatus-push')
if not os.path.exists(out_path):
    out_path = os.getcwd()
os.makedirs(out_path, exist_ok=True)
with open(os.path.join(out_path, 'nsoc-status.html'), 'w') as f:
    f.write(html)
print(f"✅ Done ({len(html)} bytes) | Total: {total_all} | Alert >60%: {alert_count}")
