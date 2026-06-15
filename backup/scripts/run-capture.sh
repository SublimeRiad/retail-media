#!/bin/bash
# Camera capture runner with Gotify notifications
source /home/iots/.local/bin/notify
NOTIFY="$HOME/.local/bin/notify"

cd /home/iots/.openclaw/workspace/iot-camera
export NODE_PATH=/home/iots/.openclaw/workspace/node_modules

"$NOTIFY" "📸 Capture" "Démarrage capture caméras..." 3

start=$(date +%s)
node capture-cameras.js --cron 2>&1
exit_code=$?
end=$(date +%s)
dur=$((end - start))

if [ $exit_code -eq 0 ]; then
  # Count captured images
  US_COUNT=$(ls lulu/*.jpg ummu-suqeim/*.jpg al-warqa/*.jpg 2>/dev/null | wc -l)
  "$NOTIFY" "✅ Capture OK" "Terminée en ${dur}s · ${US_COUNT} photos" 3
else
  "$NOTIFY" "❌ Capture FAILED" "Exit code $exit_code après ${dur}s" 8
fi
