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

$SSH "pkill -f 'jiopc-home/(src|experiments)/' || true; \
  cd ~/jiopc-home && DISPLAY=:0 nohup python3 $TARGET >/tmp/jiopc.log 2>&1 & \
  sleep 1; head -20 /tmp/jiopc.log"
