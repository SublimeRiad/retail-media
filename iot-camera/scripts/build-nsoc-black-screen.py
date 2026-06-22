#!/usr/bin/env python3
"""Build nsoc-black-screen.html — query Grafana API, embed live data.
Output: old layout with Chart.js charts, Leaflet maps, paginated table."""
import json, os, urllib.request, datetime, math

# ── Auth ───────────────────────────────────
token = os.environ.get('GRAFANA_TOKEN', '')
if not token:
    for path in ['~/.openclaw/workspace/.grafana_token', '~/.grafana_token']:
        f = os.path.expanduser(path)
        if os.path.exists(f):
            with open(f) as fh:
                token = fh.read().strip()
            break

if not token:
    print('⚠ GRAFANA_TOKEN not set, using embedded fallback')
    token = ''

GRAFANA_BASE = 'https://nsoc.aiootech.com/grafana'
DS_UID = 'afgjq2q0g0000c'

# ── Helpers ────────────────────────────────
def grafana_query(sql):
    if not token:
        return None
    req = urllib.request.Request(
        f'{GRAFANA_BASE}/api/ds/query',
        data=json.dumps({
            'queries': [{
                'refId': 'A',
                'datasource': {'type': 'mysql', 'uid': DS_UID},
                'rawSql': sql,
                'format': 'table',
                'rawQuery': True,
                'editorMode': 'code'
            }]
        }).encode(),
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    )
    resp = urllib.request.urlopen(req, timeout=30)
    data = json.loads(resp.read())
    frame = data['results']['A']['frames'][0]['data']['values']
    return frame  # list of columns

def safe_val(frame, row=0, col=0):
    try:
        return frame[col][row]
    except (IndexError, TypeError, KeyError):
        return 0

def safe_str(frame, row=0, col=0):
    try:
        return str(frame[col][row])
    except (IndexError, TypeError, KeyError):
        return '-'

def safe_float(frame, row=0, col=0):
    try:
        v = frame[col][row]
        return float(v) if v is not None else None
    except (IndexError, TypeError, KeyError, ValueError):
        return None

