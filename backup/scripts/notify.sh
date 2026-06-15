#!/bin/bash
# Gotify notification helper
# Usage: notify.sh "Title" "Message" [priority]
GOTIFY_URL="http://localhost:8090"
GOTIFY_TOKEN="***"

title="${1:-Notification}"
msg="${2:-}"
pri="${3:-3}"

curl -s -X POST "$GOTIFY_URL/message" \
  -H "Content-Type: application/json" \
  -H "X-Gotify-Key: $GOTIFY_TOKEN" \
  -d "{\"title\":\"$title\",\"message\":\"$msg\",\"priority\":$pri}" > /dev/null
