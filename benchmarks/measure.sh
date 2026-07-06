#!/usr/bin/env bash
# measure.sh - reproduce the Phase-H benchmark numbers against the target VM.
#
# Deploys the current src/ tree, launches it at 1280x720 (the mandated
# minimum test resolution), and reports:
#   - login-to-visible proxy: FIRST_PAINT proc_s from the app's own startup log
#   - idle CPU: pidstat average over 30 s with no windows open
#   - idle RSS: VmRSS read from /proc after the 30 s sample settles
#
# Usage: ./benchmarks/measure.sh [resolution]
#   ./benchmarks/measure.sh            # 1280x720 (default, mandated minimum)
#   ./benchmarks/measure.sh 1920x1080  # cross-check at a larger resolution
set -euo pipefail

VM="vboxuser@127.0.0.1"
PORT=2222
SSH="ssh -p $PORT $VM"
RES="${1:-1280x720}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "== Deploying current src/ to VM =="
$SSH "mkdir -p ~/jiopc-home/src"
rsync -az --delete -e "ssh -p $PORT" "$ROOT/src/" "$VM:~/jiopc-home/src/"

echo "== Setting resolution to $RES =="
$SSH "DISPLAY=:0 xrandr --output Virtual1 --mode $RES"

echo "== Restarting the app =="
# The backgrounded remote process keeps this ssh session's channel open even
# with nohup+disown (its pty is still attached), so bound the wait with
# timeout; the launch itself completes in ~2s well inside that window.
timeout 10 $SSH "for pid in \$(pgrep -f 'src/main.py'); do \
    [ \"\$(cat /proc/\$pid/comm 2>/dev/null)\" = python3 ] && kill \$pid 2>/dev/null || true; \
  done; sleep 1; \
  rm -f /tmp/jiopc-startup.log; \
  cd ~/jiopc-home && DISPLAY=:0 nohup python3 src/main.py </dev/null >/tmp/jiopc.log 2>&1 & \
  disown; sleep 2" || true

PID=$($SSH "pgrep -f 'python3 src/main.py'" | tail -1)
if [ -z "$PID" ]; then
  echo "FAILED: app did not start; see /tmp/jiopc.log on the VM"
  exit 1
fi
echo "App PID on VM: $PID"

echo "== First paint =="
FIRST_PAINT=$($SSH "tail -1 /tmp/jiopc-startup.log")
echo "$FIRST_PAINT"

echo "== Idle CPU (30 s pidstat, no windows open) =="
$SSH "pidstat -p $PID 1 30" | tee /tmp/jiopc_pidstat_$$.txt
AVG_CPU=$(tail -1 /tmp/jiopc_pidstat_$$.txt | awk '{print $NF == "python3" ? $(NF-2) : $(NF-1)}')
rm -f /tmp/jiopc_pidstat_$$.txt

echo "== Idle RSS =="
RSS_KB=$($SSH "grep VmRSS /proc/$PID/status" | awk '{print $2}')
RSS_MB=$(awk "BEGIN{printf \"%.1f\", $RSS_KB/1024}")
echo "VmRSS: ${RSS_MB} MB"

echo
echo "== Summary (resolution=$RES) =="
echo "$FIRST_PAINT"
echo "idle_cpu_pct_avg_30s=$AVG_CPU"
echo "idle_rss_mb=$RSS_MB"
