#!/bin/bash

# IoT Deploy Skill - Find & deploy NVIDIA J30 modules on the network
# Usage: bash deploy.sh [--scan|--deploy]

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WS_DIR="$(cd "$SCRIPT_DIR/../.." 2>/dev/null && pwd)"
CREDS_FILE="$WS_DIR/.iot_deploy_creds"

if [ -z "$IOT_GITHUB_TOKEN" ]; then
    if [ -f "$CREDS_FILE" ]; then source "$CREDS_FILE"
    elif [ -f "/home/iots/.openclaw/workspace/.iot_deploy_creds" ]; then source "/home/iots/.openclaw/workspace/.iot_deploy_creds"
    fi
fi

if [ -z "$IOT_GITHUB_TOKEN" ]; then
    echo "ERROR: Missing credentials. Source .iot_deploy_creds first."
    exit 1
fi

MODE="${1:-deploy}"
IOT_S_DIR="$WS_DIR/iot_s"
SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=10 -o PubkeyAuthentication=no"
TARGET_DIR="/home/$IOT_REMOTE_USER/iot_install"

echo "🔍 Scanning for IoT devices..."

INVENTORY=""

# Attempt sudo nmap scan
if echo "$IOT_SCP_PASS" | sudo -S true 2>/dev/null; then
    NMAP_OUT=$(echo "$IOT_SCP_PASS" | sudo -S nmap -sn $IOT_NETWORK 2>/dev/null)
    if [ -n "$NMAP_OUT" ]; then
        INVENTORY=$(echo "$NMAP_OUT" | python3 -c "
import sys, re
lines = sys.stdin.read().split('\n')
devices = {}
ip = ''
for line in lines:
    m = re.search(r'Nmap scan report for (.+)', line)
    if m:
        ip = m.group(1).strip('()')
        continue
    m = re.search(r'MAC Address: ([0-9A-F:]+)', line, re.I)
    if m and ip:
        mac = m.group(1).upper()
        if 'NVIDIA' in line or mac.startswith('3C:6D') or mac.startswith('54:EF:33'):
            devices[ip] = mac
for ip, mac in sorted(devices.items()):
    print(f'{ip}\t{mac}')
")
    fi
fi

# Fallback: ARP cache
if [ -z "$INVENTORY" ]; then
    INVENTORY=$(ip neigh show 2>/dev/null | grep -iE "3c:6d|54:ef:33" | awk '{print $1 "\t" $5}' | sort -u)
fi

if [ -z "$INVENTORY" ]; then
    echo "❌ No IoT devices detected on the network."
    exit 1
fi

COUNT=$(echo "$INVENTORY" | wc -l)
echo "✅ Found $COUNT IoT device(s):"
echo ""
echo "$INVENTORY" | while IFS=$'\t' read -r ip mac; do
    echo "   📍 $ip  →  $mac"
done
echo ""

if [ "$MODE" = "--scan" ] || [ "$MODE" = "scan" ] || [ "$MODE" = "--find" ] || [ "$MODE" = "find" ]; then
    echo "────────────────────────────────"
    echo "Total: $COUNT IoT device(s) detected"
    exit 0
fi

echo "🚀 Deploying to $COUNT devices..."

while read -u 3 -r IP MAC; do
    echo "═══ $IP ═══"
    sshpass -p "$IOT_INITIAL_PASS" ssh $SSH_OPTS ${IOT_REMOTE_USER}@${IP} "mkdir -p $TARGET_DIR" 2>/dev/null
    sshpass -p "$IOT_INITIAL_PASS" scp $SSH_OPTS "$IOT_S_DIR/scp_info_send.sh" "$IOT_S_DIR/All_in_one.sh" ${IOT_REMOTE_USER}@${IP}:$TARGET_DIR/ 2>/dev/null

    if [ $? -eq 0 ]; then
        REMOTE_CMD="cd $TARGET_DIR && \
            if ! command -v sshpass &> /dev/null; then echo '$IOT_INITIAL_PASS' | sudo -S apt-get install -y sshpass -qq 2>/dev/null; fi && \
            wget -q --header='Authorization: token $IOT_GITHUB_TOKEN' --header='Accept: application/vnd.github.v3.raw' -O aioo_j30_bootstrap.sh '$IOT_GITHUB_URL' && \
            chmod +x aioo_j30_bootstrap.sh && \
            echo '$IOT_INITIAL_PASS' | sudo -S ./aioo_j30_bootstrap.sh && \
            sed -i 's/sudo cat/echo \"$IOT_NEW_PASS\" | sudo -S cat/g' scp_info_send.sh && \
            chmod +x scp_info_send.sh && ./scp_info_send.sh && \
            cd ~ && rm -rf $TARGET_DIR && echo 'SUCCESS'"
        SSH_OUTPUT=$(sshpass -p "$IOT_INITIAL_PASS" ssh -n $SSH_OPTS ${IOT_REMOTE_USER}@${IP} "$REMOTE_CMD" 2>/dev/null)
        echo "$SSH_OUTPUT" | grep "^AIOO_DATA_TAG:" | sed 's/AIOO_DATA_TAG://' >> "$WS_DIR/skills/iot-deploy/devices.txt"
        echo "   ✅ $IP done"
    else
        echo "   ❌ $IP connection failed"
    fi
    echo ""
done 3<<< "$INVENTORY"

echo "────────────────────────────────"
echo "✅ Done"

if [ -f "$WS_DIR/skills/iot-deploy/devices.txt" ] && [ -s "$WS_DIR/skills/iot-deploy/devices.txt" ]; then
    curl -s -X POST "https://api.telegram.org/bot${IOT_BOT_TOKEN}/sendDocument" \
         -F chat_id="${IOT_CHAT_ID}" \
         -F document="@$WS_DIR/skills/iot-deploy/devices.txt" > /dev/null
    echo "📤 Report sent to Telegram"
fi
