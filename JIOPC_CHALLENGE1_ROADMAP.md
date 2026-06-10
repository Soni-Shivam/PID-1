# JioPC Challenge-01 — Execution Roadmap
### "JioPC Home: Engaging Desktop Experience" · Solo builder + Claude Code · ~14 days
**This is the single reference document for the human AND for Claude Code. Both should re-read Section 1 before every work session.**

---

## 0. How to use this document

- **You (human):** work in *phases* (Section 6). Each phase starts with micro-experiments (ME-xx, Section 7) that de-risk the hard part *before* you build the real feature. Never build a feature whose ME hasn't passed.
- **Claude Code:** this doc is your spec. The constraint cheat-sheet (Section 1) overrides any default you'd normally choose. When asked to implement a phase, read that phase's WHAT/WHY/HOW/TEST block and the linked MEs first. Always finish a task by stating how to verify it inside the VM.
- **Cadence:** every work session = (1) pick the next unchecked item, (2) run/extend its ME, (3) implement, (4) run the TEST block, (5) commit with a message referencing the phase (e.g. `B2: dock struts working`), (6) update `PROGRESS.md`.
- **Golden rule:** anything that touches packaging, autostart, performance, or X11 gets verified **inside the Ubuntu 24.04 + LxQt VM**, never only on the Ubuntu 22.04 host. The VM *is* the target.

---

## 1. Mission & Non-Negotiables (the cheat sheet)

**Build:** a desktop shell for LxQt with 5 components — (A) macOS-style dock, (B) application menu/launcher, (C) extensible desktop widget engine fed by a CMS, (D) token-based theme engine, (E) once-only first-run wizard.

**Hard constraints — every line of code must respect these:**

| # | Constraint | Practical meaning |
|---|-----------|-------------------|
| 1 | No GPU, no compositor | No real transparency, no blur/shadow effects. Solid backgrounds + rounded corners via window masks. Test with compositing OFF (LxQt default). |
| 2 | Idle CPU < 10% (30s avg) | Event-driven X11 (no polling loops), coalesced timers, animations only on user interaction and ≤ 200 ms. |
| 3 | Idle RAM < 200 MB (VmRSS after 5 min) | ONE process for everything. Cap icon cache. Measure constantly. |
| 4 | Login → shell visible < 3 s | Lazy-load the menu and widget data; paint the dock + cached widgets first. |
| 5 | No root at runtime | Pure user-space process. Root only at `dpkg -i` time. |
| 6 | All state in `$HOME` | Config: `~/.config/jiopc/home/` · Usage data: `~/.local/share/jiopc/home/` · CMS cache: `~/.cache/jiopc/home/`. **Zero** state anywhere else. |
| 7 | Ships as a .deb | Must install on a FRESH Ubuntu 24.04 + LxQt VM. INSTALL.md may list dependency installs first. |
| 8 | LxQt stays functional | Don't kill lxqt-panel or break the session. Our shell is additive (with optional desktop takeover, see Phase D). |
| 9 | Works at 1280×720 over RDP | Responsive layouts; test both 1920×1080 and 1280×720. |
| 10 | Offline = cached content, no crash | Always render from cache; network only refreshes the cache. |

**Scoring map (where the points are):** Functionality 30 · Performance 25 · Code Quality 20 · Docs 15 · Innovation 10. Translation: a *complete, benchmarked, well-documented* solid build beats a flashy incomplete one. Bonus goals come LAST.

**Automatic disqualifiers (memorize):** needs root at runtime · needs GPU · .deb fails on fresh VM · private repo / missing INSTALL.md · benchmark methodology absent or not reproducible.

---

## 2. Stack Decision (and why)

**Decision: Python 3.12 + PyQt (Qt Widgets), single process `jiopc-home`, plus `python3-xlib` for EWMH, `requests` for CMS, plain JSON for persistence.**

Why Python over C++ for a solo, 2-week, Claude-Code-assisted build:
- 3–4× faster iteration; Claude Code produces correct PyQt at very high reliability.
- All dependencies exist as Ubuntu archive packages → trivially installable, no compile step, .deb stays a thin wrapper.
- RAM cost (~+30–50 MB vs C++) still fits the 200 MB budget for a single process — but we verify this on Day 0 with ME-01 before committing.

**⚠️ DAY-0 VERIFICATION (do not skip):** In the fresh VM, check which Qt major version LxQt ships on Ubuntu 24.04 (`apt list --installed | grep -i qt` and `lxqt-session --version`). Then pick:
- If LxQt is **Qt5** → use **PyQt5** (`python3-pyqt5`) — Qt5 libs are already on disk, smallest dependency footprint.
- If **Qt6** (or both available) → **PyQt6** (`python3-pyqt6`) is fine and matches the doc's Qt 6 recommendation.
- Whichever you pick, write it into `CLAUDE.md` and never mix. The code should import through a tiny `qt_compat.py` shim so a later switch is a one-file change.

**Justification paragraph for design.md (draft now, refine later):** "Qt Widgets chosen because LxQt is itself Qt-based, Qt renders fully on CPU without compositing, and a single-process Qt app keeps idle RSS far below the Electron-class alternatives. Python chosen for development velocity; profiling (see benchmarks/) confirms the interpreter overhead keeps us within the 200 MB / 10% CPU budget."

**Architecture (one process, five modules):**

```
jiopc-home (single QApplication process)
├── core/
│   ├── qt_compat.py        # PyQt5/6 import shim
│   ├── paths.py            # XDG paths under ~/.config|.local|.cache /jiopc/home
│   ├── store.py            # atomic JSON read/write (write-to-temp + rename)
│   ├── theme.py            # token JSON -> QSS template -> app.setStyleSheet()
│   └── x11.py              # EWMH: dock type, struts, client list, activate window
├── apps/
│   ├── desktop_entries.py  # scan+parse .desktop (system, local, flatpak exports)
│   ├── launcher.py         # Exec= parsing, QProcess.startDetached
│   └── usage.py            # usage log -> recent / most-used / recommended
├── dock/                   # Component A
├── menu/                   # Component B
├── widgets/                # Component C: engine + plugins/ (one file per widget)
│   └── cms.py              # fetch -> cache -> serve-from-cache
├── wizard/                 # Component E
├── settings/               # theme editor + widget arrange UI
└── main.py                 # boot order: theme -> dock -> desktop layer -> lazy rest
```

