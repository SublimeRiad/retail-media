#!/usr/bin/env python3
"""Build nsoc-black-screen.html — query Grafana API, embed live data"""
import json, os, urllib.request, datetime

# ── Auth ───────────────────────────────────
token = os.environ.get('GRAFANA_TOKEN', '')
if not token:
    # Fallback: try loading from file
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
    # Total black screens (ratio >= 0.95)
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
        "COALESCE(agents.tag, '-') AS playerid "
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
    if pcs_frame and len(pcs_frame) >= 5:
        for i in range(len(pcs_frame[0])):
            pcs_list.append({
                'pc': safe_str(pcs_frame, i, 0),
                'venue': safe_str(pcs_frame, i, 1),
                'type': safe_str(pcs_frame, i, 2),
                'ratio': safe_val(pcs_frame, i, 3),
                'playerid': safe_str(pcs_frame, i, 4)
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

# ── Build HTML ─────────────────────────────
def build_html(data):
    s = data['stats']
    mode = 'LIVE' if data['live'] else 'STATIC'
    mode_cls = 'mode-live' if data['live'] else 'mode-fallback'

    def esc(t):
        return str(t).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')

    # Top PCs (first 12 from pcs list, sorted by ratio desc)
    top_pcs = sorted(data['pcs'], key=lambda x: -x['ratio'])[:12]
    top_html = ''
    for i, pc in enumerate(top_pcs):
        r = pc['ratio']
        color = '#ef4444' if r >= 0.95 else '#f97316' if r >= 0.80 else '#eab308' if r >= 0.60 else '#22c55e'
        pct = f'{r*100:.2f}%' if r < 1 else f'{r*100:.0f}%'
        top_html += f'''<div style="background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.15);border-radius:5px;padding:6px 12px;min-width:200px;flex:1">
<div style="display:flex;align-items:center;gap:6px">
<span style="font-weight:700;color:#ef4444;font-size:12px">#{i+1}</span>
<span style="font-weight:600;font-size:12px;font-family:'SF Mono',Consolas,monospace">{esc(pc['pc'])}</span>
<span style="font-weight:700;font-size:14px;color:#f97316;margin-left:auto">{esc(pct)}</span>
</div>
<div style="display:flex;gap:10px;font-size:9px;color:#6b7c93;margin-top:1px">
<span>Player: {esc(pc['playerid'])}</span>
<span>{esc(pc['venue'])}</span>
</div>
</div>'''

    # Venues breakdown
    TC = {'Convenience Stores':'#22c55e','In-Store':'#ec4899','Malls':'#3b82f6','Outdoor':'#f59e0b','Metro':'#a78bfa'}
    venues_html = ''
    for v in data['venues']:
        color = '#ef4444'
        bar_px = min(max(int(v['count'] / max(1, max(x['count'] for x in data['venues'] or [{'count':1}])) * 200), 10), 200)
        venues_html += f'''<div class="venue-bar"><div class="vb-label">{esc(v['venue'])}</div><div class="vb-track"><div class="vb-fill" style="width:{bar_px}px;background:{'#ef4444'}"></div></div><div class="vb-val">{v['count']}</div></div>'''

    types_total = sum(t['count'] for t in data['types'])
    types_html = ''
    for t in sorted(data['types'], key=lambda x: -x['count']):
        pct = f'{(t["count"]/types_total*100):.0f}' if types_total > 0 else '0'
        c = TC.get(t['type'], '#64748b')
        types_html += f'''<div class="type-item"><span class="type-dot" style="background:{c}"></span><span class="type-name">{esc(t['type'])}</span><span class="type-val">{t["count"]}</span><span class="type-pct">{pct}%</span></div>'''

    # PCs table by venue
    venue_groups = {}
    for pc in data['pcs']:
        v = pc['venue']
        if v not in venue_groups:
            venue_groups[v] = []
        venue_groups[v].append(pc)

    venue_colors = {'Malls': '#3b82f6', 'In-Store': '#ec4899', 'Outdoor': '#f59e0b', 'Metro': '#a78bfa', 'Convenience Stores': '#22c55e'}
    venue_rows_html = ''
    for venue_name, pcs in sorted(venue_groups.items(), key=lambda x: -len(x[1])):
        pc_type = pcs[0]['type'] if pcs else 'Unknown'
        color = venue_colors.get(pc_type, '#64748b')
        rows = ''
        for pc in sorted(pcs, key=lambda x: -x['ratio']):
            r = pc['ratio']
            bar_pct = min(r * 100, 100)
            pct_text = f'{r*100:.2f}%' if r < 1 else f'{r*100:.0f}%'
            bar_color = '#ef4444' if r >= 0.95 else '#f97316' if r >= 0.80 else '#eab308' if r >= 0.60 else '#22c55e'
            rows += f'''<tr><td><span class="ic ok">✓</span></td><td class="sn" title="{esc(pc['pc'])}">{esc(pc['pc'])}</td><td class="tg">{esc(pc['playerid'])}</td><td class="tr"><div class="dc"><span class="db" style="width:{bar_pct:.1f}px;background:{bar_color}"></span>{pct_text}</div></td></tr>'''
        venue_rows_html += f'''<div class="venue-card" style="border-top:2px solid {color}">
<div class="vc-header"><h3 style="color:{color}">{esc(venue_name)}</h3><span class="badge">{len(pcs)} black screens</span></div>
<div class="scroll-t"><table class="pc-t"><thead><tr><th style="width:14px">S</th><th>PC</th><th style="width:40px">Player</th><th style="width:56px;text-align:right">Black %</th></tr></thead><tbody>{rows}</tbody></table></div>
</div>'''

    ts = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="600">
<title>NSOC Black Screen Monitor</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Inter',-apple-system,sans-serif;background:#080a0e;color:#e0e2e6;font-size:13px;height:100vh;display:flex;flex-direction:column;overflow:hidden}}
.header{{background:linear-gradient(135deg,#111318,#1c212d);padding:7px 18px;border-bottom:1px solid #1e293b;display:flex;align-items:center;justify-content:space-between;flex-shrink:0;gap:8px;flex-wrap:wrap}}
.header h1{{font-size:14px;font-weight:700;background:linear-gradient(90deg,#3b82f6,#8b5cf6);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.header .meta{{display:flex;align-items:center;gap:8px}}
.header .ts{{color:#52525b;font-size:9px;font-family:monospace}}
.mode{{font-size:9px;font-weight:700;padding:2px 8px;border-radius:10px;text-transform:uppercase;letter-spacing:.3px}}
.mode-live{{background:rgba(34,197,94,.2);color:#22c55e;border:1px solid rgba(34,197,94,.3)}}
.mode-fallback{{background:rgba(245,158,11,.2);color:#f59e0b;border:1px solid rgba(245,158,11,.3)}}
.stats-row{{display:flex;gap:8px;padding:8px 18px;background:#0c0e13;border-bottom:1px solid #161b22;flex-shrink:0;flex-wrap:wrap}}
.stat-card{{background:linear-gradient(145deg,#161b22,#12151d);border:1px solid #1e293b;border-radius:8px;padding:8px 16px;min-width:100px;flex:1;text-align:center}}
.stat-card .sv{{font-size:22px;font-weight:800;background:linear-gradient(90deg,#3b82f6,#8b5cf6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;line-height:1.2}}
.stat-card .sl{{font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:.5px;margin-top:2px}}
.body{{flex:1;display:flex;flex-direction:column;overflow:hidden;padding:6px 12px 0;gap:6px}}
.top-row{{display:flex;gap:8px;flex-shrink:0;overflow-x:auto;padding-bottom:6px;min-height:60px}}
.top-pc-card{{background:#0c0e13;border:1px solid #161b22;border-radius:8px;padding:8px 12px;flex-shrink:0;display:flex;flex-direction:column;justify-content:center;min-width:180px}}
.top-pc-label{{font-size:9px;color:#64748b}}
.top-pc-val{{font-size:16px;font-weight:700}}
.mid-row{{display:flex;gap:8px;flex:1;min-height:0}}
.left-panel{{flex:1;min-width:0;display:flex;flex-direction:column;background:#0c0e13;border:1px solid #161b22;border-radius:8px;overflow:hidden}}
.left-panel .lp-header{{padding:6px 10px;font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:.5px;font-weight:600;border-bottom:1px solid #161b22;flex-shrink:0}}
.scroll-area{{flex:1;overflow-y:auto;padding:4px 6px}}
.venue-bar{{display:flex;align-items:center;gap:6px;padding:3px 4px;font-size:11px}}
.vb-label{{min-width:80px;max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#94a3b8}}
.vb-track{{flex:1;height:14px;background:#161b22;border-radius:3px;overflow:hidden;max-width:200px}}
.vb-fill{{height:100%;border-radius:3px;min-width:4px}}
.vb-val{{min-width:24px;text-align:right;font-weight:600}}
.right-panel{{width:clamp(220px,28vw,340px);display:flex;flex-direction:column;background:#0c0e13;border:1px solid #161b22;border-radius:8px;overflow:hidden}}
.right-panel .rp-header{{padding:6px 10px;font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:.5px;font-weight:600;border-bottom:1px solid #161b22;flex-shrink:0}}
.type-item{{display:flex;align-items:center;gap:6px;padding:4px 8px;font-size:11px;border-bottom:1px solid rgba(255,255,255,.03)}}
.type-dot{{width:8px;height:8px;border-radius:2px;flex-shrink:0}}
.type-name{{color:#94a3b8;flex:1}}
.type-val{{font-weight:700;font-size:13px}}
.type-pct{{font-size:10px;color:#52525b;min-width:28px;text-align:right}}
.venue-row{{flex:1;min-height:0;overflow-x:auto;display:flex;gap:6px;padding:0 0 6px 0}}
.venue-card{{background:#0c0e13;border:1px solid #161b22;border-radius:8px;min-width:300px;flex:1;display:flex;flex-direction:column;overflow:hidden}}
.vc-header{{display:flex;align-items:center;justify-content:space-between;padding:6px 10px;border-bottom:1px solid #161b22;flex-shrink:0}}
.vc-header h3{{font-size:12px;font-weight:600}}
.badge{{background:#161b22;padding:0 8px;border-radius:8px;font-size:9px;color:#64748b;font-weight:600}}
.scroll-t{{flex:1;overflow-y:auto}}
.pc-t{{width:100%;border-collapse:collapse;font-size:10px}}
.pc-t th{{padding:4px 6px;background:#080a0e;color:#52525b;font-size:8px;text-transform:uppercase;letter-spacing:.5px;text-align:left;font-weight:600;position:sticky;top:0;z-index:1;border-bottom:1px solid #161b22}}
.pc-t td{{padding:3px 6px;border-bottom:1px solid rgba(255,255,255,.02);vertical-align:middle}}
.pc-t tr:hover td{{background:rgba(59,130,246,.06)}}
.sn{{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:200px;color:#e0e2e6}}
.tg{{font-family:'SF Mono',Consolas,monospace;color:#52525b;font-size:9px}}
.tr{{text-align:right;white-space:nowrap}}
.ic{{font-size:11px}}
.ic.ok{{color:#22c55e}}
.dc{{display:flex;align-items:center;gap:4px;justify-content:flex-end}}
.db{{height:10px;border-radius:2px;min-width:2px}}
.footer{{padding:4px 18px;text-align:center;color:#1e293b;font-size:8px;border-top:1px solid #161b22;flex-shrink:0}}
@media(max-width:1000px){{.right-panel{{width:180px}}.mid-row{{flex-direction:column}}.venue-row{{flex-direction:column}}}}
</style>
</head>
<body>
<div class="header">
<h1>NSOC Black Screen Monitor</h1>
<div class="meta"><span class="ts">{esc(ts)}</span><span class="mode {mode_cls}">{mode}</span></div>
</div>
<div class="stats-row">
<div class="stat-card"><div class="sv">{s["blackTotal"]}</div><div class="sl">Black Screens</div></div>
<div class="stat-card"><div class="sv">{s["monitored"]}</div><div class="sl">Monitored</div></div>
<div class="stat-card"><div class="sv">{s["venues"]}</div><div class="sl">Venues</div></div>
<div class="stat-card"><div class="sv">{s["venueTypes"]}</div><div class="sl">Venue Types</div></div>
</div>
<div class="body">
<div class="top-row">{top_html}</div>
<div class="mid-row">
<div class="left-panel"><div class="lp-header">Venues with black screens</div><div class="scroll-area">{venues_html}</div></div>
<div class="right-panel"><div class="rp-header">By venue type</div><div class="scroll-area">{types_html}</div></div>
</div>
<div class="venue-row">{venue_rows_html}</div>
</div>
<div class="footer">NSOC Black Screen Monitor · {esc(ts)}</div>
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
