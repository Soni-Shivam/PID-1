# Project: jiopc-home — desktop shell for LxQt (JioPC hackathon Challenge-01)
Read JIOPC_CHALLENGE1_ROADMAP.md Section 1 (constraints) before any task.

## Hard rules
- Target: Ubuntu 24.04 + LxQt in a VM, X11, NO compositor, NO GPU. 4 vCPU / 8 GB.
- ONE QApplication process. No Electron, no web views, no extra daemons.
- Qt binding: PyQt5 Import only via src/core/qt_compat.py.
- Idle budgets: CPU < 10% (30 s avg), RSS < 200 MB. No polling loops —
  X11 events via python3-xlib; QTimer only for the clock (1 s) and CMS refresh.
- ALL persistent state under ~/.config/jiopc/home, ~/.local/share/jiopc/home,
  ~/.cache/jiopc/home. Atomic JSON writes via core/store.py. Never write elsewhere.
- No sudo at runtime. No hardcoded usernames/paths/URLs — read config.
- Every visual must survive: compositing off, 1280x720, light AND dark theme.

## Verification
- App runs in the VM: ./scripts/deploy.sh ; logs at /tmp/jiopc.log
- You may ssh -p '2222' 'vboxuser@127.0.0.1' to run checks (xprop, ps, cat logs).
- After implementing anything, state the exact command(s) to verify it.

## Style
- Python 3.11, type hints, small modules (<300 lines), docstring per module
  explaining its role. No global state except the QApplication.
- Widget plugins live in src/widgets/plugins/, one file each, implementing
  WidgetPlugin (see src/widgets/engine.py). Adding a widget = adding a file.
- Lets do this professionally and not use emojis