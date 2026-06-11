# PROGRESS — jiopc-home

> Living checklist. Update after every work session. Roadmap = JIOPC_CHALLENGE1_ROADMAP.md.

## Day 0 — Environment
- [x] VM snapshots `00-clean` and `01-dev` exist  *(human task — confirmed)*
- [x] VM reachable: `ssh -p 2222 vboxuser@127.0.0.1` (2026-06-11)
- [x] Qt version verified: LxQt on Qt5 -> **PyQt5 5.15.10** (python3-pyqt5 installed in VM); CLAUDE.md updated (2026-06-11)
- [x] Dev deps in VM: python3-xlib, python3-xdg, python3-requests, wmctrl, xprop, hyperfine, pidstat, rsync (2026-06-11)
- [x] No external compositor; xfwm4 built-in compositor found ON and disabled persistently via `xfconf-query -c xfwm4 -p /general/use_compositing -s false` (2026-06-11)
- [x] `deploy.sh` works end-to-end (~5 s edit-to-log cycle) (2026-06-11)
- [x] **ME-01 passed** — window visible (human-confirmed on VM console), RSS baseline: **97.3 MB stable over 60 s**, first paint ~35 ms (2026-06-11)
- [x] git repo initialized, first commit pushed to **public** GitHub repo (2026-06-11)

## Environment findings (important)
- Session is LXQt (`XDG_CURRENT_DESKTOP=LXQt`) but the WM is **xfwm4**, not Openbox (openbox not installed). All EWMH work (ME-02 dock type/struts) must be tested against xfwm4.
- xfwm4's built-in compositor (on by default) prevented xfwm4 from managing Qt frameless windows (empty WM_STATE, not in client list, never painted to screen). With compositing off the same window is managed and visible. Packaging/first-run must ensure compositing is off, or document it in INSTALL.md.
- `xwd -root` screenshots in this VirtualBox setup do NOT capture managed window content. Do not use screenshots as visibility proof; use `wmctrl -l`, `_NET_CLIENT_LIST_STACKING`, `xprop`, and human confirmation.
- Display manager is GDM (Xorg on vt2). Sockets :1024/:1025 are gnome-remote-desktop, ignore.
- PyQt5 RSS baseline 97 MB means ~100 MB headroom under the 200 MB budget for all features.

## Phases
- [x] P — Packaging + autostart skeleton (Day 1) · MEs: ME-09 PASS, ME-10 PASS
      build-deb.sh + .deb + /usr/bin launcher + XDG autostart + INSTALL.md done; app skeleton (qt_compat shim + placeholder dock) runs from /usr/lib; autostarts at LxQt login in 239 ms
- [~] A — Dock (Days 2-3) · MEs: ME-02/03/04/05/06 PASS
      dock/widget.py + dock/model.py done; boots as DOCK (geo 320x72, strut honored), 4 default pins from dock.json, running indicators wired to ClientListWatcher (no crash on open/close), launch/focus, pin/unpin/reorder via right-click + persistence, grid button -> menu_requested. Idle CPU 0%, RSS 117 MB. PENDING: human visual confirm; follow-ups: drag-reorder, animated hover-scale, theme tokens (Phase D)
- [~] B — Application menu (Days 4-5)
      menu/app_model.py (model+proxy: search Name+Comment, category filter, order-by), menu/recommend.py (recently/most/recommended w/ category-overlap scoring), menu/window.py (search + chips + order-by + Recently/Recommended strips + IconMode grid, work-area sized so dock stays visible, live updates via QFileSystemWatcher, Esc/lazy/reusable). Global hotkey Super+Space via core/x11.HotkeyListener + dock button. PENDING: human visual confirm of rendering/click
- [~] C — Widget engine + CMS (Days 6-7) · MEs: ME-07 PASS, ME-08 PASS
      widgets/engine.py (WidgetPlugin ABC + auto-discovery + execute_action + layout.json), 4 plugins (greeting_clock, news, quick_tiles, carousel), widgets/desktop.py (DESKTOP-layer grid + Widget Library add/remove), widgets/cms.py offline-first wired in. Boots clean: idle CPU 0.2%, RSS 137 MB; offline (dead endpoint) serves cache, no crash. PENDING: human visual confirm of widget rendering/interaction; follow-ups: drag-arrange, carousel slide animation, image download
- [~] D — Theme engine (pulled early to Day 2 per Roadmapv2) · ME-11 PASS
      core/theme.py (ThemeManager: token JSON -> string.Template QSS -> app.setStyleSheet + app.setFont, theme_changed signal, persist to settings.json); themes/dark.json + light.json + base.qss.tmpl; settings/dialog.py (theme + accent + font, all live-applying, Save-as-custom). Migrated ALL 7 _C dicts off hardcoded colour: dock/menu chrome via the app-wide sheet, plugins re-theme from ctx.theme.tokens on theme_changed, custom-painted bits (dock dot, carousel dots) read tokens. WidgetContext gains `theme`. Settings opens from the app-menu header. **D1 CLOSED** (hard grep gate green) and **D4 CLOSED** (main.py app.aboutToQuit stops watcher + hotkey). Boots dark, FIRST_PAINT 0.121 s, RSS 128 MB, idle CPU 0.00%, DESKTOP+DOCK types intact, theme=light persists across restart, .deb ships themes/. PENDING: human visual confirm of light/dark look at 1280x720 (D3/D9)
- [ ] E — First-run wizard (Day 9)
- [ ] I — Integration day (Day 10) · ME-12
- [ ] H — Benchmarks (Day 11)
- [ ] Docs (Day 12) · Video + usability (Day 13) · Submission gate (Day 14)