**Why one process (write this in design.md too):** one Qt runtime in RAM instead of five; `setStyleSheet()` re-themes everything atomically; one autostart entry = one startup cost; no IPC needed.

---

## 3. Day 0 — Environment & the Fast Iteration Loop

You're on an Ubuntu 22.04 host. The target is a VM. **Goal of Day 0: a VM you can rebuild/reset in 60 seconds, and a one-command deploy-and-run loop.**

### 3.1 Create the VM (VirtualBox, ~1.5 h mostly waiting)
1. `sudo apt install virtualbox` on the host (challenge explicitly allows VirtualBox; on a Linux host KVM/virt-manager is faster but VirtualBox keeps you 1:1 with the judging description — use VirtualBox).
2. Download Ubuntu 24.04 LTS desktop ISO.
3. New VM: **4 vCPU, 8 GB RAM, 50 GB disk** (match the JioPC profile exactly — your benchmarks are only valid at this spec). Enable nested paging; **disable 3D acceleration** (we must not accidentally rely on GPU).
4. Install Ubuntu (minimal install). Then inside the VM:
   ```bash
   sudo apt update && sudo apt install -y lxqt openssh-server
   ```
5. Log out → at the login screen pick the **LxQt session** → log in. Confirm LxQt panel appears.
6. Disable the compositor if one is running (LxQt default uses Openbox without compositing — verify with `ps aux | grep -E 'picom|compton|xcompmgr'`; nothing should be running).
7. **Take snapshot `00-clean`** — fresh OS + LxQt + ssh, nothing else. This snapshot is sacred: it's what the judges' "fresh VM" looks like. Every packaging test starts by restoring it.
8. Install dev deps in the VM, then snapshot again as `01-dev`:
   ```bash
   sudo apt install -y git python3-pip python3-xdg python3-xlib python3-requests wmctrl x11-utils hyperfine sysstat
   # plus python3-pyqt5 OR python3-pyqt6 per the Day-0 verification above
   ```
   You'll do daily work on `01-dev` and packaging/acceptance tests on a restore of `00-clean`.

### 3.2 The iteration loop (this is what makes 2 weeks possible)
Two viable modes — pick one, set it up, never think about it again:

**Mode 1 (recommended): Claude Code runs ON THE HOST, code deploys to the VM.**
- Repo lives on the host. Claude Code edits there (full speed, your normal terminal).
- VirtualBox: set the VM network to NAT with a port-forward `2222 → 22`, or Bridged.
- One deploy script, `scripts/deploy.sh`:
  ```bash
  #!/usr/bin/env bash
  set -e
  rsync -az --delete -e "ssh -p 2222" ./src/ user@localhost:~/jiopc-home/src/
  ssh -p 2222 user@localhost 'pkill -f jiopc-home || true; \
    DISPLAY=:0 nohup python3 ~/jiopc-home/src/main.py >/tmp/jiopc.log 2>&1 &'
  ```
- Loop = **edit → `./scripts/deploy.sh` → look at the VM window → read `/tmp/jiopc.log`**. Sub-10-second cycle.
- Give Claude Code permission to run `deploy.sh` and `ssh -p 2222 ... 'command'` so it can self-verify (e.g., grep the log, run `xprop`, measure RSS) without you copy-pasting.

**Mode 2: Claude Code runs INSIDE the VM.** Simpler mentally (no sync), fine on 8 GB RAM since Claude Code is light, but your editor/terminal comfort lives inside a VM window. Choose this if SSH/rsync setup frustrates you.

### 3.3 Repo + CLAUDE.md (create now, on the host)
```
jiopc-home/
├── CLAUDE.md            # see below — Claude Code reads this automatically
├── PROGRESS.md          # living checklist (phases + MEs, checked off)
├── README.md  design.md  INSTALL.md        # grow these as you go, not at the end
├── src/                 # all application code (structure from Section 2)
├── experiments/         # me01_blank_window.py, me02_struts.py, ... (KEEP these — they're proof of methodology)
├── packaging/           # debian control files + build-deb.sh
├── benchmarks/          # measure_*.sh + results/ + METHODOLOGY.md
├── cms-mock/            # feed.json + serve.py (one-liner http server)
├── screenshots/  video/
└── scripts/             # deploy.sh, reset-state.sh, simulate-vm-reassignment.sh
```

**`CLAUDE.md` — paste this verbatim, then keep it updated:**
```markdown
# Project: jiopc-home — desktop shell for LxQt (JioPC hackathon Challenge-01)
Read JIOPC_CHALLENGE1_ROADMAP.md Section 1 (constraints) before any task.

## Hard rules
- Target: Ubuntu 24.04 + LxQt in a VM, X11, NO compositor, NO GPU. 4 vCPU / 8 GB.
- ONE QApplication process. No Electron, no web views, no extra daemons.
- Qt binding: <PyQt5|PyQt6 — fill in after Day-0 check>. Import only via src/core/qt_compat.py.
- Idle budgets: CPU < 10% (30 s avg), RSS < 200 MB. No polling loops —
  X11 events via python3-xlib; QTimer only for the clock (1 s) and CMS refresh.
- ALL persistent state under ~/.config/jiopc/home, ~/.local/share/jiopc/home,
  ~/.cache/jiopc/home. Atomic JSON writes via core/store.py. Never write elsewhere.
- No sudo at runtime. No hardcoded usernames/paths/URLs — read config.
- Every visual must survive: compositing off, 1280x720, light AND dark theme.

## Verification
- App runs in the VM: ./scripts/deploy.sh ; logs at /tmp/jiopc.log
- You may ssh -p 2222 user@localhost to run checks (xprop, ps, cat logs).
- After implementing anything, state the exact command(s) to verify it.

## Style
- Python 3.12, type hints, small modules (<300 lines), docstring per module
  explaining its role. No global state except the QApplication.
- Widget plugins live in src/widgets/plugins/, one file each, implementing
  WidgetPlugin (see src/widgets/engine.py). Adding a widget = adding a file.
```

