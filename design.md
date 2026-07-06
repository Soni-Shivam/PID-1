# design.md — JioPC Home (Challenge 01: Engaging Desktop Experience)

This document covers architecture, data flow, technology justification, and
known limitations for all five components, per the challenge's deliverables
list. For build/install steps see `INSTALL.md`; for benchmark methodology
and numbers see `benchmarks/METHODOLOGY.md` and `benchmarks/results/`; for
the CMS content contract see `cms-mock/SCHEMA.md`.

## 1. Technology choices, and why

**Python 3.11+ · PyQt5 (Qt5 Widgets) · python3-xlib · requests · python3-xdg ·
plain JSON persistence. One process, one `QApplication`.**

| Choice | Why |
|---|---|
| PyQt5 over PyQt6/PySide6 | LxQt on the target Ubuntu 24.04 image is itself Qt5-based, so PyQt5 shares the platform's already-loaded Qt5 libraries rather than pulling in a second major Qt version — smaller footprint, and no risk of two incompatible Qt runtimes coexisting in the session. Verified as the correct choice on Day 0 by checking the installed LxQt/Qt version before committing. |
| Python over C++ | The five components are UI-orchestration-heavy, not compute-heavy; Python's iteration speed mattered far more than its ~30–50 MB interpreter overhead, which the idle-RSS budget comfortably absorbs (measured: 97 MB baseline with zero features, 145–155 MB with the full shell — see `benchmarks/results/`). |
| Qt Widgets (not Qt Quick/QML) | Renders entirely on the CPU rasterizer with no compositor and no GPU dependency — QML's scene-graph model assumes a GPU-backed (or at least compositor-friendly) pipeline that this target explicitly does not have. |
| One `QApplication` process for all five components | One Qt runtime in RAM instead of five; `setStyleSheet()` re-themes dock+menu+widgets atomically in one call; one autostart entry, one process to benchmark, no IPC to design or debug. This is the single biggest lever against the 200 MB budget. |
| `python3-xlib` for X11 (not `wmctrl` shellouts) | The dock needs to know about window open/close/focus continuously, not once. `python3-xlib` lets `ClientListWatcher` block in `select()` on the root window's `PropertyNotify` and wake only on real events — 0.00% measured idle CPU from this path — where polling `wmctrl` on a timer would cost real, continuous CPU against the 10% budget. |
| `core/qt_compat.py` shim | A single import boundary (`from core.qt_compat import ...`, never `PyQt5` directly) so a future Qt-binding switch is a one-file change, per CLAUDE.md's hard rule. |
| Plain JSON + atomic write (`core/store.py`) | Every persisted file (pins, layout, theme, usage, wizard flag) is small and human-diffable; a database would add a dependency and a migration story for no benefit at this scale. Atomicity (write-to-temp + `fsync` + `os.replace`) is the one thing that does matter — it's what makes "floating VM, NFS home, could be interrupted mid-write" safe. || Electron explicitly rejected | Bundling Chromium means a GPU-accelerated-compositing mental model and a baseline RSS in the hundreds of MB before a single feature is added — categorically incompatible with the 200 MB / no-GPU budget (see PDF Section 2.3, "What we are not looking for"). |
## 2. Process & directory architecture

```
jiopc-home (single QApplication, src/main.py)
├── core/            qt_compat · paths · store · theme · x11 · colors · background · user · secrets
├── apps/            desktop_entries (scan .desktop) · launcher (QProcess) · usage (launch log)
├── dock/            Component A — widget.py (view) · model.py (pins+running) · customize.py
├── menu/            Component B — window.py (view) · app_model.py (list+filter+sort) · recommend.py
├── widgets/         Component C — engine.py (plugin ABC+discovery) · cms.py · grid.py · desktop.py
│   └── plugins/     one file per widget type (see 5.3)
├── wizard/          Component E — window.py + completion flag
└── settings/        theme + widget-arrange settings UI (Component D's user-facing surface)
```

All persistent state is under the three XDG dirs from `core/paths.py`
(honours `XDG_*_HOME` overrides, never writes elsewhere):

| Directory | Holds |
|---|---|
| `~/.config/jiopc/home/` | `dock.json` (pin order), `layout.json` (widget grid), `settings.json` (theme name + overrides + `cms_endpoint`/`cms_refresh_minutes`), `onboarding_done` (wizard flag) |
| `~/.local/share/jiopc/home/` | `usage.json` (per-app launch count + last-launch time), `themes/*.json` (user-saved custom themes) |
| `~/.cache/jiopc/home/` | `feed.json` (last-good CMS fetch), `images/*.img` (fetched hero images) — safe to delete, everything here is a cache |

Because this is the *only* state and it all lives under `$HOME` (NFS in the
real deployment), a session on a different VM with the same home directory
resumes with identical pins, layout, theme, and usage history — this is the
"survives VM reassignment" requirement, and it falls out of the architecture
rather than needing special-case code.

