#!/bin/bash
# IoT Health — check ping, SSH, and camera for all known IoTs
# Usage: bash health.sh

WS_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
source "$WS_DIR/.iot_deploy_creds" 2>/dev/null || source "$WS_DIR/.iot_deploy_creds"

SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=5 -o PubkeyAuthentication=no"

echo "🔍 Health check..."
echo ""

DEVICES=(
  "192.168.30.109|3C:6D:66:BA:54:3F|A1-00-5E-ED-01-6D"
  "192.168.30.161|3C:6D:66:BA:47:B4|A1-00-5E-ED-01-6C"
  "192.168.31.6|3C:6D:66:BA:57:87|A1-00-5E-ED-02-DF"
)

ONLINE=0
CAMERAS_OK=0

for DEV in "${DEVICES[@]}"; do
  IFS='|' read -r IP MAC ONBOARD_MAC <<< "$DEV"

  echo "📍 $IP ($MAC)"

  # Ping
  if ping -c1 -W2 "$IP" &>/dev/null; then
    echo "   ✅ Ping OK"
    ((ONLINE++))
  else
    echo "   ❌ Ping FAIL"
    echo ""
    continue
  fi

  # SSH
  if sshpass -p "$IOT_NEW_PASS" ssh $SSH_OPTS aioo@"$IP" "echo ok" &>/dev/null; then
    echo "   ✅ SSH OK"
  else
    echo "   ❌ SSH FAIL"
    echo ""
    continue
  fi

  # Device ID
  ID=$(sshpass -p "$IOT_NEW_PASS" ssh $SSH_OPTS aioo@"$IP" "cat /opt/hex-device-id 2>/dev/null" 2>/dev/null)
  if [ -n "$ID" ]; then
    echo "   🆔 Device: $ID"
  fi

  echo ""
done

echo "━━━━━━━━━━━━━━━━━━"
echo "$ONLINE/3 online"
