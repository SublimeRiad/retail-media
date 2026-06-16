#!/bin/bash
# Retail Media IoT Dashboard — Auto-update script
# Runs: build-rmstatus.js → git commit + push

REPO_DIR="/tmp/rm-push"
BUILD_SCRIPT="/tmp/build-branded.js"

# Rebuild the dashboard
export NODE_PATH=/home/iots/.openclaw/workspace/node_modules
node "$BUILD_SCRIPT" || exit 1

# Push to GitHub
cd "$REPO_DIR" || exit 1
cp /tmp/rmstatus-light/rmstatus.html .
git add rmstatus.html
git commit -m "Auto-update dashboard $(date '+%Y-%m-%d %H:%M')" || true
git pull origin master --rebase || true
git push origin master 2>&1

echo "[OK] Dashboard updated $(date)"