## 3. Component A — Dock

**Files:** `dock/widget.py`, `dock/model.py`, `dock/customize.py`, `core/x11.py`.

- **Persistence:** `DockModel` holds `pins: list[str]` (app ids), loaded from
  and saved to `dock.json` via `core/store.py`. First run seeds a default set
  by walking a candidate list (`firefox`, a file manager, a terminal, an
  editor, `lxqt-config`) and keeping only what's actually installed — so the
  default dock is never full of launch-failing icons on a minimal image.
- **Running-window tracking:** `core/x11.py`'s `ClientListWatcher` is a
  `QThread` that blocks in `select()` on the root window's `PropertyNotify`
  and diffs `_NET_CLIENT_LIST` on wake, resolving each window's `WM_CLASS` to
  an app id via an index built from every installed `.desktop` file's
  `StartupWMClass`/id/`Name` (handles the common mismatch case, e.g. a
  Flatpak app reporting a `WM_CLASS` that doesn't match its desktop-id). This
  is event-driven, not polled — the mechanism behind the 0.00–0.10% idle CPU
  measured with the dock's running-indicators active.
- **Window type & no-GPU rendering:** the dock sets
  `_NET_WM_WINDOW_TYPE_DOCK` via a raw property change (`core/x11.py`) so the
  WM treats it correctly, and reserves screen space via
  `_NET_WM_STRUT_PARTIAL`. There is no compositor, so "hover magnification"
  (macOS-style) is plain Qt geometry animation (`QPropertyAnimation` on
  button size/position), not a shader or blur effect — CPU-cheap by
  construction, not by budget-fitting after the fact.
- **Rounded pill without a compositor:** `_refresh_pill_and_mask()` builds a
  `QRegion` (rounded pill ∪ per-icon overflow rects for anything magnified
  wider than the pill) and calls `setMask()` on the window. This is how a
  soft rounded shape exists at all with compositing disabled — the mask
  recomputes every layout pass so it stays correct as the icon count or
  scale changes (this recompute is what a stale kill-loop in my own test
  tooling briefly made look broken during this session's screenshot pass —
  see the git history around the quick_tiles fix for the unrelated widget
  version of the same "recompute on resize, don't assume a fixed count"
  lesson).
- **Autohide:** the dock slides off the left edge and reveals on
  edge-hover/mouse-move (`enterEvent`/`mouseMoveEvent`), reserving zero strut
  while hidden so a maximized window gets the full screen width; this is a
  `QPropertyAnimation` slide, not a compositor effect.
- **Pin / unpin / reorder / launch:** click launches via
  `apps/launcher.py` (`QProcess.startDetached`, field-code stripping per the
  desktop-entry spec); right-click opens a context menu for
  pin/unpin/customize; drag-and-drop reorders and persists immediately;
  dropping an app from the menu onto the dock pins it (shared MIME type
  `application/x-jiopc-dock-app`).

## 4. Component B — Application Menu

**Files:** `menu/window.py`, `menu/app_model.py`, `menu/recommend.py`,
`apps/desktop_entries.py`, `apps/usage.py`.

- **App enumeration:** `apps/desktop_entries.py` scans
  `/usr/share/applications/` and `~/.local/share/applications/` (PyXDG),
  extracting id, name, icon, `Comment=`, and `Categories=`. Rescanned once at
  menu-build time, not polled.
- **Search / filter / sort:** `AppListModel` (a flat `QAbstractListModel`)
  feeds `AppFilterProxy` (`QSortFilterProxyModel`), which implements:
  - live fuzzy search (`fuzzy_match` — ordered-subsequence match over
    name+comment, so `"clc"` finds "Calculator" and `"gimp"` finds "GNU
    Image Manipulation Program" via initials, not just substring);
  - category filter, from the `.desktop` `Categories=` field, as pill
    chips;
  - order-by name / most-used / recently-used, backed by `usage.json`.
- **Recently Used / Most Used:** `menu/recommend.py`'s `recently_used()` and
  `most_used()` sort apps that appear in `usage.json` by `last_ts` or
  `count` respectively.
- **Recommended:** `recommended()` builds a weighted category-preference
  vector from the user's launch history (category → summed launch-count
  weight), then scores every *never-launched* app by the overlap between its
  declared categories and that vector (normalised by
  `sqrt(len(categories))` so apps with many categories don't win purely on
  breadth), with a small per-session random jitter so ties don't feel frozen
  across opens. With no history yet, it falls back to a random sample rather
  than an empty section — so Recommended is never blank on first login.
- **Launch + usage persistence:** click launches via the same
  `apps/launcher.py` path as the dock, then `apps/usage.py:record_launch()`
  increments count and stamps `last_ts` in `usage.json` (atomic write) — the
  same file both this and the dock's nothing-to-do-with-menu code read, so
  Recently/Most-Used/Recommended and any future usage-driven feature all see
  one consistent history.

## 5. Component C — Widget Engine

**Files:** `widgets/engine.py`, `widgets/grid.py`, `widgets/desktop.py`,
`widgets/cms.py`, `widgets/plugins/*.py`.

### 5.1 Plugin contract

`WidgetPlugin` (`widgets/engine.py`) is a small ABC:
`id`, `name`, `description`, `icon`, `default_size`, `sizes` (the resize
cycle), `needs_cms`, `category`, and one method, `create_view(ctx) -> QWidget`.
`discover_plugins()` walks `widgets/plugins/` with `pkgutil.iter_modules` and
instantiates every `WidgetPlugin` subclass found — **adding a widget means
adding one file to that directory**, not touching the engine, the grid, or
the Widget Store, which auto-lists whatever `discover_plugins()` returns.
This is the literal "extensible — a plugin, not a shell rewrite" requirement.
Twelve plugins currently exist (four required — carousel, news, quick-launch
tiles, greeting/clock — plus eight more: a plain clock, calendar, focus
timer, system health, music player, app shortcuts, digital wellbeing, and an
assistant — as the bonus-goals "additional widget plugins" evidence).

### 5.2 Grid, layout persistence, and resolution-adaptive rendering

`SnapGrid` (`widgets/grid.py`) is a fixed `GRID_COLS × GRID_ROWS` (3×2) slot
grid; each `WidgetCard` occupies `(col, row, w, h)` in grid units, positioned
by absolute `setGeometry` (not a Qt layout — needed for the drag-to-swap and
hover-chrome interactions). Layout is persisted to
`~/.config/jiopc/home/layout.json` as a flat list of
`{plugin_id, col, row, w, h}` on every add/remove/resize/reorder.

A widget's *pixel* cell size is not fixed — it's `(available width or
height) / grid dimension`, so the same `(1,1)` slot is a different number of
pixels tall at 1280×720 than at 1920×1080/1920×945. This matters: during
this submission's benchmark pass, the quick-launch tiles widget was found
rendering an assumed-fixed 3 rows of tiles regardless of its actual cell
height, which overflowed past the card border at 1280×720 while happening
to fit at a larger dev-resolution (see `benchmarks/results/2026-07-06.md`
for the full writeup). The fix — compute how many tile rows actually fit the
card's real allocated height, both at first render and on resize, instead
of assuming a count — is the general pattern any new widget should follow
if its content count depends on available space: **query the real allocated
size, don't assume the dev machine's resolution is the only one that
matters.**

### 5.3 The four required widgets (plus eight more)

| Widget | File | Notes |
|---|---|---|
| Greeting/clock | `greeting_clock.py` | Personalised greeting (`core/user.py`) + live clock, 1 s `QTimer` |
| Hero carousel | `carousel.py` | Full-bleed image, auto-advances every 8 s while visible (paused on `hideEvent`, so covered-desktop costs 0 CPU), local-asset-first image loading with a remote-URL fallback (see `cms-mock/SCHEMA.md`). |
| News/headlines | `news.py` | CMS-fed headline list; click opens via the same `url:` action path as everything else. |
| Quick-launch tiles | `quick_tiles.py` | CMS-fed; see 5.2 for the resolution-adaptive fix. |
| Plain clock, calendar, focus timer, system health, music player, app shortcuts, digital wellbeing, assistant | `clock.py`, `calendar.py`, `focus_timer.py`, `system_health.py`, `music_player.py`, `app_shortcuts.py`, `digital_wellbeing.py`, `assistant.py` | Extensibility evidence (bonus goal). `system_health.py` reads `/proc` directly (no polling daemon); the others are locally-computed, non-CMS widgets. |

### 5.4 CMS pipeline

Full schema in `cms-mock/SCHEMA.md`; summary of the offline-first design
(`widgets/cms.py`):

1. **Construction:** serve the best content available with **zero network
   wait** — last-good cache → bundled `default_feed.json` → empty feed, in
   that order. A widget is never blank-and-stuck on a cold, offline boot.
2. **Refresh:** `CmsService.refresh()` fetches the configured endpoint on a
   background `QThread` with a 5 s timeout (never blocks the UI thread),
   called once at session start (`widgets/desktop.py:start()` — the spec's
   default cadence) and additionally on a repeat timer if
   `cms_refresh_minutes` is set in `settings.json` (0/absent = session-start
   only).
3. **Success:** atomic cache replace (`core/store.py`) + `content_updated`
   signal → every subscribed widget re-renders with new content.
4. **Failure** (timeout / connection error / HTTP error / invalid or
   schema-missing JSON): logged, previous content keeps serving unchanged —
   verified end-to-end this session by pointing `cms_endpoint` at an
   unreachable address and confirming no crash / no blank widget
   (`benchmarks/results/2026-07-06.md`, `screenshots/offline_*.png`).

## 6. Component D — Theme Engine

**Files:** `core/theme.py`, `src/themes/{dark,light,base.qss.tmpl}.json`,
`settings/dialog.py`.

- **Token model:** a theme is a flat JSON dict — colours (`bg`, `surface`,
  `accent`, `text`, …), `wallpaper`/gradient/glow tokens for the
  no-compositor painted background, and `font_family`/`font_size_base`. This
  is genuinely an *engine*: `dark.json` and `light.json` are both just data
  read by the same code path, and a user can define a third by saving one
  (`save_custom()` snapshots the live merged tokens to
  `DATA_DIR/themes/<name>.json`).
- **Apply mechanism:** `ThemeManager.apply()` renders `base.qss.tmpl`
  (`string.Template`) with the token dict and calls
  `QApplication.setStyleSheet()` once — this is what makes the theme apply
  *consistently* across dock, menu, and widgets in one call rather than
  needing each component to re-theme itself. Custom-painted (non-QSS) bits —
  the dock's running-indicator dot, the carousel's page dots, the desktop's
  painted gradient background — read `theme.tokens` directly and repaint on
  the `theme_changed` signal.
- **User overrides:** accent colour and font are stored separately as
  `theme_overrides` in `settings.json` and layered on top of whichever named
  theme is active on load, so "I like dark but with my own accent" survives
  switching themes, not just restarting.
- **Persistence:** active theme name + overrides live in `settings.json`
  under `~/.config/jiopc/home/` — survives VM reassignment like everything
  else.

## 7. Component E — First-Time Wizard

**Files:** `wizard/window.py`.

- **Runs once:** `is_done()` checks for
  `~/.config/jiopc/home/onboarding_done`; `main.py` shows the wizard 400 ms
  after boot (after the shell has painted, so the tour can point at live
  components) only if that flag is absent (or `JIOPC_FORCE_WIZARD=1` is set,
  a screenshot/demo hook).
- **Flag written on open, not on finish** — a deliberate choice: if the
  wizard is interrupted (window closed, session killed) partway through, it
  will not re-trigger and re-annoy the user on the next login. The tradeoff
  (a user who never touches the wizard at all still gets it marked "seen")
  was judged the better failure mode for a once-only onboarding flow.
- **Content:** personalised greeting (name from `core/user.py`, live
  time/date), a feature tour (dock/menu/widgets/theming), and initial
  choices (pick a theme, pin a few apps) that write through the same
  `ThemeManager`/`DockModel` APIs the rest of the app uses — the wizard has
  no parallel persistence path of its own.

## 8. Cross-cutting: idle-cost discipline

Every "must stay under budget" requirement traces to one of three
mechanisms used consistently across all five components:

1. **Event-driven X11**, not polling — `ClientListWatcher` and
   `HotkeyListener` both block in `select()`.
2. **QTimers only where the spec explicitly allows it** — the 1 s clock
   tick, and any per-widget auto-advance (carousel) is stopped on
   `hideEvent` so a covered desktop costs 0 CPU, not "less" CPU.
3. **One process** — see Section 1. There is nothing to sum across
   processes because there is only one.

Measured result (`benchmarks/results/2026-07-06.md`): idle CPU 0.10%
(budget 10%), idle RSS 145.5 MB at 1280×720 (budget 200 MB), first paint
p95 0.195 s / packaged login-to-visible 0.301–0.621 s (budget 3 s).

## 9. Known limitations

- **`fetched_hint_minutes` in the CMS schema is advisory only** — the client
  does not currently read it to decide freshness; refresh cadence is
  controlled purely client-side via `cms_refresh_minutes`. A real CMS
  producer can set it meaningfully for future client versions, but this
  version ignores it.
- **Widget Store preview cosmetic bug:** the Digital Wellbeing widget's live
  preview thumbnail in the Widget Store has an overlapping text label (its
  usage-ring legend overlaps the "most-opened app" line) at the small
  preview scale. Cosmetic, isolated to the store's preview rendering, does
  not affect the widget as placed on the desktop. Not fixed as of this
  writing.
- **Persona detection and theme import/export (bonus goals) are not
  implemented.** The Recommended-apps category-vector scoring in Component
  B is the one piece of usage-driven personalisation shipped; a full
  persona-detection system adapting default dock/menu/widget *selection*
  (not just menu ordering) was judged lower priority than hardening the
  five required components and the benchmark/documentation trail.
- **Login-to-visible has two related numbers, not one** (app-internal first
  paint vs. full packaged autostart timing) — see
  `benchmarks/METHODOLOGY.md` Section "Startup" for why, and don't read the
  smaller dev-loop number as the whole budget's proof by itself.
