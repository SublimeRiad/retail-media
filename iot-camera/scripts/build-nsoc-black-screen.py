#!/usr/bin/env python3
"""Build nsoc-black-screen.html — query Grafana API, embed live data.
Output: old layout with Chart.js charts, Leaflet maps, paginated table."""
import json, os, urllib.request, datetime

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
        'live': use_live
    }

# ── Build HTML (OLD LAYOUT) ────────────────
def build_html(data):
    s = data['stats']
    pcs = data['pcs']

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

    # Build type doughnut data
    type_counts = {}
    for pc in pcs:
        t = pc['type']
        if t and t != '-':
            type_counts[t] = type_counts.get(t, 0) + 1
    type_sorted = sorted(type_counts.items(), key=lambda x: -x[1])

    # Build PC table JSON data
    pcs_json = json.dumps([{
        'pc': esc(p['pc']),
        'venue': esc(p['venue']),
        'type': esc(p['type']),
        'ratio': float(p['ratio']),
        'playerid': esc(p['playerid']),
        'last_check': esc(p.get('last_check', '-'))
    } for p in pcs])

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
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{height:100vh;overflow:hidden;font-family:'Inter',-apple-system,sans-serif;background:#080a0e;color:#e0e2e6;font-size:12px}}
/* ── TOP BAR ── */
.top{{display:flex;align-items:center;gap:8px;padding:6px 14px;background:#0c0e13;border-bottom:1px solid #161b22;height:46px;flex-shrink:0}}
.top .dot{{width:3px;height:18px;background:#ef4444;border-radius:2px}}
.top h1{{font-size:13px;font-weight:700;color:#ef4444;white-space:nowrap}}
.st-badge{{display:flex;align-items:center;gap:4px;padding:2px 10px;border-radius:4px;font-size:10px;font-weight:600;height:24px;border:1px solid rgba(255,255,255,.06)}}
.st-badge .sv{{font-size:14px;font-weight:800}}
.st-badge .sl{{color:#64748b;font-weight:500}}
.st-br{{background:rgba(239,68,68,.12);color:#ef4444}}.st-bb{{background:rgba(59,130,246,.12);color:#60a5fa}}.st-bo{{background:rgba(245,158,11,.12);color:#f59e0b}}.st-bp{{background:rgba(168,85,247,.12);color:#a78bfa}}
.top .spacer{{flex:1}}
.top .ts{{color:#52525b;font-size:9px;font-family:monospace}}
.top .mode{{font-size:8px;font-weight:700;padding:1px 7px;border-radius:8px;text-transform:uppercase;letter-spacing:.3px;background:rgba(34,197,94,.2);color:#22c55e;border:1px solid rgba(34,197,94,.3)}}
/* ── MID ROW ── */
.mid{{display:flex;gap:6px;padding:5px 10px;height:clamp(200px,32vh,260px);flex-shrink:0}}
.mp{{flex:1;background:#0c0e13;border:1px solid #161b22;border-radius:6px;overflow:hidden;display:flex;flex-direction:column}}
.mp .mh{{flex-shrink:0;padding:4px 10px;font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:.5px;font-weight:600;border-bottom:1px solid #161b22}}
.mp .mb{{flex:1;position:relative;min-height:0}}
.mp .mb canvas{{height:100%!important;width:100%!important}}
.mp-50{{flex:0.5}}
/* ── BOTTOM TABLE ── */
.btm{{flex:1;display:flex;flex-direction:column;padding:0 10px 4px;min-height:0}}
.btm .bh{{display:flex;align-items:center;justify-content:space-between;padding:3px 8px;flex-shrink:0}}
.btm .bh h2{{font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:.6px;font-weight:600}}
.btm .bh .cnt{{font-size:10px;color:#52525b}}
.tb-wr{{flex:1;overflow-y:auto;border:1px solid #161b22;border-radius:4px}}
.tb-wr::-webkit-scrollbar{{width:4px}}
.tb-wr::-webkit-scrollbar-track{{background:#080a0e}}
.tb-wr::-webkit-scrollbar-thumb{{background:#1e293b;border-radius:3px}}
.tb{{width:100%;border-collapse:collapse;font-size:10px}}
.tb th{{position:sticky;top:0;z-index:2;text-align:left;padding:3px 8px;color:#52525b;font-weight:600;font-size:9px;text-transform:uppercase;letter-spacing:.4px;background:#080a0e;border-bottom:1px solid #161b22}}
.tb td{{padding:3px 8px;border-bottom:1px solid rgba(255,255,255,.02);color:#94a3b8}}
.tb tr:hover td{{background:rgba(59,130,246,.06)}}
.tb .pc-n{{color:#e0e2e6;font-weight:500}}
.tb .pc-p{{font-family:'SF Mono',Consolas,monospace;font-size:9px;color:#52525b}}
.tb .pc-ven{{max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.bt{{display:inline-flex;align-items:center;gap:3px}}
.bt-bar{{width:36px;height:8px;border-radius:2px}}
.badge{{padding:1px 6px;border-radius:3px;font-size:9px;font-weight:600}}
.bg-re{{background:rgba(239,68,68,.2);color:#ef4444}}
.bg-or{{background:rgba(245,158,11,.2);color:#f59e0b}}
.bg-gr{{background:rgba(34,197,94,.2);color:#22c55e}}
</style>
</head>
<body>

<!-- TOP BAR -->
<div class="top">
  <div class="dot"></div>
  <h1>NSOC Black Screen</h1>
  <div class="st-badge st-br"><span class="sv">{s["blackTotal"]}</span>&nbsp;<span class="sl">Black</span></div>
  <div class="st-badge st-bb"><span class="sv">{monitored_str}</span>&nbsp;<span class="sl">Monitored</span></div>
  <div class="st-badge st-bo"><span class="sv">{s["venues"]}</span>&nbsp;<span class="sl">Venues</span></div>
  <div class="st-badge st-bp"><span class="sv">{s["venueTypes"]}</span>&nbsp;<span class="sl">Types</span></div>
  <div class="spacer"></div>
  <span class="ts">{esc(ts)}</span>
  <span class="mode">LIVE</span>
</div>

<!-- MID ROW: CHARTS + MAPS -->
<div class="mid">
  <div class="mp mp-50">
    <div class="mh">Black Screens by Venue</div>
    <div class="mb"><canvas id="venueChart"></canvas></div>
  </div>
  <div class="mp" style="flex:0.35">
    <div class="mh">By Type</div>
    <div class="mb"><canvas id="typeChart"></canvas></div>
  </div>

</div>

<!-- BOTTOM: PC TABLE -->
<div class="btm">
  <div class="bh">
    <h2>PC with Black Screen</h2>
    <span class="cnt" id="pcCount"></span>
  </div>
  <div class="tb-wr">
    <table class="tb">
      <thead><tr><th style="width:30px">#</th><th>PC Name</th><th>Venue</th><th style="width:80px">Type</th><th style="width:100px">Black %</th><th style="width:80px">Player ID</th><th style="width:80px">Last Check</th></tr></thead>
      <tbody id="pcBody"></tbody>
    </table>
  </div>
</div>

</body>

<script>
// ===== LIVE DATA =====
const pcs = {pcs_json};
document.getElementById('pcCount').textContent = pcs.length + ' PC' + (pcs.length!==1?'s':'');

// ===== TABLE (scrollable, all rows) =====
document.getElementById('pcBody').innerHTML = pcs.map((p,i) => `
  <tr>
    <td style="color:#52525b">${{i+1}}</td>
    <td class="pc-n">${{p.pc}}</td>
    <td class="pc-ven">${{p.venue}}</td>
    <td>${{p.type}}</td>
    <td><span class="bt"><span class="bt-bar" style="background:${{p.ratio>=1?'#ef4444':p.ratio>0.95?'#f97316':'#22c55e'}};width:${{Math.min(p.ratio*36,36)}}px"></span><span class="badge ${{p.ratio>=1?'bg-re':p.ratio>0.95?'bg-or':'bg-gr'}}">${{(p.ratio*100).toFixed(0)}}%</span></span></td>
    <td class="pc-p">${{p.playerid}}</td>
    <td>${{p.last_check}}</td>
  </tr>`).join('');

// ===== VENUE CHART =====
const venueCounts = {{}};
pcs.forEach(p => {{ if(p.venue!=='-'&&p.venue!=='—') venueCounts[p.venue] = (venueCounts[p.venue]||0) + 1 }});
const sorted = Object.entries(venueCounts).sort((a,b)=>b[1]-a[1]).slice(0,12);
new Chart(document.getElementById('venueChart'), {{
  type:'bar',
  data:{{ labels:sorted.map(s=>s[0]), datasets:[{{label:'Black Screens', data:sorted.map(s=>s[1]), backgroundColor:['#ef4444','#f59e0b','#3b82f6','#22c55e','#a78bfa','#ec4899','#06b6d4','#f97316','#8b5cf6','#14b8a6','#e11d48','#84cc16'], borderRadius:3 }}] }},
  options:{{
    indexAxis:'y', responsive:true, maintainAspectRatio:false,
    plugins:{{legend:{{display:false}}}},
    scales:{{
      x:{{grid:{{color:'rgba(255,255,255,.04)'}}, ticks:{{color:'#64748b',font:{{size:9}}}}, beginAtZero:true }},
      y:{{grid:{{display:false}}, ticks:{{color:'#64748b',font:{{size:8}}}} }}
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
      legend:{{ position:'right', labels:{{ color:'#94a3b8', font:{{size:9}}, boxWidth:8, padding:8 }}}}
    }}
  }}
}});


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
    print(f'  Mode: {"LIVE" if data["live"] else "STATIC"}')

    html = build_html(data)
    out = 'grafana-dashboards/nsoc-black-screen.html'
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    with open(out, 'w') as f:
        f.write(html)
    print(f'\n✅ Written {out} ({len(html)} bytes)')

if __name__ == '__main__':
    main()
