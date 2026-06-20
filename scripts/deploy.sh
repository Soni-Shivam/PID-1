#!/usr/bin/env bash
# Deploy src/ + experiments/ to the VM and (re)start the app.
# Usage:
#   ./scripts/deploy.sh                  # sync + run src/main.py
#   ./scripts/deploy.sh experiments/me01_blank_window.py   # sync + run a specific script
set -euo pipefail

VM="vboxuser@127.0.0.1"
PORT=2222
SSH="ssh -p $PORT $VM"
TARGET="${1:-src/main.py}"

$SSH "mkdir -p ~/jiopc-home/src ~/jiopc-home/experiments"
rsync -az --delete -e "ssh -p $PORT" ./src/ "$VM:~/jiopc-home/src/"
rsync -az --delete -e "ssh -p $PORT" ./experiments/ "$VM:~/jiopc-home/experiments/"

# Ship runtime secrets (gitignored .env: NEWS_API_KEY etc.) so the app can read
# them via core.secrets. Never committed; lives only on the dev box and the VM.
[ -f .env ] && scp -P "$PORT" .env "$VM:~/jiopc-home/.env" >/dev/null 2>&1 || true

# Kill any running instance. Match main.py/experiment cmdlines but only kill
# real python interpreters (comm==python3), never the bash wrapper running this
# command (which also contains the path) - avoids the pkill self-kill trap.
$SSH "for pid in \$(pgrep -f 'jiopc-home|main\.py|experiments/'); do \
    [ \"\$(cat /proc/\$pid/comm 2>/dev/null)\" = python3 ] && kill \$pid 2>/dev/null || true; \
  done; sleep 1; \
  cd ~/jiopc-home && DISPLAY=:0 nohup python3 $TARGET >/tmp/jiopc.log 2>&1 & \
  sleep 1.5; head -20 /tmp/jiopc.log"
