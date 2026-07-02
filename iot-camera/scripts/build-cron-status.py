#!/usr/bin/env python3
"""Build cron-status.html — shows only dashboard-related cron runs & next executions."""
import json, os, re, sys
from datetime import datetime, timezone

# Ensure we can import subprocess
from subprocess import run as sub_run
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

OUTPUT = os.environ.get("GITHUB_WORKSPACE", "/tmp/rm-push") + "/cron-status.html"
REPO_DIR = "/tmp/rm-push"
GITHUB_OWNER = "SublimeRiad"
GITHUB_REPO = "retail-media"

def run(cmd, cwd=None):
    try:
        r = sub_run(cmd, capture_output=True, text=True, cwd=cwd)
        return r.stdout.strip()
    except Exception:
        return ""

def github_workflow_runs(workflow_id, limit=5):
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/workflows/{workflow_id}/runs?per_page={limit}"
    req = Request(url, headers={"User-Agent": "cron-status/1.0", "Accept": "application/vnd.github+json"})
    try:
        resp = urlopen(req, timeout=10)
        data = json.loads(resp.read())
        return [{"created_at": r["created_at"], "conclusion": r.get("conclusion"), "run_started_at": r.get("run_started_at")} for r in data.get("workflow_runs", [])]
    except (HTTPError, URLError, json.JSONDecodeError):
        return []

def github_pages_runs(limit=3):
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/runs?per_page={limit * 3}&status=completed"
    req = Request(url, headers={"User-Agent": "cron-status/1.0", "Accept": "application/vnd.github+json"})
    try:
        resp = urlopen(req, timeout=10)
        data = json.loads(resp.read())
        return [{"created_at": r["created_at"], "conclusion": r.get("conclusion")} for r in data.get("workflow_runs", []) if "pages" in r.get("name", "").lower() or "pages" in r.get("path", "")][:limit]
    except (HTTPError, URLError, json.JSONDecodeError):
        return []

# ── Frequencies ──
WORKFLOWS = [
    ("update-iot-retail", "Update IoT Retail Dashboards", 296625292, "*/10 * * * *", "Every 10m"),
    ("update-dashboards", "Update Dashboards (NSOC)", 305665737, "*/10 * * * *", "Every 10m"),
]
PAGES_FREQ = "On push to master"

now = datetime.now(timezone.utc)
ts_date = now.strftime("%Y-%m-%dT%H:%M:%SZ")

def tm_iso(isostr):
    if not isostr:
        return '<span class="val muted">—</span>'
    return f'<script>document.write(fmt("{isostr}"));</script>'

def next_run_from_iso(last_iso_or_none, interval_min=10, label="in —"):
    if not last_iso_or_none:
        return label
    from datetime import datetime, timedelta, timezone
    dt = datetime.fromisoformat(last_iso_or_none.replace("Z", "+00:00"))
    nxt = dt + timedelta(minutes=interval_min)
    return f'<script>document.write(fmt("{nxt.isoformat()}"));</script>'

def badge(conclusion):
    if conclusion == "success":
        return '<span class="badge bg-ok">✅ Success</span>'
    elif conclusion == "failure":
        return '<span class="badge bg-err">❌ Failed</span>'
    elif conclusion == "cancelled":
        return '<span class="badge bg-warn">⚠ Cancelled</span>'
    else:
        return f'<span class="badge bg-idle">— {conclusion or "unknown"}</span>'

# ── Fetch data ──
w_data = {}
for wid_name, wf_name, wid, cron_expr, freq_label in WORKFLOWS:
    runs = github_workflow_runs(wid)
    w_data[wid_name] = {
        "name": wf_name,
        "runs": runs,
        "last": runs[0]["created_at"] if runs else None,
        "conclusion": runs[0]["conclusion"] if runs else None,
        "cron": cron_expr,
        "freq": freq_label,
    }
    print(f"  {wf_name}: last={runs[0]['created_at'] if runs else 'N/A'}, status={runs[0]['conclusion'] if runs else 'N/A'}")

pages_runs = github_pages_runs()
pages_last = pages_runs[0]["created_at"] if pages_runs else None
pages_status = pages_runs[0]["conclusion"] if pages_runs else "unknown"

