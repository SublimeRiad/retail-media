#!/bin/bash

# NSOC Skill - Fetch NUC/media player status & data consumption
# Usage: ./nsoc.sh [--slack]

set -e

# Auto-load credentials if env vars not set
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CREDS_FILE="$(cd "$SCRIPT_DIR/../.." 2>/dev/null && pwd)/.nsoc_creds"
if [ -z "$GLPI_API_URL" ] && [ -f "$CREDS_FILE" ]; then
    source "$CREDS_FILE"
elif [ -z "$GLPI_API_URL" ] && [ -f "$HOME/.nsoc_creds" ]; then
    source "$HOME/.nsoc_creds"
elif [ -z "$GLPI_API_URL" ] && [ -f "/home/iots/.openclaw/workspace/.nsoc_creds" ]; then
    source "/home/iots/.openclaw/workspace/.nsoc_creds"
fi

MODE="${1:-normal}"

RAW_TOKEN=$(curl -s -X GET "$GLPI_API_URL/initSession" \
    -H "App-Token: $GLPI_APP_TOKEN" \
    -H "Authorization: user_token $GLPI_USER_TOKEN")

SESSION_TOKEN=$(echo "$RAW_TOKEN" | grep -o '"session_token":"[^"]*"' | awk -F'"' '{print $4}')

if [ -z "$SESSION_TOKEN" ]; then
    echo "Error: Failed to retrieve session token."
    exit 1
fi

TMPFILE=$(mktemp)
trap "rm -f $TMPFILE" EXIT

curl -s -X GET "$GLPI_API_URL/search/Computer?expand_dropdowns=true&withplugins=true&range=0-2000" \
    -H "Session-Token: $SESSION_TOKEN" \
    -H "App-Token: $GLPI_APP_TOKEN" \
    -H "Content-Type: application/json" > "$TMPFILE"

# Field mappings (search API with expand_dropdowns=true):
# 1 = Name, 3 = Location, 31 = Status (emoji), 45 = Comment
# 901 = Tag (otherserial), 76670 = Data percent, 76666 = SIM phone

if [ "$MODE" = "--slack" ]; then
python3 -c "
import sys, json
with open('$TMPFILE') as f:
    data = json.load(f)
total = data.get('totalcount', 0)
devices = data.get('data', [])
online = 0
offline = []

GREEN = '\U0001f7e2'
RED = '\U0001f534'
YELLOW = '\U0001f7e1'
CROSS = '\u274c'
SATELLITE = '\U0001f4e1'

for pc in devices:
    status = str(pc.get('31', ''))
    name = pc.get('1', 'Unknown')
    if GREEN in status:
        online += 1
    else:
        tag = str(pc.get('901', '') or '')
        location = str(pc.get('3', '') or '')
        comment = str(pc.get('45', '') or '')
        percent = str(pc.get('76670', '0 %'))
        offline.append((name, tag, location, comment, percent))

print(SATELLITE + ' NSOC Device Status')
print('=' * 35)
print('Online: ' + str(online) + '    Offline: ' + str(len(offline)))
print()

for name, tag, location, comment, percent in offline:
    p = percent.strip()
    if p in ('0 %', '0%', '0.0 %'):
        icon = GREEN
    else:
        try:
            val = float(p.replace('%','').replace(',','.').strip())
            if val > 80:
                icon = RED
            elif val > 50:
                icon = YELLOW
            else:
                icon = GREEN
        except:
            icon = YELLOW

    print(CROSS + ' ' + name)
    print('   Tag: ' + tag)
    print('   Location: ' + location)
    print('   Data: ' + percent + ' ' + icon)
    if comment:
        print('   ' + comment)
    print()

print('=' * 35)
print('Total: ' + str(total) + ' devices | ' + str(len(offline)) + ' offline')
"
else
python3 -c "
import sys, json
with open('$TMPFILE') as f:
    data = json.load(f)
devices = data.get('data', [])
total = data.get('totalcount', 0)
offline_count = 0
online_count = 0

GREEN = '\U0001f7e2'

print()
print('=== DEVICE STATUS ===')
for pc in devices:
    status = str(pc.get('31', ''))
    name = str(pc.get('1', 'Unknown') or 'Unknown')
    if GREEN in status:
        online_count += 1
    else:
        tag = str(pc.get('901', '') or '')
        comment = str(pc.get('45', '') or '')
        percent = str(pc.get('76670', '0 %'))
        location = str(pc.get('3', 'Undefined') or 'Undefined')
        print('- Name: ' + name + ' | Tag: ' + tag + ' | Comment: ' + comment + ' | Data%: ' + percent + ' | Location: ' + location)
        offline_count += 1

print()
print('Total online devices: ' + str(online_count))
print('Total offline devices: ' + str(offline_count))
"
fi