### 3.4 Day-0 exit criteria
- [ ] VM snapshots `00-clean` and `01-dev` exist
- [ ] `deploy.sh` works: edit a print statement on host → see it in `/tmp/jiopc.log` in <15 s
- [ ] Qt version verified, CLAUDE.md filled in
- [ ] **ME-01 passed** (blank Qt window in LxQt, RSS measured — see Section 7)
- [ ] git repo initialized, first commit pushed to a **public** GitHub repo (private repo = disqualification; create it public from day one so you never forget)

---

## 4. The Micro-Experiment System

A micro-experiment (ME) is a **throwaway script ≤ ~80 lines that proves ONE risky mechanism works in the VM** before you build the real feature on top of it. This is how you avoid discovering a fatal X11/packaging problem on day 12.

Rules:
1. Each ME lives in `experiments/meXX_name.py` (or `.sh`) and is committed even after it's "done" — judges reading your repo will see a disciplined methodology (Code Quality + Innovation points).
2. Each ME has a one-line PASS criterion written at the top of the file. It either passes in the VM or it doesn't — no "seems fine".
3. Time-box: if an ME fights you for > 2 hours, stop and use its listed **fallback** (Section 7).
4. Claude Code workflow per ME: *"Implement experiments/meXX per the roadmap Section 7. Then tell me the exact command to run it in the VM and what output proves PASS."* Run it, paste the output back, move on.
5. Log results in `PROGRESS.md` (`ME-02 ✅ 2026-06-12 — struts respected by Openbox, maximized window stops at dock edge`).

---

## 5. Phase Plan Overview (14 days)

| Day | Phase | Output |
|----|-------|--------|
| 0 | Environment | VM + snapshots + deploy loop + ME-01 |
| 1 | **P: Packaging skeleton FIRST** | installable .deb + autostart, proven on `00-clean` |
| 2–3 | **A: Dock** | pin/unpin/reorder, launch, running indicators, tooltips, menu button |
| 4–5 | **B: Application menu** | search, categories, order-by, recent, recommended |
| 6–7 | **C: Widget engine + CMS** | engine + 4 widgets + mock CMS + offline path |
| 8 | **D: Theme engine** | tokens → QSS, light+dark, settings UI, persistence |
| 9 | **E: First-run wizard** | greeting, tour, initial choices, once-only flag |
| 10 | **I: Integration day** | persistence/VM-reassignment test, 720p pass, RDP check |
| 11 | **H: Benchmarks + perf tuning** | p50/p95 numbers meeting all 3 budgets |
| 12 | **Docs** | README, design.md (+diagrams), INSTALL.md, schema doc, screenshots |
| 13 | **Demo video + usability test** | ≤3-min VM recording, 5-person test results |
| 14 | **Submission gate** | full EVALUATE checklist on a `00-clean` restore, submit |

Why packaging is Day 1 and not Day 12: the .deb failing on a fresh VM is an **automatic disqualification**, and autostart timing feeds the <3 s budget. De-risk the disqualifiers first; features second. From Day 1 onward, every feature you add ships through the same .deb pipeline, so the scary "final packaging" step never exists.

If you fall behind (you will, somewhere): the protected core is **P + A + B + minimal C + minimal D + E + benchmarks + docs**. Cut in this order: bonus goals → extra widgets → theme editor polish (keep light/dark switch) → dock animations.

---

## 6. Phase-by-Phase Detail

Format: **WHAT** (deliverable) · **WHY** (which checklist items it buys) · **HOW** (steps + the mechanism explained) · **TEST** (objective pass) · **MEs** (prereqs from Section 7) · **CC** (a starting prompt for Claude Code).

---

### PHASE P — Packaging + Autostart Skeleton (Day 1)
**WHAT:** A "hello shell" version of jiopc-home (it only shows a 1-button dock placeholder), packaged as a .deb that installs on a `00-clean` restore and auto-starts into the LxQt session.
**WHY:** Buys checklist items ".deb installs cleanly" and the foundation of "shell visible < 3 s". Kills the #1 disqualification risk in day one.
**HOW (mechanism):**
- A Debian binary package is just a directory tree + a `DEBIAN/control` file, built with `dpkg-deb --build`. No compilation needed for Python.
- Install layout: app code → `/usr/lib/jiopc-home/`, launcher script → `/usr/bin/jiopc-home`, autostart entry → `/etc/xdg/autostart/jiopc-home.desktop` (this is the XDG autostart spec — LxQt's session manager launches every .desktop in that dir at login; LxQt's own modules start exactly this way).
- The autostart entry:
  ```ini
  [Desktop Entry]
  Type=Application
  Name=JioPC Home
  Exec=/usr/bin/jiopc-home
  OnlyShowIn=LXQt;
  X-LXQt-Need-Tray=false
  ```
- `DEBIAN/control` `Depends:` lists only Ubuntu-archive packages (your Qt binding, python3-xdg, python3-xlib, python3-requests). INSTALL.md then has two commands: `sudo apt install -y <deps>` then `sudo dpkg -i jiopc-home.deb`. (The checklist allows deps "your INSTALL.md specifies". Also mention `sudo apt install ./jiopc-home.deb` as the one-command alternative that resolves deps automatically.)
- `packaging/build-deb.sh` copies `src/` into the staging tree, stamps a version, runs `dpkg-deb --build`. CI-grade reproducibility = free Documentation points.
**TEST:** Restore snapshot `00-clean` → follow INSTALL.md literally, copy-pasting → reboot → log into LxQt → placeholder appears without touching anything. Time how long after login it appears (baseline for the 3 s budget).
**MEs:** ME-09, ME-10.
**CC:** *"Create packaging/build-deb.sh and the DEBIAN tree per roadmap Phase P. App entry point src/main.py currently shows a frameless 200×48 QWidget bottom-center. Include the XDG autostart entry. Output: the dpkg-deb command sequence and the INSTALL.md install section."*