# ── HTML ──
HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="300">
<title>Cron Status · Retail Media</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Inter',-apple-system,sans-serif;background:#0a0c10;color:#e0e2e6;font-size:13px;min-height:100vh}}
.hdr{{background:linear-gradient(135deg,#111318,#1c212d);padding:14px 24px;border-bottom:1px solid #1e293b;display:flex;align-items:center;gap:12px}}
.hdr .logo{{width:32px;height:32px;border-radius:8px;background:linear-gradient(135deg,#3b82f6,#8b5cf6);display:flex;align-items:center;justify-content:center;font-weight:800;font-size:13px;color:#fff}}
.hdr h1{{font-size:16px;font-weight:700;background:linear-gradient(90deg,#3b82f6,#8b5cf6);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.hdr .ts{{margin-left:auto;font-size:10px;color:#52525b;font-family:monospace}}
.d{{padding:16px 24px;max-width:960px;margin:0 auto}}
.sec{{margin-bottom:24px}}
.sec h2{{font-size:11px;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:.8px;margin-bottom:10px;padding:0 4px;display:flex;align-items:center;gap:8px}}
.sec h2 .bar{{width:3px;height:14px;border-radius:2px;background:#8b5cf6}}
.card{{background:#111318;border:1px solid #1e293b;border-radius:10px;overflow:hidden;margin-bottom:8px}}
.card-head{{display:flex;align-items:center;gap:10px;padding:10px 14px;border-bottom:1px solid #1e293b}}
.card-head .icon{{width:28px;height:28px;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0}}
.icon-gh{{background:rgba(139,92,246,.15)}}
.card-head .name{{font-size:13px;font-weight:600;flex:1}}
.card-head .freq{{font-size:9px;color:#52525b;background:#161b22;padding:2px 8px;border-radius:4px;font-weight:500}}
.card-body{{padding:10px 14px}}
.row{{display:flex;align-items:center;justify-content:space-between;padding:5px 0;font-size:12px;border-bottom:1px solid rgba(255,255,255,.03)}}
.row:last-child{{border:none}}
.row .label{{color:#6b7c93;display:flex;align-items:center;gap:6px}}
.row .label .dot{{width:6px;height:6px;border-radius:50%;display:inline-block}}
.dot-ok{{background:#22c55e}}.dot-err{{background:#ef4444}}.dot-warn{{background:#f59e0b}}.dot-idle{{background:#64748b}}
.row .val{{font-weight:500;font-family:'SF Mono',Consolas,monospace;font-size:11px;color:#e0e2e6}}
.row .val a{{color:#60a5fa;text-decoration:none;font-family:inherit}}
.row .val a:hover{{text-decoration:underline}}
.row .val.muted{{color:#52525b}}
.status-ok{{color:#22c55e}}.status-err{{color:#ef4444}}.status-warn{{color:#f59e0b}}
.badge{{display:inline-block;padding:1px 7px;border-radius:4px;font-size:10px;font-weight:600}}
.bg-ok{{background:rgba(34,197,94,.15);color:#22c55e}}
.bg-err{{background:rgba(239,68,68,.15);color:#ef4444}}
.bg-warn{{background:rgba(245,158,11,.15);color:#f59e0b}}
.bg-idle{{background:rgba(100,116,139,.15);color:#64748b}}
.summary{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:16px}}
.sum-card{{background:#111318;border:1px solid #1e293b;border-radius:8px;padding:10px 14px;text-align:center}}
.sum-card .sv{{font-size:20px;font-weight:800;line-height:1.2}}
.sum-card .sl{{font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:.5px;margin-top:2px}}
.sc-blue .sv{{color:#60a5fa}}
.ftr{{padding:10px 24px;text-align:center;color:#1e293b;font-size:9px;border-top:1px solid #161b22}}
.show{{margin-top:8px;display:flex;flex-direction:column;gap:4px}}
.show-row{{display:flex;justify-content:space-between;padding:3px 0;font-size:11px}}
.show-row .sl{{color:#52525b}}
.show-row .sv{{color:#94a3b8;font-family:'SF Mono',Consolas,monospace;font-size:10px}}
@media(max-width:600px){{.d{{padding:12px}}.summary{{grid-template-columns:1fr 1fr}}}}
</style>
</head>
<body>
<div class="hdr">
<div class="logo">C</div>
<h1>Cron Status · Retail Media</h1>
<span class="ts" id="ts"></span>
</div>
<div class="d">

<script>
function fmt(t){{if(!t) return '—';var d=new Date(t),n=new Date(),diff=d-n;if(diff<0){{var m=Math.floor(-diff/60000);if(m<1) return 'just now';if(m<60) return m+'m ago';var h=Math.floor(m/60);var r=m%60;if(h<24) return h+'h '+r+'m ago';return Math.floor(h/24)+'d '+(h%24)+'h ago';}}else{{var m=Math.floor(diff/60000);if(m<1) return 'now';if(m<60) return 'in '+m+'m';if(m>=1440) return 'in '+Math.floor(m/1440)+'d';return 'in '+Math.floor(m/60)+'h '+(m%60)+'m';}}}}
function pad(n){{return n<10?'0'+n:''+n}}
function dateStr(d){{return d.getUTCFullYear()+'-'+pad(d.getUTCMonth()+1)+'-'+pad(d.getUTCDate())+' '+pad(d.getUTCHours())+':'+pad(d.getUTCMinutes())+' UTC'}}
document.getElementById('ts').textContent=dateStr(new Date());
</script>

<div class="summary">
<div class="sum-card sc-blue"><div class="sv">2</div><div class="sl">Workflows</div></div>
<div class="sum-card sc-blue"><div class="sv">10m</div><div class="sl">Interval</div></div>
<div class="sum-card sc-blue"><div class="sv">5</div><div class="sl">Dashboards</div></div>
<div class="sum-card sc-blue"><div class="sv">☁️</div><div class="sl">100% Cloud</div></div>
</div>

<!-- GITHUB ACTIONS WORKFLOWS -->
<div class="sec"><h2><span class="bar" style="background:#8b5cf6"></span>GitHub Actions Workflows</h2></div>
"""

for wid_name, wf_data in w_data.items():
    last = wf_data["last"]
    conclusion = wf_data["conclusion"]
    # Determine last 5 run times
    run_times = wf_data["runs"]
    next_html = next_run_from_iso(last, 10, "—")

    HTML += f"""
<div class="card">
<div class="card-head">
<div class="icon icon-gh">⚙</div>
<span class="name">{wf_data["name"]}</span>
<span class="freq">{wf_data["freq"]}</span>
</div>
<div class="card-body">
<div class="row"><span class="label"><span class="dot dot-ok"></span>Last run</span><span class="val">{tm_iso(last)}</span></div>
<div class="row"><span class="label"><span class="dot dot-idle"></span>Next run</span><span class="val">{next_html}</span></div>
<div class="row"><span class="label">Status</span><span class="val">{badge(conclusion)}</span></div>
<div class="row"><span class="label">Schedule</span><span class="val" style="font-size:10px;color:#52525b;font-weight:400">{wf_data["cron"]}</span></div>
<div class="row"><span class="label">Workflow</span><span class="val"><a href="https://github.com/SublimeRiad/retail-media/actions/workflows/{wid_name}.yml" target="_blank">View on GitHub →</a></span></div>
"""

    # Last 5 runs
    if run_times:
        HTML += f'''<div class="show">
'''
        for r in run_times:
            HTML += f'<div class="show-row"><span class="sl">{tm_iso(r["created_at"])}</span><span class="sv">{badge(r["conclusion"])}</span></div>\n'
        HTML += '</div>\n'

    HTML += """</div>
</div>
"""

# Pages Build
HTML += f"""
<div class="sec"><h2><span class="bar" style="background:#ef4444"></span>Pages Build & Deploy</h2></div>
<div class="card">
<div class="card-head">
<div class="icon icon-gh">📄</div>
<span class="name">GitHub Pages</span>
<span class="freq">{PAGES_FREQ}</span>
</div>
<div class="card-body">
<div class="row"><span class="label"><span class="dot dot-ok"></span>Last build</span><span class="val">{tm_iso(pages_last)}</span></div>
<div class="row"><span class="label">Status</span><span class="val">{badge(pages_status)}</span></div>
</div>
</div>

<!-- DASHBOARDS -->
<div class="sec"><h2><span class="bar" style="background:#3b82f6"></span>Dashboards</h2></div>

<div class="card">
<div class="card-body">
<div class="row"><span class="label"><span class="dot dot-ok"></span>retailmedia.html</span><span class="val"><a href="https://sublimeriad.github.io/retail-media/retailmedia.html">→ open</a></span></div>
<div class="row"><span class="label"><span class="dot dot-ok"></span>retailer.html</span><span class="val"><a href="https://sublimeriad.github.io/retail-media/retailer.html">→ open</a></span></div>
<div class="row"><span class="label"><span class="dot dot-ok"></span>wall-dashboard.html</span><span class="val"><a href="https://sublimeriad.github.io/retail-media/wall-dashboard.html">→ open</a></span></div>
<div class="row"><span class="label"><span class="dot dot-ok"></span>Retail-Media-Nsoc-Players.html</span><span class="val"><a href="https://sublimeriad.github.io/retail-media/Retail-Media-Nsoc-Players.html">→ open</a></span></div>
<div class="row"><span class="label"><span class="dot dot-ok"></span>nsoc-status.html</span><span class="val"><a href="https://sublimeriad.github.io/retail-media/nsoc-status.html">→ open</a></span></div>
</div>
</div>

</div>
<div class="ftr">Auto-refresh every 5 min · Cron Status v3 · {ts_date}</div>
<script>setInterval(function(){{location.reload();}},300000);</script>
</body>
</html>
"""

with open(OUTPUT, "w") as f:
    f.write(HTML)
print(f"[cron-status] Written to {OUTPUT}")
print("[cron-status] Done")