## ME log
| ME | Status | Date | Evidence |
|----|--------|------|----------|
| ME-01 | PASS | 2026-06-11 | First paint 35 ms; RSS 97.1 -> 97.3 MB stable at 10/30/60 s; window visible bottom-center (human-confirmed); managed by xfwm4, top of `_NET_CLIENT_LIST_STACKING` |
| ME-09 | PASS | 2026-06-11 | `build-deb.sh` -> `jiopc-home_0.1.0_all.deb`. On VM (all 4 deps already present): `dpkg -i` clean; runs from `/usr/lib/jiopc-home/main.py`; FIRST_PAINT 43 ms, RSS 103.0 MB; `dpkg -r` removes ALL files (postrm `rm -rf` clears untracked `__pycache__`); `desktop-file-validate` clean |
| ME-10 | PASS | 2026-06-11 | Autostart entry `/etc/xdg/autostart/jiopc-home.desktop` installed + validates; placeholder dock appears at LxQt login with NO interaction (human-confirmed). Login-to-visible delta (FIRST_PAINT - SESSION_START) = **239 ms** (budget 3 s); app-internal first paint 139 ms; RSS 103.7 MB |
| ME-02 | PASS | 2026-06-11 | Set _NET_WM_WINDOW_TYPE_DOCK before map + re-assert after; xprop confirms DOCK type, _NET_WM_STRUT_PARTIAL=0,0,0,64,..,340,939, sticky (0xFFFFFFFF), no decorations (_NET_FRAME_EXTENTS 0). xfwm4 honors strut: _NET_WORKAREA shrank to 1280x746 on 1280x810 screen; maximized window frame occupies y 0..746 exactly (xwininfo), stops at dock top |
| ME-05 | PASS | 2026-06-11 | ClientListWatcher (QThread, select()-blocking on root PropertyNotify, diffs _NET_CLIENT_LIST): `+ XClock 0x..` / `- 0x..` fire on open/close, WM_CLASS resolved; **idle CPU 0.00%** over 8 s pidstat |
| ME-06 | PASS | 2026-06-11 | activate_window via _NET_ACTIVE_WINDOW (source=2): focus switches between two qterminals on command; restores a minimized window (HIDDEN cleared + becomes active). NOTE: xclock can't be activated because it sets WM_HINTS input=False (not a code bug) - test with focus-accepting apps |
| ME-03 | PASS | 2026-06-11 | apps/desktop_entries.py: 183 visible apps enumerated (NoDisplay/Hidden excluded), icons resolve via QIcon.fromTheme, WM_CLASS index maps qterminal/pcmanfm-qt correctly. CAVEAT: 0 flatpaks installed in VM so live flatpak-match unproven (export dirs ARE scanned; rule flatpak-id==desktop-id in place) - install org.gnome.Calculator at Phase I to close |
| ME-04 | PASS | 2026-06-11 | apps/launcher.py: strip_field_codes drops %U etc.; `featherpad %U` + `qterminal` launched via QProcess.startDetached("/bin/sh",-c); no zombies after close; jiopc unaffected; usage.json written atomically to ~/.local/share/jiopc/home/ (core/store.py + core/paths.py) |
| ME-07 | PASS | 2026-06-11 | _NET_WM_WINDOW_TYPE_DESKTOP full-screen Qt window. _NET_CLIENT_LIST_STACKING bottom->top: pcmanfm-desktop, OUR layer, qterminal, panel. Our layer renders above pcmanfm desktop, normal windows cover it, lxqt-panel unaffected. Strategy (a) works - no pcmanfm-module-disable fallback needed |
| ME-08 | PASS | 2026-06-11 | widgets/cms.py offline-first. Online: fetch http feed -> 6 carousel -> atomic cache write. Offline (server down): fetch fails cleanly (caught), cache still served (6 items). Cold (no cache, no server): initial_content -> bundled default_feed.json, valid, no traceback. Endpoint configurable (http/file) |
| ME-11 | PASS | 2026-06-11 | experiments/me11_theme.py: string.Template QSS renders with no leftover tokens; `app.setStyleSheet` restyles built widgets live (no restart); custom-painted swatch repaints across themes (centre pixel 91,155,255 -> 23,99,214). Verified locally (offscreen) AND in VM with **compositing off**. Greenlit the migration: 7 `_C` dicts removed, hard grep gate (`#[0-9a-fA-F]{3,6}` in src/*.py outside themes/) returns nothing |

## Notes / TODO next session
- OnlyShowIn deliberately OMITTED from the autostart .desktop: session XDG_CURRENT_DESKTOP casing ("LXQt" vs "LxQt") is unreliable for spec's case-sensitive match, and SSH sessions report it empty. Package is LxQt-only anyway. Revisit if needed.
- VM 00-clean restore did NOT take effect last session (deps still present, jiopc-home still installed). Real fresh-VM .deb install test still owed before/at Day-14 gate.
- Phase A remaining: ME-03 (apps/desktop_entries.py enumerate system+local+Flatpak .desktop), ME-04 (apps/launcher.py Exec= parse + QProcess.startDetached + usage log), then build dock/ widget (pinned apps from dock.json, running indicators wired to ClientListWatcher, click-to-focus via activate_window, pin/unpin/reorder, hover, grid/menu button).
- WM_CLASS matching heuristic for dock running-indicators: StartupWMClass -> desktop-id == lower(WM_CLASS) -> Name == WM_CLASS -> generic. qterminal titles itself by shell prompt; match on WM_CLASS not title.
- VM display currently 1280x800-810; test 1280x720 and 1920x1080 at Phase I.
- Decide whether to `apt install openbox` to match LxQt defaults, or build against xfwm4 (current choice: xfwm4, document in design.md).
