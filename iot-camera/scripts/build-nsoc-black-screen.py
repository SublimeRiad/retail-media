#!/usr/bin/env python3
"""Build nsoc-black-screen.html — query Grafana API, embed live data.
Output: Leaflet maps (Dubai + Abu Dhabi), paginated table with comment field."""
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
        "COALESCE(DATE_FORMAT(fields.date_mod, '%Y-%m-%d'), '-') AS last_check, "
        "COALESCE(comp.comment, '-') AS comment "
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
    if pcs_frame and len(pcs_frame) >= 7:
        for i in range(len(pcs_frame[0])):
            pcs_list.append({
                'pc': safe_str(pcs_frame, i, 0),
                'venue': safe_str(pcs_frame, i, 1),
                'type': safe_str(pcs_frame, i, 2),
                'ratio': safe_val(pcs_frame, i, 3),
                'playerid': safe_str(pcs_frame, i, 4),
                'last_check': safe_str(pcs_frame, i, 5),
                'comment': safe_str(pcs_frame, i, 6)
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

    # Build PC table JSON data
    pcs_json = json.dumps([{
        'pc': esc(p['pc']),
        'venue': esc(p['venue']),
        'type': esc(p['type']),
        'ratio': float(p['ratio']),
        'playerid': esc(p['playerid']),
        'last_check': esc(p.get('last_check', '-')),
        'comment': esc(p.get('comment', '-'))
    } for p in pcs])

    # Split coordinates into Dubai vs Abu Dhabi
    dubai_markers = []
    abu_markers = []
    for c in coords:
        if c['lat'] and c['lng']:
            if c['lat'] >= 25.0:
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
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{height:100vh;overflow:hidden;font-family:'Inter',sans-serif;background:#080a0e;color:#e0e2e6}}
/* ── TOP BAR ── */
.top{{display:flex;align-items:center;gap:12px;padding:6px 16px;background:#0c0e13;border-bottom:1px solid #161b22;height:52px;flex-shrink:0}}
.top .dot{{width:3px;height:16px;background:#ef4444;border-radius:2px}}
.top h1{{font-size:12px;font-weight:700;color:#ef4444;white-space:nowrap}}
.stb{{display:flex;align-items:center;gap:5px;padding:3px 12px;border-radius:5px;font-size:11px;font-weight:600;height:28px;border:1px solid rgba(255,255,255,.08)}}
.stb .sv{{font-size:20px;font-weight:800}}
.stb .sl{{color:#64748b;font-size:10px}}
.sr{{background:rgba(239,68,68,.12);color:#ef4444}}.sb{{background:rgba(59,130,246,.12);color:#60a5fa}}.so{{background:rgba(245,158,11,.12);color:#f59e0b}}.sp{{background:rgba(168,85,247,.12);color:#a78bfa}}
.top .spc{{flex:1}}
.top .ts{{color:#52525b;font-size:8px;font-family:monospace}}
.top .mode{{font-size:7px;font-weight:700;padding:1px 6px;border-radius:6px;text-transform:uppercase;background:rgba(34,197,94,.2);color:#22c55e;border:1px solid rgba(34,197,94,.3)}}
/* ── MAIN SPLIT ── */
.main{{display:flex;flex:1;min-height:0;padding:4px 10px 4px;gap:6px}}
/* Left: maps */
.mcol{{flex:0.48;display:flex;flex-direction:column;gap:4px;min-width:0}}
.mcol .mlabel{{font-size:8px;color:#64748b;text-transform:uppercase;letter-spacing:.4px;font-weight:600;padding:0 2px}}
.mcol .mmap{{flex:1;border-radius:4px;overflow:hidden;border:1px solid #161b22;background:#0c0e13}}
/* Right: table */
.tcol{{flex:0.52;display:flex;flex-direction:column;min-width:0}}
.tcol .thdr{{display:flex;align-items:center;justify-content:space-between;padding:0 2px 2px;flex-shrink:0}}
.tcol .thdr h2{{font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:.5px;font-weight:600}}
.tcol .thdr .cnt{{font-size:8px;color:#52525b}}
.tb-wr{{flex:1;overflow-y:auto;border:1px solid #161b22;border-radius:4px;min-height:0}}

.tb{{width:100%;border-collapse:collapse;font-size:10px}}
.tb th{{position:sticky;top:0;z-index:2;text-align:left;padding:4px 8px;color:#52525b;font-weight:600;font-size:8px;text-transform:uppercase;letter-spacing:.3px;background:#080a0e;border-bottom:1px solid #161b22}}
.tb td{{padding:3px 8px;border-bottom:1px solid rgba(255,255,255,.015);color:#94a3b8}}
.tb tr:hover td{{background:rgba(59,130,246,.06)}}
.tb .pn{{color:#e0e2e6;font-weight:500}}
.tb .cm{{color:#52525b;font-size:8px;display:block}}
.tb .pp{{font-family:monospace;font-size:8px;color:#52525b}}
.tb .pv{{max-width:100px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.bt{{display:inline-flex;align-items:center;gap:2px}}
.bt-bar{{width:28px;height:6px;border-radius:2px}}
.bdg{{padding:1px 5px;border-radius:2px;font-size:8px;font-weight:600}}
.bdr{{background:rgba(239,68,68,.2);color:#ef4444}}
.bdo{{background:rgba(245,158,11,.2);color:#f97316}}
.bdg{{background:rgba(34,197,94,.2);color:#22c55e}}
::-webkit-scrollbar{{width:3px}}
::-webkit-scrollbar-track{{background:#080a0e}}
::-webkit-scrollbar-thumb{{background:#1e293b;border-radius:2px}}
</style>
</head>
<body>

<div class="top">
  <div class="dot"></div>
  <h1>NSOC Black Screen</h1>
  <div class="stb sr"><span class="sv">{s["blackTotal"]}</span>&nbsp;<span class="sl">Black</span></div>
  <div class="stb sb"><span class="sv">{monitored_str}</span>&nbsp;<span class="sl">Monitored</span></div>
  <div class="stb so"><span class="sv">{s["venues"]}</span>&nbsp;<span class="sl">Venues</span></div>
  <div class="stb sp"><span class="sv">{s["venueTypes"]}</span>&nbsp;<span class="sl">Types</span></div>
  <div class="spc"></div>
  <span class="ts">{esc(ts)}</span>
  <span class="mode">LIVE</span>
</div>

<div class="main">
  <!-- Left: Maps column -->
  <div class="mcol">
    <span class="mlabel"><span style="color:var(--re)">●</span> Geographic Overview</span>
    <div class="mmap" id="dubaiMap"></div>
    <div class="mmap" id="abuDhabiMap"></div>
  </div>
  <!-- Right: Auto-scroll PC table -->
  <div class="tcol">
    <div class="thdr">
      <h2>PC with Black Screen</h2>
      <span class="cnt" id="pcCount"></span>
    </div>
    <div class="tb-wr">
      <table class="tb">
          <thead><tr><th style="width:24px">#</th><th>PC Name / Comment</th><th style="width:70px">Venue</th><th style="width:55px">Type</th><th style="width:70px">Black %</th><th style="width:60px">Player</th><th style="width:55px">Checked</th></tr></thead>
          <tbody></tbody>
        </table>
    </div>
  </div>
</div>

<script>
const pcs = {pcs_json};
const total = pcs.length;
document.getElementById('pcCount').textContent = total + ' PC' + (total!==1?'s':'');
const rows = pcs.map((p,i)=>`
  <tr>
    <td style="color:#52525b">${{i+1}}</td>
    <td><span class="pn">${{p.pc}}</span><span class="cm">${{p.comment}}</span></td>
    <td class="pv">${{p.venue}}</td>
    <td>${{p.type}}</td>
    <td><span class="bt"><span class="bt-bar" style="background:${{p.ratio>=1?'#ef4444':p.ratio>0.95?'#f97316':'#22c55e'}};width:${{Math.min(p.ratio*28,28)}}px"></span><span class="bdg ${{p.ratio>=1?'bdr':p.ratio>0.95?'bdo':'bdg'}}">${{(p.ratio*100).toFixed(0)}}%</span></span></td>
    <td class="pp">${{p.playerid}}</td>
    <td>${{p.last_check}}</td>
  </tr>`).join('');
document.querySelector('.tb-wr table tbody').innerHTML = rows;

function initMap(id,center,markers){{
  if(markers.length===0) return;
  const m = L.map(id,{{center,zoom:9,layers:[L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png',{{subdomains:'abcd',maxZoom:19}})],zoomControl:false,attributionControl:false,dragging:false,scrollWheelZoom:false}});
  setTimeout(()=>m.invalidateSize(),500);
  setTimeout(()=>{{
    try{{
      const g=L.featureGroup(markers.map(p=>L.circleMarker([p[0],p[1]],{{radius:6,fillColor:'#ef4444',color:'#fff',weight:1.5,opacity:.8,fillOpacity:.5}})));
      g.eachLayer(l=>l.addTo(m));
      m.fitBounds(g.getBounds(),{{padding:[15,15],maxZoom:10}});
    }}catch(e){{}}
  }},800);
  setTimeout(()=>{{try{{m.fitBounds(g.getBounds(),{{padding:[20,20],maxZoom:10}})}}catch(e){{}}}},500);
}}
const dc = {dubai_coords_json}, ac = {abu_coords_json};
initMap('dubaiMap',[25.18,55.28],dc);
initMap('abuDhabiMap',[24.46,54.38],ac);
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