# ── Fetch data ─────────────────────────────
def fetch_all():
    print('[1] Querying black screen stats...')
    black_frame = grafana_query(
        "SELECT COUNT(DISTINCT fields.items_id) as total "
        "FROM glpi_plugin_fields_computerlivescreens fields "
        "WHERE fields.itemtype='Computer' "
        "AND JSON_VALID(fields.livescreenfield) "
        "AND CAST(JSON_EXTRACT(fields.livescreenfield, '$.metrics.black_ratio') AS DECIMAL(4,2)) >= 0.95"
    )
    black_total = safe_val(black_frame) if black_frame else 0

    print('[2] Querying monitored screens...')
    monitored_frame = grafana_query(
        "SELECT COUNT(*) as cnt "
        "FROM glpi_plugin_fields_computerlivescreens "
        "WHERE livescreenfield IS NOT NULL AND livescreenfield <> ''"
    )
    monitored = safe_val(monitored_frame) if monitored_frame else 0

    print('[3] Querying venues...')
    venues_frame = grafana_query(
        "SELECT COUNT(DISTINCT loc.completename) as venues "
        "FROM glpi_plugin_fields_computerlivescreens fields "
        "JOIN glpi_computers comp ON fields.items_id = comp.id "
        "LEFT JOIN glpi_locations loc ON comp.locations_id = loc.id "
        "WHERE fields.itemtype='Computer' "
        "AND JSON_VALID(fields.livescreenfield) "
        "AND CAST(JSON_EXTRACT(fields.livescreenfield, '$.metrics.black_ratio') AS DECIMAL(4,2)) >= 0.95 "
        "AND loc.completename IS NOT NULL"
    )
    venues = safe_val(venues_frame) if venues_frame else 0

    print('[4] Querying venue types...')
    types_frame = grafana_query(
        "SELECT COUNT(DISTINCT tags.name) as types "
        "FROM glpi_plugin_fields_computerlivescreens fields "
        "JOIN glpi_computers comp ON fields.items_id = comp.id "
        "LEFT JOIN glpi_plugin_tag_tagitems tag_items ON (comp.id = tag_items.items_id AND tag_items.itemtype='Computer') "
        "LEFT JOIN glpi_plugin_tag_tags tags ON tag_items.plugin_tag_tags_id = tags.id "
        "WHERE fields.itemtype='Computer' "
        "AND JSON_VALID(fields.livescreenfield) "
        "AND CAST(JSON_EXTRACT(fields.livescreenfield, '$.metrics.black_ratio') AS DECIMAL(4,2)) >= 0.95 "
        "AND tags.name IS NOT NULL"
    )
    venue_types = safe_val(types_frame) if types_frame else 0

    print('[5] Querying venues list...')
    venues_list_frame = grafana_query(
        "SELECT loc.completename AS venue, COUNT(DISTINCT fields.items_id) AS black_count "
        "FROM glpi_plugin_fields_computerlivescreens fields "
        "JOIN glpi_computers comp ON fields.items_id = comp.id "
        "LEFT JOIN glpi_locations loc ON comp.locations_id = loc.id "
        "WHERE fields.itemtype='Computer' "
        "AND JSON_VALID(fields.livescreenfield) "
        "AND CAST(JSON_EXTRACT(fields.livescreenfield, '$.metrics.black_ratio') AS DECIMAL(4,2)) >= 0.95 "
        "GROUP BY loc.completename ORDER BY black_count DESC LIMIT 15"
    )
    venues_list = []
    if venues_list_frame:
        names = venues_list_frame[0]
        counts = venues_list_frame[1]
        for i in range(len(names)):
            venues_list.append({'venue': str(names[i]), 'count': int(counts[i])})

    print('[6] Querying types list...')
    types_list_frame = grafana_query(
        "SELECT COALESCE(tags.name, 'Unknown') AS type, COUNT(DISTINCT fields.items_id) AS count "
        "FROM glpi_plugin_fields_computerlivescreens fields "
        "JOIN glpi_computers comp ON fields.items_id = comp.id "
        "LEFT JOIN glpi_plugin_tag_tagitems tag_items ON (comp.id = tag_items.items_id AND tag_items.itemtype='Computer') "
        "LEFT JOIN glpi_plugin_tag_tags tags ON tag_items.plugin_tag_tags_id = tags.id "
        "WHERE fields.itemtype='Computer' "
        "AND JSON_VALID(fields.livescreenfield) "
        "AND CAST(JSON_EXTRACT(fields.livescreenfield, '$.metrics.black_ratio') AS DECIMAL(4,2)) >= 0.95 "
        "AND tags.name IS NOT NULL "
        "GROUP BY tags.name ORDER BY count DESC"
    )
    types_list = []
    if types_list_frame:
        names = types_list_frame[0]
        counts = types_list_frame[1]
        for i in range(len(names)):
            types_list.append({'type': str(names[i]), 'count': int(counts[i])})

    print('[7] Querying PC list...')
    pcs_frame = grafana_query(
        "SELECT comp.name AS pc, COALESCE(loc.completename, '-') AS venue, "
        "COALESCE(tags.name, '-') AS type, "
        "CAST(JSON_EXTRACT(fields.livescreenfield, '$.metrics.black_ratio') AS DECIMAL(4,2)) AS ratio, "
        "COALESCE(agents.tag, '-') AS playerid, "
        "COALESCE(DATE_FORMAT(fields.date_mod, '%Y-%m-%d'), '-') AS last_check "
        "FROM glpi_plugin_fields_computerlivescreens fields "
        "JOIN glpi_computers comp ON fields.items_id = comp.id "
        "LEFT JOIN glpi_locations loc ON comp.locations_id = loc.id "
        "LEFT JOIN glpi_agents agents ON (comp.id = agents.items_id AND agents.itemtype='Computer') "
        "LEFT JOIN glpi_plugin_tag_tagitems tag_items ON (comp.id = tag_items.items_id AND tag_items.itemtype='Computer') "
        "LEFT JOIN glpi_plugin_tag_tags tags ON tag_items.plugin_tag_tags_id = tags.id "
        "WHERE fields.itemtype='Computer' "
        "AND JSON_VALID(fields.livescreenfield) "
        "AND CAST(JSON_EXTRACT(fields.livescreenfield, '$.metrics.black_ratio') AS DECIMAL(4,2)) >= 0.95 "
        "ORDER BY ratio DESC, fields.date_mod DESC"
    )
    pcs_list = []
    if pcs_frame and len(pcs_frame) >= 6:
        for i in range(len(pcs_frame[0])):
            pcs_list.append({
                'pc': safe_str(pcs_frame, i, 0),
                'venue': safe_str(pcs_frame, i, 1),
                'type': safe_str(pcs_frame, i, 2),
                'ratio': safe_val(pcs_frame, i, 3),
                'playerid': safe_str(pcs_frame, i, 4),
                'last_check': safe_str(pcs_frame, i, 5)
            })

    print('[8] Querying GPS coordinates for black PCs...')
    coords_frame = grafana_query(
        "SELECT comp.name AS pc, loc.latitude, loc.longitude "
        "FROM glpi_plugin_fields_computerlivescreens fields "
        "JOIN glpi_computers comp ON fields.items_id = comp.id "
        "JOIN glpi_locations loc ON comp.locations_id = loc.id "
        "WHERE fields.itemtype='Computer' "
        "AND JSON_VALID(fields.livescreenfield) "
        "AND CAST(JSON_EXTRACT(fields.livescreenfield, '$.metrics.black_ratio') AS DECIMAL(4,2)) >= 0.95 "
        "AND loc.latitude IS NOT NULL AND loc.latitude <> 0 "
        "AND loc.longitude IS NOT NULL AND loc.longitude <> 0"
    )
    coords_list = []
    if coords_frame and len(coords_frame) >= 3:
        for i in range(len(coords_frame[0])):
            lat = safe_float(coords_frame, i, 1)
            lng = safe_float(coords_frame, i, 2)
            if lat and lng:
                coords_list.append({
                    'pc': safe_str(coords_frame, i, 0),
                    'lat': lat,
                    'lng': lng
                })

    use_live = black_frame is not None

    return {
        'stats': {
            'blackTotal': black_total,
            'monitored': monitored,
            'venues': venues,
            'venueTypes': venue_types
        },
        'venues': venues_list,
        'types': types_list,
        'pcs': pcs_list,
        'coords': coords_list,
        'live': use_live
    }

