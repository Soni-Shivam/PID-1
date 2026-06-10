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
- [ ] git repo initialized, first commit pushed to **public** GitHub repo

## Environment findings (important)
- Session is LXQt (`XDG_CURRENT_DESKTOP=LXQt`) but the WM is **xfwm4**, not Openbox (openbox not installed). All EWMH work (ME-02 dock type/struts) must be tested against xfwm4.
- xfwm4's built-in compositor (on by default) prevented xfwm4 from managing Qt frameless windows (empty WM_STATE, not in client list, never painted to screen). With compositing off the same window is managed and visible. Packaging/first-run must ensure compositing is off, or document it in INSTALL.md.
- `xwd -root` screenshots in this VirtualBox setup do NOT capture managed window content. Do not use screenshots as visibility proof; use `wmctrl -l`, `_NET_CLIENT_LIST_STACKING`, `xprop`, and human confirmation.
- Display manager is GDM (Xorg on vt2). Sockets :1024/:1025 are gnome-remote-desktop, ignore.
- PyQt5 RSS baseline 97 MB means ~100 MB headroom under the 200 MB budget for all features.

## Phases
- [ ] P — Packaging + autostart skeleton (Day 1) · MEs: ME-09, ME-10
- [ ] A — Dock (Days 2-3) · MEs: ME-02..06
- [ ] B — Application menu (Days 4-5)
- [ ] C — Widget engine + CMS (Days 6-7) · MEs: ME-07, ME-08
- [ ] D — Theme engine (Day 8) · ME-11
- [ ] E — First-run wizard (Day 9)
- [ ] I — Integration day (Day 10) · ME-12
- [ ] H — Benchmarks (Day 11)
- [ ] Docs (Day 12) · Video + usability (Day 13) · Submission gate (Day 14)

## ME log
| ME | Status | Date | Evidence |
|----|--------|------|----------|
| ME-01 | PASS | 2026-06-11 | First paint 35 ms; RSS 97.1 -> 97.3 MB stable at 10/30/60 s; window visible bottom-center (human-confirmed); managed by xfwm4, top of `_NET_CLIENT_LIST_STACKING` |

## Notes / TODO next session
- Next: Phase P (packaging skeleton + autostart, ME-09/ME-10). The .deb failing on a fresh VM is an automatic disqualifier — de-risk first.
- VM display currently 1280x800-810; test 1280x720 and 1920x1080 at Phase I.
- Decide whether to `apt install openbox` to match LxQt defaults, or build against xfwm4 (current choice: xfwm4, document in design.md).
