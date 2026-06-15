#!/bin/bash
# IoT Alerts — checks for devices needing attention and sends Gotify notification
NOTIFY="$HOME/.local/bin/notify"

# Last 4h errors/warnings — check if devices have high error counts
# We use the Admin Console data (this is a lightweight check)
# For now: check the latest capture log for error patterns

LOG="/home/iots/.openclaw/workspace/iot-camera/capture.log"
if [ -f "$LOG" ]; then
  ERRORS=$(grep -c "ERROR\|error\|fail" "$LOG" 2>/dev/null || echo 0)
  if [ "$ERRORS" -gt 0 ]; then
    "$NOTIFY" "⚠️ Capture Errors" "$ERRORS errors in last capture log" 8
  fi
fi

# Check if Gotify server is up
if ! curl -sf http://localhost:8090 > /dev/null 2>&1; then
  "$NOTIFY" "🔴 Gotify Down" "Gotify server unreachable!" 10
fi

# System health
LOAD=$(awk '{print $1}' /proc/loadavg)
DISK=$(df -h / | awk 'NR==2 {print $5}')
"$NOTIFY" "🖥️ System Health" "Load: $LOAD | Disk: $DISK" 2
