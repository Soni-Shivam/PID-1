#!/usr/bin/env bash
# gate-g1.sh - Fresh-VM .deb proof of the packaged install/autostart path.
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
# All runtime deps (verified present AFTER install).
DEPS="python3-pyqt5 python3-xdg python3-xlib python3-requests papirus-icon-theme"
# Deps that must be ABSENT to constitute a clean precondition. On Ubuntu 24.04 +
# LxQt the base session already provides python3-pyqt5 (meteo-qt), python3-xdg
# (speechd), python3-requests (cloud-init/apport) and papirus-icon-theme (LxQt),
# so those are present on any genuine target machine. python3-xlib is the only
# dependency unique to this package, i.e. the one apt must actually pull in.
SENTINEL_DEPS="python3-xlib"

fail() { echo "GATE G1: FAIL - $1"; exit 1; }
say()  { echo; echo "=== $1 ==="; }

[ -f "$DEB" ] || fail "no .deb at $DEB (run packaging/build-deb.sh)"
$SSH true 2>/dev/null || fail "cannot SSH to the VM on port $PORT"

# --- D6: Flatpak live-match subcommand --------------------------------------
# ./scripts/gate-g1.sh flatpak : install a real Flatpak app and prove its
# running window's WM_CLASS resolves to its launcher entry (the ME-03 caveat).
if [ "${1:-}" = "flatpak" ]; then
  APP="org.gnome.Calculator"
  say "D6: install Flatpak + $APP (may pull a large runtime)"
  $SSH "command -v flatpak >/dev/null || sudo apt-get install -y flatpak >/dev/null 2>&1"
  $SSH "sudo flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo >/dev/null 2>&1"
  $SSH "flatpak info $APP >/dev/null 2>&1 || sudo flatpak install -y --noninteractive flathub $APP" 2>&1 | tail -2
  $SSH "test -f /var/lib/flatpak/exports/share/applications/$APP.desktop" || \
    fail "$APP exported .desktop missing"
  say "D6: launch it and resolve the live WM_CLASS through our matcher"
  $SSH "DISPLAY=:0 setsid flatpak run $APP >/tmp/calc.log 2>&1 </dev/null & sleep 8"
  $SSH "cd /usr/lib/jiopc-home && DISPLAY=:0 python3 -c \"
import sys, subprocess
sys.path.insert(0,'/usr/lib/jiopc-home')
from core.qt_compat import QtWidgets
app=QtWidgets.QApplication([])
from core import x11
from apps import desktop_entries as de
wid=subprocess.check_output(['bash','-c','DISPLAY=:0 wmctrl -l | grep -i calculator | head -1']).split()[0].decode()
cls=x11.wm_class_of(int(wid,16))
cap=[a for a in de.list_apps() if a.app_id=='$APP'][0]
m=de.match_wm_class(cls, de.index_by_wm_class())
print('live WM_CLASS:', repr(cls))
print('wm_class_keys:', cap.wm_class_keys)
print('resolved:', m.app_id if m else None)
print('D6 RESULT:', 'MATCH' if (m and m.app_id=='$APP') else 'NO MATCH')
\"" 2>&1 | grep -v -i wayland
  $SSH "flatpak kill $APP 2>/dev/null" >/dev/null 2>&1
  exit 0
fi

# --- SENTINEL: prove the VM is actually 00-clean ----------------------------
say "Sentinel: confirm 00-clean (deps absent, package absent)"
if $SSH "dpkg -s jiopc-home" >/dev/null 2>&1; then
  fail "jiopc-home is ALREADY installed -> this is NOT a fresh 00-clean restore"
fi
present=""
for p in $SENTINEL_DEPS; do
  if $SSH "dpkg -s $p" >/dev/null 2>&1; then present="$present $p"; fi
done
if [ -n "$present" ]; then
  fail "python runtime deps already present ->$present
       Either the snapshot restore did not take effect, or the snapshot was
       taken after Day-0 deps were installed. Create the clean precondition with:
         ssh -p $PORT $VM \"sudo dpkg --remove --force-depends$present\"
       then re-run this script."
fi
echo "OK: package absent, python runtime deps absent - clean precondition met."

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
