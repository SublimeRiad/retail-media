#!/bin/bash
# Wall dashboard update - once per day
cd /home/iots/.openclaw/workspace/iot-camera/scripts
export NODE_PATH=/home/iots/.openclaw/workspace/node_modules
LOG="/tmp/wall-cron.log"
echo "=== Wall Update $(date)" >> "$LOG"
node /home/iots/.openclaw/workspace/iot-camera/scripts/build-wall-dash.js 2>>"$LOG" || exit 1
cp /tmp/rmstatus-light/wall-dashboard.html /tmp/rm-push/
cd /tmp/rm-push
git add wall-dashboard.html
git commit -m "Auto-wall $(date '+%Y-%m-%d %H:%M')" || true
git pull origin master --rebase || true
git push origin master 2>>"$LOG"
echo "OK" >> "$LOG"
