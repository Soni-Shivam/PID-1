# Installing JioPC Home

JioPC Home is a single-process Qt desktop shell for **Ubuntu 24.04 + LxQt**.
It installs from a `.deb`, runs entirely in user space, and auto-starts at LxQt
login. No root is needed at runtime (only at install time, as with any package).

## Prerequisites

- Ubuntu 24.04 LTS with the **LxQt** session
- X11 (no compositor required; the shell renders on CPU only)

## Install

### Option A — one command (recommended, resolves dependencies)

```bash
sudo apt install ./jiopc-home_0.1.0_all.deb
```

`apt` reads the package's `Depends:` and pulls in any missing dependencies from
the Ubuntu archive automatically.

### Option B — explicit two-step (dpkg)

```bash
# 1. install runtime dependencies (all from the Ubuntu archive)
sudo apt install -y python3-pyqt5 python3-xdg python3-xlib python3-requests papirus-icon-theme

# 2. install the package
sudo dpkg -i jiopc-home_0.1.0_all.deb
```

## What gets installed

| Path | Purpose |
|------|---------|
| `/usr/lib/jiopc-home/` | application code (single Qt process) |
| `/usr/bin/jiopc-home` | launcher (logs session-start time, then runs the shell) |
| `/etc/xdg/autostart/jiopc-home.desktop` | XDG autostart entry — LxQt launches it at login |

## Verify

Log out and back in to the LxQt session — the shell appears automatically with
no interaction. To run it manually instead:

```bash
jiopc-home
```

Startup timing is recorded at `/tmp/jiopc-startup.log` (a `SESSION_START` line
from the launcher and a `FIRST_PAINT` line from the app; the delta is the
login-to-visible figure).

## Uninstall

```bash
sudo dpkg -r jiopc-home      # remove the package
sudo dpkg --purge jiopc-home # also remove any config (when present)
```

## Build the .deb from source

No compilation is required (pure Python). On any machine with `dpkg-deb`:

```bash
./packaging/build-deb.sh           # -> dist/jiopc-home_0.1.0_all.deb
./packaging/build-deb.sh 0.2.0     # optional: stamp a different version
```
