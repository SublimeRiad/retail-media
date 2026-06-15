#!/bin/bash
# IoT Onboard Skill - Credential Helper
# Fetches credentials from Bitwarden for the AiOO Onboarding portal
# Usage: source .bw_session && ./iot_onboard.sh

set -e

BW_ITEM="AiOO Onboarding"

# Check if bw is available
if ! command -v bw &> /dev/null; then
    echo "ERROR: Bitwarden CLI (bw) not found. Install with: npm install -g @bitwarden/cli"
    exit 1
fi

# Check bw status
STATUS=$(bw status 2>/dev/null | python3 -c "import sys, json; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null || echo "unknown")

if [ "$STATUS" = "unknown" ] || [ -z "$STATUS" ]; then
    echo "ERROR: Not authenticated. Run: export BW_CLIENTID='...' && export BW_CLIENTSECRET='...' && bw login --apikey"
    exit 1
fi

if [ "$STATUS" != "unlocked" ]; then
    echo "ERROR: Vault is locked. Run: bw unlock and set BW_SESSION"
    exit 1
fi

echo "Fetching credentials for '$BW_ITEM' from Bitwarden..."
CREDS=$(bw get item "$BW_ITEM" 2>/dev/null)

if [ $? -ne 0 ] || [ -z "$CREDS" ]; then
    echo "ERROR: Item '$BW_ITEM' not found in vault."
    echo "Create a Login item named '$BW_ITEM' with username and password."
    exit 1
fi

USERNAME=$(echo "$CREDS" | python3 -c "import sys, json; print(json.load(sys.stdin)['login']['username'])")
PASSWORD=$(echo "$CREDS" | python3 -c "import sys, json; print(json.load(sys.stdin)['login']['password'])")

echo "USERNAME=$USERNAME"
echo "PASSWORD=${PASSWORD:0:4}****"
echo ""
echo "Credentials ready for browser automation."
