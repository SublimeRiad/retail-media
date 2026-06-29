#!/bin/bash
# Auto-update Retail Media IoT Dashboard + IoT Admin Dashboard
cd /home/iots/.openclaw/workspace/iot-camera/scripts
export NODE_PATH=/home/iots/.openclaw/workspace/node_modules

# Gotify notification setup
GOTIFY_URL="http://localhost:8090"
GOTIFY_TOKEN="iot-ac52025c500e1f6eafb7cab9886560e5"

notify() {
  local title="$1" msg="$2" pri="${3:-3}"
  curl -s -X POST "$GOTIFY_URL/message" \
    -H "Content-Type: application/json" \
    -H "X-Gotify-Key: $GOTIFY_TOKEN" \
    -d "{\"title\":\"$title\",\"message\":\"$msg\",\"priority\":$pri}" &>/dev/null
}

notify "🔄 RM Dashboard" "Update started" 3

# 1. Scrape live data from IoT Admin Console
echo "[1/4] Scraping IoT Admin Console..."
node scrape-iot-admin.js || { notify "❌ RM Dashboard" "scrape-iot-admin FAILED" 8; exit 1; }

# 2. Generate Retail Media Status (from scraped data)
echo "[2/4] Building retailmedia.html..."
node build-rmstatus.js || { notify "❌ RM Dashboard" "build-rmstatus FAILED" 8; exit 1; }
cp /tmp/rmstatus-light/rmstatus.html /tmp/rm-push/retailmedia.html

# 3. Generate IoT Admin dashboard (from scraped data)
echo "[3/4] Building iot-dashboard.html..."
node build-iot-dash.js || { notify "❌ RM Dashboard" "build-iot-dash FAILED" 8; exit 1; }
cp /tmp/rmstatus-light/iot-dashboard.html /tmp/rm-push/

# 4. Generate Wall dashboard (from scraped data)
echo "[4/4] Building wall-dashboard.html..."
node build-wall-dash.js || { notify "❌ RM Dashboard" "build-wall-dash FAILED" 8; exit 1; }
cp /tmp/rmstatus-light/wall-dashboard.html /tmp/rm-push/

# 5a. Generate retailer.html honeycomb dashboard
echo "[5a/6] Building retailer.html..."
node build-retailer.js || { notify "❌ RM Dashboard" "build-retailer FAILED" 8; exit 1; }
cp /tmp/rmstatus-light/retailer.html /tmp/rm-push/

# 5b. Generate cron-status.html with live timestamps
echo "[5b/6] Building cron-status.html..."
python3 /home/iots/.openclaw/workspace/iot-camera/scripts/build-cron-status.py || {
  notify "⚠ RM Dashboard" "build-cron-status FAILED" 5
  echo "[WARN] build-cron-status failed, continuing anyway"
}

# 6. Push all to GitHub (filenames match GitHub URLs)
cd /tmp/rm-push
git add retailmedia.html iot-dashboard.html wall-dashboard.html retailer.html cron-status.html
git commit -m "Auto-update $(date '+%Y-%m-%d %H:%M')" || true
git pull origin master --rebase || true
git push origin master

notify "✅ RM Dashboard" "3 pages + cron-status updated OK" 3
echo "[OK] $(date)"