---

### PHASE A — The Dock (Days 2–3)
**WHAT:** Bottom-anchored dock: pinned apps (persisted), single-click launch, running-app indicators (dot under icon), click-to-focus running windows, pin/unpin/reorder via right-click menu + drag, hover tooltips, subtle hover scale, and a "grid" button that will open the app menu.
**WHY:** Biggest visible component; covers 2 checklist rows; the EWMH plumbing built here (core/x11.py) is reused by the menu and widgets.
**HOW (mechanism — read this, it's the heart of the project):**
1. **Being a dock.** Set the window type to `_NET_WM_WINDOW_TYPE_DOCK` so Openbox keeps it undecorated, above normal windows, on all desktops. In Qt: frameless tool window flags, then (because Qt sometimes rewrites X properties) re-assert the type via python-xlib *after* the window is shown. Verify with `xprop` — never trust, always inspect.
2. **Reserving space.** Set `_NET_WM_STRUT_PARTIAL` (12 CARDINAL values; for a bottom dock: bottom = dock height, bottom_start_x/bottom_end_x = dock's x-range) so maximized windows stop at the dock's edge instead of covering it.
3. **Knowing what's running.** Subscribe to `PropertyNotify` on the X root window. When `_NET_CLIENT_LIST` changes, diff it: new window IDs → read their `WM_CLASS` → match to a .desktop entry; vanished IDs → clear indicator. Matching heuristic (in order): `StartupWMClass=` field equals WM_CLASS → desktop-file ID (filename minus .desktop) equals lowercased WM_CLASS → `Name=` lowercased equals WM_CLASS → unmatched (show a generic running icon). Run the X event listener in a QThread emitting Qt signals — **never poll**.
4. **Focusing.** Send a `_NET_ACTIVE_WINDOW` client message for the target window ID (what `wmctrl -ia` does; do it natively via xlib, keep wmctrl as a debugging tool).
5. **Launching.** Parse `Exec=` (strip `%f %F %u %U` field codes per the desktop-entry spec), `QProcess.startDetached("/bin/sh", ["-c", cmd])`. Log the launch to usage.py (the menu needs this data later).
6. **Pinned state.** `~/.config/jiopc/home/dock.json`: ordered list of desktop-file IDs. Atomic writes. Default pin set (browser, file manager, terminal, settings) defined in code for first run.
7. **Hover effect within CPU budget.** Pre-render each icon at 2 sizes (e.g. 40 px and 52 px) at load; on hover run one ~120 ms QPropertyAnimation between them. No continuous animation, no per-frame scaling of fresh pixmaps. While idle the dock paints nothing → 0% CPU.
**TEST:** Pin 3 apps → reorder → restart app → order preserved. Launch Firefox from dock → dot appears. Open a second Firefox window, minimize, click dock icon → window focuses/raises. Maximize any app → it does NOT cover the dock. `pidstat -p $(pgrep -f jiopc-home) 1 30` while idle → < 2–3%.
**MEs:** ME-02, ME-03, ME-04, ME-05, ME-06.
**CC:** *"Implement src/core/x11.py per roadmap Phase A steps 1–4: set_dock_type(win_id), set_bottom_strut(win_id, h, x0, x1), a ClientListWatcher(QThread) emitting window_added/window_removed(wm_class, win_id), and activate_window(win_id). python3-xlib only. Then src/dock/ using it. Pass criteria are in the TEST block."*

---

### PHASE B — Application Menu (Days 4–5)
**WHAT:** Full-screen-ish launcher over the desktop (opened from the dock button or a hotkey): live search, category chips from `Categories=`, order-by (name / most used / recently used), a Recently Used row, a Recommended row, each app = icon + name + one-line `Comment=`, click to launch.
**WHY:** Covers a 5-part checklist row by itself; also where "4 of 5 strangers find an app in 60 s" is won — so design for *obviousness*: huge search bar, autofocus on open, Esc closes.
**HOW (mechanism):**
1. **Enumeration.** Scan `/usr/share/applications/`, `~/.local/share/applications/`, AND the Flatpak export dirs `/var/lib/flatpak/exports/share/applications/` + `~/.local/share/flatpak/exports/share/applications/` (JioPC user apps are Flatpaks — supporting these shows you actually read the platform doc). Parse with PyXDG. Skip `NoDisplay=true` / `Hidden=true`. Icons: `QIcon.fromTheme(icon_name)` with a generic fallback. Deduplicate by desktop-file ID with the precedence user > system.
2. **Live updates.** `QFileSystemWatcher` on those dirs → rescan (debounced 1 s) → "user installs from Software Center, app appears instantly" — show this in the demo video.
3. **Model/view.** One `QAbstractListModel` of all apps + `QSortFilterProxyModel` for search (case-insensitive match over Name+Comment) and category filter; sort role switches for the order-by control. `QListView` in IconMode + `setUniformItemSizes(True)` keeps painting cheap.
4. **Usage intelligence.** `usage.json`: `{app_id: {count, last_ts, category_counts_at_launch}}` updated on every launch (dock and menu share launcher.py so both record). Recently Used = top-N by last_ts. **Recommended** = apps with count==0, scored by cosine-ish overlap between the app's `Categories=` and the user's aggregate category usage vector; tie-break randomly each session so the row feels alive. Document this formula in design.md — it's a cheap, legitimate Innovation point.
5. **Open/close.** Menu is a borderless window sized to the work area; build it lazily on first open (protects the 3 s startup), keep it alive after (instant re-open).
**TEST:** Type "fire" → Firefox filters in < 50 ms perceived. Click Education chip → only Education apps. Launch 3 apps → they head Recently Used; restart app → still there. Recommended shows only never-launched apps. Install/remove a .desktop file in `~/.local/share/applications` → list updates without restart.
**MEs:** ME-03 (already done), plus a 15-minute ME-13 if Flatpak matching misbehaves.
**CC:** *"Implement src/apps/desktop_entries.py and src/menu/ per roadmap Phase B. Model/proxy architecture as specified; recommended-apps scoring per step 4 with a docstring explaining the formula. Verify commands at the end."*

---

### PHASE C — Widget Engine + CMS (Days 6–7)
**WHAT:** A desktop layer rendering widgets; plugin architecture; minimum widgets: hero **carousel**, **news/headlines**, **quick-launch tiles**, **greeting + clock**; an "Arrange/Add widgets" mode; CMS fetch → cache → render, offline-safe; documented JSON schema; mock CMS server.
**WHY:** 3 checklist rows (engine, CMS content, offline). The carousel + greeting is also your demo's money shot.
**HOW (mechanism):**
1. **The desktop layer.** One full-work-area frameless window of type `_NET_WM_WINDOW_TYPE_DESKTOP` (Openbox keeps it under everything). It paints the wallpaper + a layout grid of widget frames. LxQt's own desktop is pcmanfm-qt running `--desktop`; two coexistence strategies — try (a) first: **(a)** our layer simply sits above pcmanfm-qt's (both are DESKTOP-type; stacking among desktop windows usually favors the later-mapped one — ME-07 verifies on Day 6 morning); **(b)** fallback: ship a session tweak that disables the pcmanfm-qt desktop module for the user (LxQt Session Settings → Modules writes user config — we can write the same key from our installer's first run, no root needed since it's user config). Constraint 8 check: lxqt-panel must remain visible/usable either way.
2. **Plugin architecture (the "engine" the judges will probe).** `widgets/engine.py` defines:
   ```python
   class WidgetPlugin(ABC):
       id: str; name: str; default_size: tuple[int,int]
       needs_cms: bool = False
       def create_view(self, ctx) -> QWidget: ...   # ctx: theme tokens, cms data, launcher
   ```
   Plugins auto-discovered from `widgets/plugins/*.py`. The engine owns layout (a simple grid with col/row spans), the add/remove/arrange UI, and persistence to `~/.config/jiopc/home/layout.json` (`[{plugin_id, col, row, w, h, props}]`). **Demo move:** write a 25-line `weather.py` or `quote.py` plugin live in the video to prove extensibility.
3. **CMS pipeline (offline-first — this exact design satisfies constraint 10 for free):**
   - Schema (`cms-mock/feed.json`, document in `design.md` + `cms-schema.md`): `{ "version": 1, "fetched_hint_minutes": 240, "carousel": [{id,title,subtitle,image_url,cta_label,cta_action}], "news": [{id,headline,source,ts,url}], "tiles": [{id,label,icon,action}] }` — actions are namespaced strings like `app:firefox.desktop` or `url:https://…` so content can drive launches. ≥5 entries per section (deliverable requirement).
   - `cms.py`: on session start, *first* load `~/.cache/jiopc/home/feed.json` and render immediately (startup never waits on network); *then* fetch the configured endpoint (URL in `~/.config/jiopc/home/settings.json`, default points at the mock) with a 5 s timeout in a background thread; on 200, atomically replace cache and emit `content_updated`; on any failure, log and do nothing — cache keeps rendering. A `QTimer` re-fetches at a configurable interval (default: once per session = timer off).
   - Images: download referenced images into the cache dir alongside the feed; render placeholders until present; never block paint on a download.
   - Mock server: `cms-mock/serve.py` = `python3 -m http.server` wrapper; also commit the file so `file://` works as a zero-setup endpoint.
4. **Carousel without GPU:** QStackedWidget + a 250 ms opacity-less slide (animate the widget position, not transparency — no compositor!), auto-advance every 8 s **only while the desktop is visible** (pause when any window covers the layer — check via the existing ClientListWatcher; this is a nice CPU-budget detail to mention in design.md).
**TEST:** Cold start with network ON → live content. `sudo ip link set <iface> down` equivalent in VM (or point endpoint at a dead URL) → restart app → cached content renders, no crash, log shows graceful failure. Add/remove/move widgets → restart → layout identical. New plugin file dropped in → appears in Add-widget list without code changes elsewhere.
**MEs:** ME-07, ME-08.
**CC:** *"Implement src/widgets/ per roadmap Phase C: engine with WidgetPlugin ABC + auto-discovery, the four plugins, cms.py with the offline-first pipeline (cache-then-fetch, atomic replace), layout persistence. Also cms-mock/feed.json with 6 entries per section and serve.py."*

---

### PHASE D — Theme Engine (Day 8)
**WHAT:** Token-based theming: a theme = JSON of design tokens; engine renders tokens → QSS template → `app.setStyleSheet()`; light + dark ship as two token files; a settings dialog edits colors (QColorDialog) and fonts (QFontComboBox + size) into a custom theme; active theme + customs persist in `$HOME`; everything re-themes live.
**WHY:** Checklist row + the doc's explicit "engine, not presets" trap — tokens+template is precisely the architecture that passes that bar. Also enables the import/export bonus in ~20 minutes (it's file copy).
**HOW:**
1. `themes/light.json`, `themes/dark.json` shipped read-only in the package; user themes in `~/.config/jiopc/home/themes/`. Tokens: `bg, surface, surface_alt, text, text_muted, accent, accent_text, danger, font_family, font_size_base, radius, dock_icon_size, spacing_unit`.
2. `core/theme.py`: loads tokens, substitutes into one `style.qss.tmpl` (use `$token` + `string.Template` — `{}` collides with QSS braces), calls `setStyleSheet` on the QApplication, and emits `theme_changed(tokens)` for the few things QSS can't reach (custom-painted dock indicators, carousel arrows) — those repaint from the token dict.
3. Settings dialog writes a `custom-*.json`, switches to it, persists `{"active_theme": "..."}` in settings.json.
4. **Discipline rule for all phases (add to CLAUDE.md):** zero hardcoded colors/fonts anywhere in widget code; everything via QSS classes (`setProperty("class", "tile")` + `*[class="tile"]{...}`) or the token dict. Retro-fitting theming on Day 8 is cheap only if Days 2–7 obeyed this.
**TEST:** Switch light↔dark → dock + open menu + widgets all change with no restart. Change accent + font in editor → applied live → restart → still applied. Grep the codebase for `#` hex colors outside themes/ → zero hits.
**MEs:** ME-11 (30 min, do it morning of Day 8).
**CC:** *"Implement src/core/theme.py + src/settings/theme_editor.py per Phase D. Then sweep src/ for hardcoded colors/fonts and migrate them to tokens/QSS; show me the diff summary."*

---

### PHASE E — First-Run Wizard (Day 9)
**WHAT:** On first login only: full-screen-ish QWizard-style flow — (1) personalized greeting (user's real name from the passwd GECOS field via `pwd.getpwuid`, fallback to username + time-of-day "Good morning, Rakesh"), (2) guided tour of dock / menu / widgets / themes (highlight overlays with arrows pointing at the real components), (3) interactive choices: pick light/dark + pick 3–5 apps to pin (writes the same dock.json/settings.json the components read), (4) finish → flag file.
**WHY:** Checklist row "runs once and does not re-trigger". Also sets up the perfect demo-video opening scene.
**HOW:** main.py boot: if `~/.config/jiopc/home/onboarding_done` missing → show wizard *after* the dock+desktop have painted (shell-visible-in-3s is measured on the shell, and the tour needs real components to point at). **Write the flag when the wizard opens, not on completion** — a mid-wizard crash must not re-trigger it (the checklist tests re-trigger, not completion). Offer "Skip tour" on every page.
**TEST:** `rm ~/.config/jiopc/home/onboarding_done` → restart → wizard runs, choices take effect immediately after finish. Restart again → no wizard. Kill the app mid-wizard → restart → no wizard.
**CC:** *"Implement src/wizard/ per Phase E. Tour pages must reference live component geometry for highlight overlays (no GPU/transparency tricks — use solid cutout frames). Flag written at wizard open."*

---

### PHASE I — Integration Day (Day 10)
The day everything is proven to work *as the judges will test it*.
1. **Simulated VM reassignment** (`scripts/simulate-vm-reassignment.sh`): the floating-VM model = same `$HOME`, fresh VM-local state. Simulation: stop app → wipe `/tmp` artifacts → (stronger: restore `00-clean`, reinstall the .deb, copy the saved `~/.config|.local|.cache/jiopc` back in) → start → pinned apps, layout, theme, usage, wizard-done flag ALL intact. Record this as a clip for the video — it's the platform's core promise.
2. **1280×720 pass.** Switch VM display to 1280×720; walk every screen; fix overflow (the doc explicitly warns about layouts that only work at 1080p). Make the widget grid column count responsive to work-area width.
3. **Real RDP check.** `sudo apt install xrdp` in the VM, connect from the host with Remmina/`xfreerdp` at both resolutions. RDP is the actual JioPC transport; it also exposes "animations feel heavy" issues (every animated frame = network traffic) — if the carousel slide stutters over RDP, shorten/disable distance animations.
4. **LxQt-intact check:** lxqt-panel reachable, logout/login works, default launcher opens.

---

### PHASE H — Benchmarks (Day 11)
**WHAT:** `benchmarks/METHODOLOGY.md` + scripts + `results/` with p50/p95 for: session-login→shell-visible, idle CPU (30 s), idle RSS (after 5 min). Reproducible = a third party can rerun with one command. (Absent/non-reproducible methodology = disqualification.)
**HOW:**
- **Time-to-visible:** instrument main.py — at the moment the dock's first `paintEvent` completes, append a monotonic timestamp to `/tmp/jiopc-startup.log`; session start reference = the autostart launcher script logging its own start time. Report the delta. For app-cold-start (not whole login) also use `hyperfine --warmup 2 'python3 src/main.py --measure-startup-and-exit'` (a flag that quits right after first paint). ≥ 20 runs; report p50/p95.
- **Idle CPU:** `pidstat -p $(pgrep -f jiopc-home) 1 30` → average %CPU; run 5 sessions; also record `top` screenshot. Conditions stated: dock + menu(opened once) + 4 widgets + content cached, no user input.
- **Idle RSS:** wait 5 min (scripted sleep), read `VmRSS` from `/proc/<pid>/status`. Also report `pmap` summary noting shared Qt libraries — honest methodology notes = Documentation points.
- All scripts committed; results as CSV + a tiny table in README.
**Tuning levers if over budget:** RSS → cap icon pixmap cache, load menu icons lazily, `import` heavyweight modules inside functions; CPU → find the timer (`strace -c` or py-spy), pause carousel when covered, ensure the X listener blocks on events rather than spinning; startup → defer menu build, defer CMS fetch (already designed that way), precompile with `python3 -m compileall` in postinst.

---

### Day 12 — Documentation
- **README.md:** what/why, screenshots inline, benchmark table, usage guide, honest known-limitations (judges explicitly score honesty).
- **design.md:** architecture diagram (Mermaid is fine), one section per component explaining the *mechanism* (steal the HOW blocks of this roadmap), data-flow diagram for CMS pipeline, technology justification (Section 2 paragraph), limitations.
- **INSTALL.md:** literally copy-paste-tested on a `00-clean` restore — have Claude Code rewrite it from your shell history of the successful run.
- **cms-schema.md**, screenshots at both resolutions (first open w/ wizard, customized, alternate theme, offline mode — the four shots the deliverable list names).

### Day 13 — Demo Video + Usability Test
**Video (≤ 3 min, recorded INSIDE the VM — show the VirtualBox chrome in frame at the start to prove it):** 0:00 fresh login → shell appears (show a visible stopwatch/timestamp) → wizard, make choices · 0:40 dock: launch, indicators, focus, pin/reorder · 1:10 menu: search, categories, recommended · 1:35 widgets: arrange, add the live-coded 25-line plugin · 2:05 theme switch light→dark live · 2:20 offline mode (kill endpoint, restart, cached content) · 2:35 the VM-reassignment simulation clip · 2:50 benchmark numbers on screen. Record with `vokoscreenNG`/OBS on the host capturing the VM window, or SimpleScreenRecorder inside the VM.
**Usability test:** 5 people (hostel friends), no instructions, task "open a music/video app". Pass = 4/5 within 60 s. Record times in `benchmarks/usability.md`. If you fail, the fix is almost always: bigger search bar, clearer dock-menu button.

### Day 14 — Submission Gate
Restore `00-clean` → run the ENTIRE EVALUATE checklist (Section 10) yourself, checking boxes with evidence → fix → repo public? INSTALL.md present? video link works in incognito? → write the 300-word solution description (lead with: single-process Qt shell, offline-first CMS, token theme engine, plugin widget architecture, all budgets met with p50/p95 evidence) → submit.

---

## 7. Micro-Experiment Catalog

Each: **GOAL → PASS → fallback if it fights you > 2 h.** All run inside the VM unless noted.

**ME-01 · Blank shell window + RAM baseline** *(Day 0, 30 min)*
Goal: frameless 400×60 Qt window appears bottom-center in LxQt; read `VmRSS` from `/proc/<pid>/status` after 60 s.
PASS: window visible; RSS recorded (expect ~50–90 MB for PyQt — this number tells you your remaining budget for everything else; write it in PROGRESS.md).
Fallback: if PyQt6 RSS is shockingly high, test PyQt5; if both >150 MB something's wrong with the measurement (check you're reading RSS not VSZ).

**ME-02 · Dock window type + struts** *(Day 2 morning — the highest-risk ME in the project)*
Goal: window gets `_NET_WM_WINDOW_TYPE_DOCK` and `_NET_WM_STRUT_PARTIAL`; verify with `xprop -id <winid>`; maximize xterm → it stops above the dock.
PASS: xprop shows both properties; maximized window respects the strut; dock stays above normal windows, no decorations, on all desktops.
Fallback: if Qt overwrites the properties, set them via python-xlib in a `QTimer.singleShot(0, ...)` after `show()`, and re-assert on any `changeProperty` race. If Openbox still ignores struts, re-map the window after setting (unmap/map). Known-solvable — docks all do this — but budget the morning for it.

**ME-03 · Enumerate .desktop files** *(Day 2, 30 min)*
Goal: script prints every visible app from system + local + Flatpak export dirs: id, Name, Comment, Categories, icon-resolved?
PASS: list matches LxQt's own menu (spot-check 10 apps); NoDisplay entries excluded; at least one Flatpak-installed test app (install `flatpak install flathub org.gnome.Calculator`) appears.

**ME-04 · Launch from Exec=** *(Day 2, 20 min)*
Goal: launch 5 diverse apps (one with `%U` in Exec, one Flatpak) via parsed Exec.
PASS: all 5 open; no zombie processes (`ps` clean after closing them); jiopc process unaffected.

**ME-05 · Event-driven running-window tracking** *(Day 2–3, the second-highest-risk ME)*
Goal: script subscribes to root-window PropertyNotify; prints `+ firefox (0x3a00007)` / `- firefox` as you open/close windows; CPU of the script ~0% while nothing changes.
PASS: events fire reliably for ≥5 different apps incl. a Flatpak; WM_CLASS→desktop-id matching correct for ≥80% (log the misses — they tune your heuristic); `pidstat` shows ~0% between events.
Fallback: poll `wmctrl -lx` at 2 s interval as a *temporary* bridge (note: costs CPU budget; replace before Day 11 benchmarks).

**ME-06 · Activate a window** *(Day 3, 15 min)*
Goal: given a window id from ME-05, raise+focus it via `_NET_ACTIVE_WINDOW` client message.
PASS: works for normal and minimized windows.

**ME-07 · Desktop-layer stacking vs pcmanfm-qt** *(Day 6 morning)*
Goal: map a full-screen `_NET_WM_WINDOW_TYPE_DESKTOP` Qt window; confirm it renders above pcmanfm-qt's desktop but below ALL normal windows; icons/right-click of LxQt desktop being covered is acceptable.
PASS: our layer visible at desktop level; normal windows cover it; lxqt-panel unaffected.
Fallback: disable the pcmanfm-qt desktop module via LxQt session user-config (Session Settings → Basic Settings → Modules → Desktop off writes a user-level key; replicate that key from code on first run) and own the layer outright. Document whichever path wins in design.md.

**ME-08 · Offline-first CMS pipeline** *(Day 6, 45 min)*
Goal: tiny script: load cache → render(print) → background fetch from `http://localhost:8765/feed.json` → atomic cache replace → re-render. Then kill the server and rerun the script.
PASS: with server: fresh content; without server: cached content + a clean warning log line; first run ever with no cache and no server: "empty state" not a traceback.

**ME-09 · Minimal .deb** *(Day 1)*
Goal: `build-deb.sh` produces a .deb installing a hello-world `jiopc-home` binary.
PASS: on a `00-clean` restore (after INSTALL.md's dependency line): `sudo dpkg -i` → zero errors → `jiopc-home` runs. `dpkg -r jiopc-home` removes cleanly too.

**ME-10 · Autostart timing** *(Day 1)*
Goal: the autostart .desktop launches the hello shell at LxQt login; launcher script logs a timestamp at start and at first paint.
PASS: appears on login with no interaction; delta recorded (baseline for the 3 s budget — expect <1 s for the skeleton; the gap to 3 s is your feature budget).

**ME-11 · Live QSS re-theme** *(Day 8 morning, 30 min)*
Goal: two token JSONs + one QSS template; a test window with a button toggles them via `setStyleSheet`.
PASS: instant visual swap, no flicker, no restart, custom-painted area also updates via the signal.

**ME-12 · RDP reality check** *(Day 10)*
Goal: xrdp into the VM at 1280×720; use the shell for 5 minutes.
PASS: readable text, no layout breakage, animations don't smear/stutter; idle CPU still in budget while connected via RDP.

**ME-13 (optional) · Flatpak WM_CLASS quirks** *(only if ME-05 matching is poor for Flatpaks)*
Goal: print WM_CLASS for 3 Flatpak apps; adjust matcher (Flatpak app-ids like `org.gnome.Calculator` usually equal the desktop-file id — add that rule).

---

## 8. Working With Claude Code — Operating Manual

1. **Session start ritual:** open Claude Code in the repo; it reads CLAUDE.md automatically. First message: *"We're on roadmap Phase X. Read Section 6 Phase X + Section 7 ME-yy in JIOPC_CHALLENGE1_ROADMAP.md, then propose your implementation plan before writing code."* Approving a 5-line plan catches misunderstandings before they cost an hour.
2. **One phase-step per conversation thread.** Long threads drift; `/clear` between major steps. The roadmap + CLAUDE.md + PROGRESS.md ARE the memory — keep PROGRESS.md updated so a fresh session can resume instantly.
3. **Make Claude Code self-verify.** Give it the ssh command to the VM. Demand of every task: "run it via deploy.sh and show me evidence (log lines / xprop output / pidstat numbers) before declaring done." Evidence-or-it-didn't-happen.
4. **Use it for the boring excellence:** docstrings, INSTALL.md from shell history, the Mermaid diagrams in design.md, benchmark scripts, the QSS template, code-review sweeps ("find every hardcoded color", "find every blocking call on the GUI thread", "find every write outside the three XDG dirs").
5. **You stay the architect.** Claude Code should never silently change the persistence paths, add a dependency, add a polling loop, or spawn a second process — those are CLAUDE.md violations; if it proposes one, it must flag it to you first (this rule is *in* CLAUDE.md via the Hard Rules).
6. **Daily closing ritual (10 min):** commit, update PROGRESS.md, write tomorrow's first task as a TODO at its top, snapshot the VM if system-level anything changed.

---

## 9. Risk Register

| Risk | Likelihood | Mitigation / trigger |
|------|-----------|----------------------|
| Qt fights X11 props (dock type/struts) | Medium | ME-02 Day 2 with the full morning budgeted; fallback sequence written there |
| RAM creeps past 200 MB | Medium | RSS check is part of EVERY phase's TEST; tuning levers in Phase H; worst case switch icon strategy to on-demand loading |
| pcmanfm-qt desktop conflict | Medium | ME-07 Day 6 morning; fallback = disable its module via user config |
| Flatpak apps don't match running windows | Medium | ME-13; rule "flatpak id == desktop id" covers most |
| dpkg -i dependency failure on fresh VM | Was high → killed Day 1 | Phase P first; INSTALL.md lists dep installs; re-tested at Day 14 gate |
| Time overrun | High (it's a hackathon) | Cut order in Section 5; Days 10–14 are protected — never steal from them for features |
| Benchmarks fail budgets on Day 11 | Low-Med | Budgets enforced per-phase, so Day 11 is confirmation, not discovery |
| Demo video over 3 min / not in VM | Low | Shot list in Day 13; VM chrome visible at open |

---

## 10. Definition of Done — EVALUATE Checklist Mapping

Run on Day 14 against a `00-clean` restore. Every row needs evidence (screenshot / log / video timestamp).

| Checklist item | Built in | Evidence |
|---|---|---|
| .deb installs cleanly on fresh 24.04 | Phase P | terminal capture |
| Shell visible < 3 s after login | P + H | startup log p50/p95 |
| Dock: pin/unpin/reorder, launch, running indicators | A | video 0:40 |
| Menu: recent, categories, order-by, search, recommended | B | video 1:10 |
| Widgets: add/remove/arrange; CMS-rendered content | C | video 1:35 |
| Content from configurable CMS endpoint | C | settings.json + demo |
| Offline degradation, no crash | C | video 2:20 + log |
| Theme: colors+fonts across all components, persists | D | video 2:05 |
| Preferences survive simulated VM reassignment | I | video 2:35 + script in repo |
| Wizard once-only | E | test log |
| Idle CPU < 10% (30 s) | H | pidstat CSV |
| Idle RAM < 200 MB (VmRSS @ 5 min) | H | proc capture |
| Renders at 1280×720 over RDP | I | screenshots |
| LxQt session functional | A/C/I | video or screenshot of lxqt-panel |

---

## 11. Bonus Goals — only after Section 10 is fully green

Ranked by points-per-hour:
1. **Theme import/export** (~30 min): "Export" copies the active token JSON to a chosen path; "Import" copies into `~/.config/jiopc/home/themes/`. Free, demoable.
2. **Extra widget plugin(s)** (~1 h each): a Pomodoro/focus timer (matches the reference design!), a weather widget reading from the same CMS feed. Each one re-proves engine extensibility.
3. **'Try this today' widget** (~2 h): pick one feature/app the usage log says is unused, rotate daily by seeding a PRNG with the date, one-click launch. Pairs beautifully with the recommendation engine narrative.
4. **Persona detection** (~3–4 h, only if everything else is polished): cluster aggregate category usage into 3 hand-defined personas (Student / Creator / Office), adapt default pins + widget set. Describe honestly in design.md as a heuristic, not ML.

---

## 12. Final Mindset Notes

- The judges reward **completeness + evidence + honesty**. A limitations section that says "WM_CLASS matching uses heuristics and fails for ~X% of apps; we log misses" earns more than pretending it's perfect.
- Your `experiments/` folder, per-phase benchmark discipline, and the reassignment-simulation script are themselves differentiators — most teams will have none of the three.
- When stuck > 2 hours on anything: take the fallback, write a TODO + limitation note, move on. The schedule is the product.

*— End of roadmap. PROGRESS.md is the living checklist; this file is the spec. Good luck — now go take that `00-clean` snapshot.*