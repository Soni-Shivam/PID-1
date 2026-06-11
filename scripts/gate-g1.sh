#!/usr/bin/env bash
# gate-g1.sh - Fresh-VM .deb proof (Roadmapv2 Gate G1, closes debt D2).
#
# MUST be run against a freshly RESTORED 00-clean snapshot (no dev deps, no
# jiopc-home installed). It first asserts cleanliness via a SENTINEL: if the
# runtime deps are already present, the snapshot restore did NOT take effect
# (this is the exact failure that invalidated earlier attempts) and the script
# aborts so we never record a false pass.
#
# Then it installs the .deb the way a judge would, verifies dependency
# resolution + autostart wiring + a real run, and prints a PASS/FAIL report.
#
# Usage: ./scripts/gate-g1.sh
set -uo pipefail

PORT=2222
VM="vboxuser@127.0.0.1"
SSH="ssh -p $PORT -o ConnectTimeout=8 $VM"
SCP="scp -P $PORT"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEB="$ROOT/dist/jiopc-home_0.1.0_all.deb"
DEPS="python3-pyqt5 python3-xdg python3-xlib python3-requests papirus-icon-theme"

fail() { echo "GATE G1: FAIL - $1"; exit 1; }
say()  { echo; echo "=== $1 ==="; }

[ -f "$DEB" ] || fail "no .deb at $DEB (run packaging/build-deb.sh)"
$SSH true 2>/dev/null || fail "cannot SSH to the VM on port $PORT"

# --- SENTINEL: prove the VM is actually 00-clean ----------------------------
say "Sentinel: confirm 00-clean (deps absent, package absent)"
if $SSH "dpkg -s jiopc-home" >/dev/null 2>&1; then
  fail "jiopc-home is ALREADY installed -> this is NOT a fresh 00-clean restore"
fi
present=""
for p in $DEPS; do
  if $SSH "dpkg -s $p" >/dev/null 2>&1; then present="$present $p"; fi
done
if [ -n "$present" ]; then
  fail "runtime deps already present ->$present
       The 00-clean snapshot restore did NOT take effect. Restore it again in
       VirtualBox (Machine > Snapshots > 00-clean > Restore), boot into LxQt,
       then re-run this script."
fi
echo "OK: package absent, all runtime deps absent - VM is genuinely clean."

# --- network reachability (apt must reach the archive) ----------------------
say "Network: apt can reach the Ubuntu archive"
$SSH "sudo apt-get update -qq" >/dev/null 2>&1 || \
  fail "apt-get update failed - the clean VM has no archive access (needed to pull deps)"
echo "OK: apt-get update succeeded."

# --- install exactly as a judge would (resolves Depends) --------------------
say "Install: sudo apt install ./jiopc-home_0.1.0_all.deb"
$SCP "$DEB" "$VM:/tmp/jiopc-home.deb" >/dev/null 2>&1 || fail "scp of .deb failed"
$SSH "sudo apt-get install -y /tmp/jiopc-home.deb" 2>&1 | tail -6
$SSH "dpkg -s jiopc-home" >/dev/null 2>&1 || fail "package not installed after apt install"

# --- verify dependency resolution + files -----------------------------------
say "Verify: deps pulled in + files placed"
for p in $DEPS; do
  $SSH "dpkg -s $p" >/dev/null 2>&1 || fail "dependency $p was NOT pulled in by apt"
done
echo "OK: all $(echo $DEPS | wc -w) deps resolved by apt."
$SSH "test -x /usr/bin/jiopc-home" || fail "/usr/bin/jiopc-home missing"
$SSH "test -f /etc/xdg/autostart/jiopc-home.desktop" || fail "autostart entry missing"
$SSH "test -f /usr/lib/jiopc-home/themes/dark.json" || fail "themes not installed"
$SSH "desktop-file-validate /etc/xdg/autostart/jiopc-home.desktop" 2>&1 || \
  echo "WARN: desktop-file-validate reported issues"
echo "OK: launcher, autostart entry, and themes all present."

# --- run it from the installed location --------------------------------------
say "Run: launch the installed shell and check first paint"
$SSH "rm -f /tmp/jiopc-startup.log /tmp/jiopc-g1.log; \
      for pid in \$(pgrep -f 'jiopc-home/main\.py'); do kill \$pid 2>/dev/null; done; \
      DISPLAY=:0 nohup /usr/bin/jiopc-home >/tmp/jiopc-g1.log 2>&1 & \
      sleep 3; \
      echo '--- startup log ---'; cat /tmp/jiopc-startup.log 2>/dev/null; \
      echo '--- errors? ---'; grep -iE 'error|traceback' /tmp/jiopc-g1.log || echo none; \
      echo '--- windows ---'; DISPLAY=:0 wmctrl -l 2>/dev/null | grep -i jiopc || echo 'NO jiopc windows'"

echo
echo "=========================================================="
echo "GATE G1 base install/run checks complete. Review output above."
echo "Login-to-visible = (FIRST_PAINT epoch - SESSION_START epoch)."
echo "Next: D6 Flatpak match - run ./scripts/gate-g1.sh flatpak"
echo "=========================================================="
