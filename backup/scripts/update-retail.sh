#!/bin/bash
# Retail Media update - every 2 hours
cd /home/iots/.openclaw/workspace/iot-camera/scripts
export NODE_PATH=/home/iots/.openclaw/workspace/node_modules
LOG="/tmp/retail-cron.log"
echo "=== Retail Update $(date)" >> "$LOG"
node build-rmstatus.js 2>>"$LOG" || exit 1
cp /tmp/rmstatus-light/rmstatus.html /tmp/rm-push/
node /home/iots/.openclaw/workspace/iot-camera/scripts/build-iot-dash.js 2>>"$LOG" || exit 1
cp /tmp/rmstatus-light/iot-dashboard.html /tmp/rm-push/
# NSOC PC Status Dashboard
python3 /home/iots/.openclaw/workspace/iot-camera/scripts/build-nsoc-dash.py 2>>"$LOG"
cp /home/iots/.openclaw/workspace/iot-camera/rmstatus-push/Retail-Media-Nsoc-Players.html /tmp/rm-push/
cd /tmp/rm-push
git add rmstatus.html iot-dashboard.html retailmedia.html Retail-Media-Nsoc-Players.html
git commit -m "Auto-retail $(date '+%Y-%m-%d %H:%M')" || true
git pull origin master --rebase || true
git push origin master 2>>"$LOG"
echo "OK" >> "$LOG"
