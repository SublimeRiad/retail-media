#!/bin/bash
# update-retail.sh — v3: uses API instead of Puppeteer
cd /home/iots/.openclaw/workspace/iot-camera/scripts
export NODE_PATH=/home/iots/.openclaw/workspace/node_modules

notify() { true; }

echo "[1/5] Fetching IoT data from API..."
node fetch-iot-api.js || { notify "❌ API" "fetch-iot-api FAILED" 8; exit 1; }

echo "[2/5] Building retailmedia.html..."
node build-rmstatus.js || { notify "❌ RM Status" "build-rmstatus FAILED" 8; exit 1; }
cp /tmp/rmstatus-light/rmstatus.html /tmp/rm-push/retailmedia.html

echo "[3/5] Building retailer.html..."
node build-retailer.js || { notify "❌ Retailer" "build-retailer FAILED" 8; exit 1; }
cp /tmp/rmstatus-light/retailer.html /tmp/rm-push/retailer.html

echo "[4/5] Building wall-dashboard.html..."
node build-wall-dash.js || { notify "❌ Wall" "build-wall-dash FAILED" 8; exit 1; }
cp /tmp/rmstatus-light/wall-dashboard.html /tmp/rm-push/wall-dashboard.html

echo "[5/5] Pushing to GitHub..."
cd /tmp/rm-push
git add retailmedia.html retailer.html wall-dashboard.html
git commit -m "Auto-update $(date '+%Y-%m-%d %H:%M UTC')" || true
git pull origin master --rebase || true
git push origin master

echo "[OK] All dashboards updated"