# ── Build HTML (OLD LAYOUT) ────────────────
def build_html(data):
    s = data['stats']
    pcs = data['pcs']
    coords = data['coords']

    def esc(t):
        return str(t).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')

    # Monitored: show count if available (from API), fallback '—'
    monitored_str = str(s['monitored']) if s['monitored'] else '—'

    # Build venue bar chart data (sorted by count desc, top 12)
    venue_counts = {}
    for pc in pcs:
        v = pc['venue']
        if v and v != '-':
            venue_counts[v] = venue_counts.get(v, 0) + 1
    venue_sorted = sorted(venue_counts.items(), key=lambda x: -x[1])[:12]
    venue_labels_json = json.dumps([esc(v[0]) for v in venue_sorted])
    venue_data_json = json.dumps([v[1] for v in venue_sorted])

    # Build type doughnut data
    type_counts = {}
    for pc in pcs:
        t = pc['type']
        if t and t != '-':
            type_counts[t] = type_counts.get(t, 0) + 1
    type_sorted = sorted(type_counts.items(), key=lambda x: -x[1])
    type_labels_json = json.dumps([esc(t[0]) for t in type_sorted])
    type_data_json = json.dumps([t[1] for t in type_sorted])

    # Type background colors
    TC = {'Convenience Stores':'#22c55e','In-Store':'#ec4899','Malls':'#3b82f6','Outdoor':'#f59e0b','Metro':'#a78bfa'}
    type_colors = [TC.get(t[0], '#64748b') for t in type_sorted]
    type_colors_json = json.dumps(type_colors)

    # Build PC table JSON data
    pcs_json = json.dumps([{
        'pc': esc(p['pc']),
        'venue': esc(p['venue']),
        'type': esc(p['type']),
        'ratio': float(p['ratio']),
        'playerid': esc(p['playerid']),
        'last_check': esc(p.get('last_check', '-'))
    } for p in pcs])

    # Split coordinates into Dubai vs Abu Dhabi
    dubai_markers = []
    abu_markers = []
    for c in coords:
        if c['lat'] and c['lng']:
            if c['lat'] >= 25.0:  # Dubai approximate
                dubai_markers.append([c['lat'], c['lng']])
            else:
                abu_markers.append([c['lat'], c['lng']])

    dubai_coords_json = json.dumps(dubai_markers)
    abu_coords_json = json.dumps(abu_markers)

    # Timestamp
    ts = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="600">
