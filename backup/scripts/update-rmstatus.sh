#!/bin/bash
# Auto-update Retail Media IoT Dashboard + IoT Admin Dashboard
cd /home/iots/.openclaw/workspace/iot-camera/scripts
export NODE_PATH=/home/iots/.openclaw/workspace/node_modules

# Gotify notification setup
GOTIFY_URL="http://localhost:8090"
GOTIFY_TOKEN="Ac8-pylKp3tvcMd"

notify() {
  local title="$1" msg="$2" pri="${3:-3}"
  curl -s -X POST "$GOTIFY_URL/message" \
    -H "Content-Type: application/json" \
    -H "X-Gotify-Key: $GOTIFY_TOKEN" \
    -d "{\"title\":\"$title\",\"message\":\"$msg\",\"priority\":$pri}" &>/dev/null
}

notify "🔄 RM Dashboard" "Update started" 3

# 1. Generate RM status dashboard
echo "[1/3] Building rmstatus.html..."
node build-rmstatus.js || { notify "❌ RM Dashboard" "build-rmstatus FAILED" 8; exit 1; }
cp /tmp/rmstatus-light/rmstatus.html /tmp/rm-push/

# 2. Generate IoT Admin dashboard
echo "[2/3] Building iot-dashboard.html..."
node /home/iots/.openclaw/workspace/iot-camera/scripts/build-iot-dash.js || { notify "❌ RM Dashboard" "build-iot-dash FAILED" 8; exit 1; }
cp /tmp/rmstatus-light/iot-dashboard.html /tmp/rm-push/

# 3. Generate Wall dashboard
echo "[3/3] Building wall-dashboard.html..."
node /home/iots/.openclaw/workspace/iot-camera/scripts/build-wall-dash.js || { notify "❌ RM Dashboard" "build-wall-dash FAILED" 8; exit 1; }
cp /tmp/rmstatus-light/wall-dashboard.html /tmp/rm-push/

# 4. Copy rmstatus as retailmedia (same data, grouped by venue)
echo "[4/4] Copying retailmedia.html..."
cp /tmp/rm-push/rmstatus.html /tmp/rm-push/retailmedia.html

# 5. Push all to GitHub
cd /tmp/rm-push
git add rmstatus.html iot-dashboard.html wall-dashboard.html
git commit -m "Auto-update $(date '+%Y-%m-%d %H:%M')" || true
git pull origin master --rebase || true
git push origin master

notify "✅ RM Dashboard" "3 pages updated OK" 3
echo "[OK] $(date)"
