#!/usr/bin/env bash
# build-deb.sh - stage src/ into a Debian tree and produce an installable .deb.
#
# Pure Python: no compilation step. Run on the host; install the result in the
# target VM (see INSTALL.md). Adding files to src/ needs no change here - the
# whole tree is copied as-is.
#
# Usage: ./packaging/build-deb.sh [version]
set -euo pipefail

VERSION="${1:-0.1.0}"
PKG="jiopc-home"
ARCH="all"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

STAGE="$ROOT/packaging/build/${PKG}_${VERSION}"
DIST="$ROOT/dist"
DEB="$DIST/${PKG}_${VERSION}_${ARCH}.deb"

rm -rf "$STAGE"
mkdir -p "$STAGE/DEBIAN" \
         "$STAGE/usr/lib/$PKG" \
         "$STAGE/usr/bin" \
         "$STAGE/etc/xdg/autostart"

# --- application code -------------------------------------------------------
rsync -a --delete \
  --exclude '__pycache__/' --exclude '*.pyc' \
  "$ROOT/src/" "$STAGE/usr/lib/$PKG/"

# --- launcher ---------------------------------------------------------------
cat > "$STAGE/usr/bin/$PKG" <<'EOF'
#!/bin/sh
# JioPC Home launcher. Logs session-start time (the login-to-visible
# benchmark reference) then execs the single-process Qt shell.
# User-space only; never runs sudo.
LOG="${JIOPC_STARTUP_LOG:-/tmp/jiopc-startup.log}"
echo "SESSION_START epoch=$(date +%s.%N)" >> "$LOG" 2>/dev/null || true
exec python3 /usr/lib/jiopc-home/main.py "$@"
EOF
chmod 755 "$STAGE/usr/bin/$PKG"

# --- XDG autostart entry ----------------------------------------------------
# OnlyShowIn is intentionally omitted: the package targets LxQt-only VMs, and
# the session's XDG_CURRENT_DESKTOP ("LXQt" vs "LxQt") is unreliable for the
# spec's case-sensitive matching. Revisit once verified in a live VM session.
cat > "$STAGE/etc/xdg/autostart/$PKG.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=JioPC Home
Comment=Engaging desktop shell for LxQt
Exec=/usr/bin/jiopc-home
Terminal=false
X-LXQt-Need-Tray=false
EOF

# --- control ----------------------------------------------------------------
INSTALLED_KB="$(du -sk "$STAGE/usr" | cut -f1)"
cat > "$STAGE/DEBIAN/control" <<EOF
Package: $PKG
Version: $VERSION
Section: x11
Priority: optional
Architecture: $ARCH
Depends: python3 (>= 3.11), python3-pyqt5, python3-xdg, python3-xlib, python3-requests
Installed-Size: $INSTALLED_KB
Maintainer: Shivam Soni <sonishivam.iitb@gmail.com>
Description: JioPC Home - engaging desktop shell for LxQt
 Single-process Qt desktop shell for LxQt providing a dock, application
 menu, CMS-driven desktop widgets, a token theme engine, and a once-only
 first-run wizard. Renders on CPU only (no compositor, no GPU).
EOF

# --- postinst: byte-compile for a faster cold start -------------------------
cat > "$STAGE/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
python3 -m compileall -q /usr/lib/jiopc-home >/dev/null 2>&1 || true
exit 0
EOF
chmod 755 "$STAGE/DEBIAN/postinst"

# --- postrm: drop the app dir wholesale, incl. untracked byte-compiled cache --
# The package owns everything under /usr/lib/jiopc-home, but postinst's
# __pycache__ is untracked and would otherwise block dpkg's dir cleanup.
cat > "$STAGE/DEBIAN/postrm" <<'EOF'
#!/bin/sh
set -e
rm -rf /usr/lib/jiopc-home 2>/dev/null || true
exit 0
EOF
chmod 755 "$STAGE/DEBIAN/postrm"

# --- build ------------------------------------------------------------------
mkdir -p "$DIST"
dpkg-deb --build --root-owner-group "$STAGE" "$DEB"
echo "Built: $DEB"
dpkg-deb --info "$DEB"
echo "--- contents ---"
dpkg-deb --contents "$DEB"