<title>NSOC Black Screen Monitor</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root{{--bg:#0b1120;--s1:#111827;--s2:#1a2332;--b1:#1f2b3e;--t1:#e2e8f0;--t2:#94a3b8;--t3:#64748b;--ac:#38bdf8;--gr:#22c55e;--re:#ef4444;--or:#f59e0b;--bl:#3b82f6;--pu:#a78bfa}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:var(--bg);color:var(--t1);font-family:'Inter',-apple-system,sans-serif;-webkit-font-smoothing:antialiased}}
.d{{max-width:1440px;margin:0 auto;padding:20px}}
/* Header */
.hd{{display:flex;align-items:center;gap:14px;padding:14px 20px;margin-bottom:18px;background:var(--s1);border-radius:10px;border:1px solid var(--b1)}}
.hd .dot{{width:4px;height:28px;background:var(--re);border-radius:3px}}
.hd h1{{font-size:18px;font-weight:700;color:var(--re);letter-spacing:-0.3px}}
.hd .sub{{font-size:13px;color:var(--t3);padding-left:12px;border-left:1px solid var(--b1);margin-left:12px;display:flex;align-items:center;gap:8px}}
.hd .ts{{font-size:10px;color:#52525b;font-family:monospace}}
.hd .mode{{font-size:9px;font-weight:700;padding:2px 8px;border-radius:10px;text-transform:uppercase;letter-spacing:.3px;background:rgba(34,197,94,.2);color:#22c55e;border:1px solid rgba(34,197,94,.3)}}
/* Stats */
.st{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px}}
.sc{{background:var(--s1);border-radius:10px;padding:16px 20px;border:1px solid var(--b1);position:relative;overflow:hidden}}
.sc::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px}}
.sc-r::before{{background:var(--re)}}.sc-b::before{{background:var(--bl)}}.sc-o::before{{background:var(--or)}}.sc-p::before{{background:var(--pu)}}
.sc .l{{font-size:11px;font-weight:500;text-transform:uppercase;letter-spacing:.8px;color:var(--t3);margin-bottom:4px}}
.sc .v{{font-size:30px;font-weight:700;letter-spacing:-1px;line-height:1.2}}
.sc-r .v{{color:var(--re)}}.sc-b .v{{color:var(--bl)}}.sc-o .v{{color:var(--or)}}.sc-p .v{{color:var(--pu)}}
.sc .m{{font-size:11px;color:var(--t3);margin-top:4px}}
/* Section */
.sx{{display:flex;align-items:center;gap:10px;padding:0 4px;margin-bottom:12px;margin-top:20px}}
.sx .bar{{width:3px;height:18px;border-radius:2px}}
.sx .bar.r{{background:var(--re)}}.sx .bar.g{{background:var(--gr)}}
.sx h2{{font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:1.2px;color:var(--t2)}}
/* Split */
.sp{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:16px}}
/* Panel */
.pa{{background:var(--s1);border-radius:10px;overflow:hidden;border:1px solid var(--b1)}}
.pa .ph{{display:flex;align-items:center;justify-content:space-between;padding:10px 14px;border-bottom:1px solid var(--b1)}}
.pa .ph h3{{font-size:12px;font-weight:600;color:var(--t2);text-transform:uppercase;letter-spacing:.5px}}
.pa .pb{{padding:6px}}
/* Charts */
.cw{{position:relative;height:220px;width:100%}}
/* Table */
.tb{{width:100%;border-collapse:collapse;font-size:12px}}
.tb th{{text-align:left;padding:8px 12px;color:var(--t3);font-weight:500;font-size:11px;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid var(--b1)}}
.tb td{{padding:7px 12px;border-bottom:1px solid rgba(255,255,255,.04);color:var(--t2)}}
.tb tr:hover td{{background:rgba(255,255,255,.03)}}
.tb .badge{{display:inline-block;padding:2px 7px;border-radius:4px;font-size:10px;font-weight:600}}
.bg-re{{background:rgba(239,68,68,.2);color:var(--re)}}
.bg-or{{background:rgba(245,158,11,.2);color:var(--or)}}
.bg-gr{{background:rgba(34,197,94,.2);color:var(--gr)}}
/* Pagination */
.pag{{display:flex;align-items:center;justify-content:space-between;padding:8px 14px;font-size:12px;color:var(--t3)}}
.pag button{{background:var(--s2);border:1px solid var(--b1);color:var(--t2);padding:4px 12px;border-radius:5px;cursor:pointer;font-size:11px}}
.pag button:hover{{background:var(--b1)}}
.pag .info{{color:var(--t3)}}
@media(max-width:960px){{.st{{grid-template-columns:1fr 1fr}}.sp{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<div class="d">

<!-- HEADER -->
<div class="hd"><div class="dot"></div><h1>NSOC Black Screen</h1><div class="sub">Screens with black ratio ≥ 95%<span class="ts">{esc(ts)}</span><span class="mode">LIVE</span></div></div>

<!-- STATS -->
<div class="st">
  <div class="sc sc-r"><div class="l">Black Screens</div><div class="v">{s["blackTotal"]}</div><div class="m">Screens affected</div></div>
  <div class="sc sc-b"><div class="l">Monitored</div><div class="v">{monitored_str}</div><div class="m">Screens with script</div></div>
  <div class="sc sc-o"><div class="l">Locations</div><div class="v">{s["venues"]}</div><div class="m">Venues affected</div></div>
  <div class="sc sc-p"><div class="l">Venue Types</div><div class="v">{s["venueTypes"]}</div><div class="m">Categories affected</div></div>
</div>

<!-- BY VENUE & TYPE -->
<div class="sx"><div class="bar r"></div><h2>Breakdown</h2></div>
<div class="sp">
  <div class="pa">
    <div class="ph"><h3>Black Screens by Venue</h3></div>
    <div class="cw"><canvas id="venueChart"></canvas></div>
  </div>
  <div class="pa">
    <div class="ph"><h3>By Venue Type</h3></div>
    <div class="cw"><canvas id="typeChart"></canvas></div>
  </div>
</div>

<!-- DETAILED LIST -->
<div class="sx"><div class="bar g"></div><h2>PC with Black Screen — Detailed List</h2></div>
<div class="pa">
  <div style="overflow-x:auto">
    <table class="tb" id="pcTable">
      <thead><tr><th>PC Name</th><th>Venue</th><th>Type</th><th>Ratio</th><th>Player ID</th><th>Last Check</th></tr></thead>
      <tbody id="pcBody"></tbody>
    </table>
  </div>
  <div class="pag"><span class="info" id="tableInfo"></span><div><button onclick="prevPage()">← Prev</button><button onclick="nextPage()" style="margin-left:6px">Next →</button></div></div>
</div>

<!-- MAPS -->
<div class="sx"><div class="bar r"></div><h2>Geographic Overview</h2></div>
<div class="sp">
  <div class="pa">
    <div class="ph"><h3>Dubai</h3></div>
    <div id="dubaiMap" style="height:320px"></div>
  </div>
  <div class="pa">
    <div class="ph"><h3>Abu Dhabi</h3></div>
    <div id="abuDhabiMap" style="height:320px"></div>
  </div>
</div>

</div>

<script>
// ===== LIVE DATA =====
const pcs = {pcs_json};

// ===== STATS =====
const uniqueVenues = new Set(pcs.filter(p=>p.venue!=='-'&&p.venue!=='—').map(p=>p.venue));
const uniqueTypes = new Set(pcs.filter(p=>p.type!=='-'&&p.type!=='—').map(p=>p.type));

// ===== TABLE =====
const perPage = 15; let curPage = 0;
function renderTable(){{
  const start = curPage * perPage;
  const pg = pcs.slice(start, start + perPage);
  document.getElementById('pcBody').innerHTML = pg.map(p => `
    <tr>
      <td style="font-weight:500;color:var(--t1)">${{p.pc}}</td>
      <td>${{p.venue}}</td>
      <td>${{p.type}}</td>
      <td><span class="badge ${{p.ratio>=1?'bg-re':p.ratio>0.95?'bg-or':'bg-gr'}}">${{(p.ratio*100).toFixed(0)}}%</span></td>
      <td style="font-family:monospace;font-size:11px">${{p.playerid}}</td>
      <td style="color:var(--t3)">${{p.last_check}}</td>
    </tr>`).join('');
  document.getElementById('tableInfo').textContent = `${{start+1}}–${{Math.min(start+perPage, pcs.length)}} of ${{pcs.length}}`;
}}
function nextPage(){{if((curPage+1)*perPage < pcs.length){{curPage++;renderTable()}}}}
function prevPage(){{if(curPage>0){{curPage--;renderTable()}}}}
renderTable();

// ===== VENUE CHART =====
const venueCounts = {{}};
pcs.forEach(p => {{ if(p.venue!=='-'&&p.venue!=='—') venueCounts[p.venue] = (venueCounts[p.venue]||0) + 1 }});
const sorted = Object.entries(venueCounts).sort((a,b)=>b[1]-a[1]).slice(0,12);
new Chart(document.getElementById('venueChart'), {{
  type:'bar',
  data:{{ labels:sorted.map(s=>s[0]), datasets:[{{label:'Black Screens', data:sorted.map(s=>s[1]), backgroundColor:['#ef4444','#f59e0b','#3b82f6','#22c55e','#a78bfa','#ec4899','#06b6d4','#f97316','#8b5cf6','#14b8a6','#e11d48','#84cc16'], borderRadius:4 }}] }},
  options:{{
    indexAxis:'y', responsive:true, maintainAspectRatio:false,
    plugins:{{legend:{{display:false}}}},
    scales:{{
      x:{{grid:{{color:'rgba(255,255,255,.04)'}}, ticks:{{color:'#64748b',font:{{size:10}}}}, beginAtZero:true }},
      y:{{grid:{{display:false}}, ticks:{{color:'#64748b',font:{{size:10}}}} }}
    }}
  }}
}});

// ===== TYPE CHART =====
const typeCounts = {{}};
pcs.forEach(p => {{ if(p.type!=='-'&&p.type!=='—') typeCounts[p.type] = (typeCounts[p.type]||0)+1 }});
const typeSorted = Object.entries(typeCounts).sort((a,b)=>b[1]-a[1]);
const typeColors = {{'Convenience Stores':'#22c55e','In-Store':'#ec4899','Malls':'#3b82f6','Outdoor':'#f59e0b','Metro':'#a78bfa'}};
new Chart(document.getElementById('typeChart'), {{
  type:'doughnut',
  data:{{ labels:typeSorted.map(s=>s[0]), datasets:[{{ data:typeSorted.map(s=>s[1]), backgroundColor:typeSorted.map(s=>typeColors[s[0]]||'#64748b'), borderWidth:0 }}] }},
  options:{{
    responsive:true, maintainAspectRatio:false,
    plugins:{{
      legend:{{ position:'right', labels:{{ color:'#94a3b8', font:{{size:11}}, boxWidth:10, padding:12 }} }}
    }}
  }}
}});

// ===== MAPS =====
function initMap(id,center,markers){{
  if(markers.length===0) return;
  const m = L.map(id,{{ center, zoom:12, layers:[L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png',{{subdomains:'abcd',maxZoom:19}})], zoomControl:false, attributionControl:false }});
  markers.forEach(p=>{{
    L.circleMarker([p[0],p[1]], {{ radius:8, fillColor:'#ef4444', color:'#fff', weight:1.5, opacity:0.8, fillOpacity:0.5 }}).addTo(m);
  }});
}}
const dubaiCoords = {dubai_coords_json};
const abuCoords = {abu_coords_json};
initMap('dubaiMap',[25.18,55.28], dubaiCoords);
initMap('abuDhabiMap',[24.46,54.38], abuCoords);
</script>
</body>
</html>'''
    return html

# ── Main ───────────────────────────────────
def main():
    data = fetch_all()
    print(f'  Black screens: {data["stats"]["blackTotal"]}')
    print(f'  Monitored: {data["stats"]["monitored"]}')
    print(f'  Venues: {data["stats"]["venues"]}')
    print(f'  Venue types: {data["stats"]["venueTypes"]}')
    print(f'  PCs in list: {len(data["pcs"])}')
    print(f'  Coords found: {len(data["coords"])}')
    print(f'  Mode: {"LIVE" if data["live"] else "STATIC"}')

    html = build_html(data)
    out = 'grafana-dashboards/nsoc-black-screen.html'
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    with open(out, 'w') as f:
        f.write(html)
    print(f'\n✅ Written {out} ({len(html)} bytes)')

if __name__ == '__main__':
    main()
