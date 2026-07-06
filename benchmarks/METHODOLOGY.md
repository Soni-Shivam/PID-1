# Benchmark methodology

Every number below is reproducible with one command against the target VM
(Ubuntu 24.04 + LxQt, X11, no compositor, 4 vCPU / 8 GB):

```bash
./benchmarks/measure.sh            # 1280x720 (mandated minimum test resolution)
./benchmarks/measure.sh 1920x1080  # optional cross-check at a larger resolution
```

The script rsyncs the current `src/` to the VM, restarts the app, and reports
three numbers plus the raw `pidstat` trace. It assumes VM access at
`vboxuser@127.0.0.1:2222` (this repo's dev VM); point `VM`/`PORT` in the script
at your own target if different.

## What each budget measures, and how

### 1. Startup (login-to-visible < 3 s)

Two related numbers, because they measure different things:

- **App-internal first paint** (`proc_s` in `/tmp/jiopc-startup.log`): wall
  time from Python interpreter start (`T_IMPORT` in `src/main.py`) to the
  dock's first `QTimer.singleShot(0, ...)` firing after the event loop draws
  it. This is what `measure.sh` reports — it isolates the app's own boot cost
  from VM/session variability, so it's the number to watch when optimizing
  code.
- **Login-to-visible** (the actual budget in the roadmap): wall time from the
  LxQt autostart session signal to that same first paint, via the packaged
  `.deb` + `/etc/xdg/autostart/jiopc-home.desktop` entry. This was last
  measured end-to-end on a freshly-restored VM snapshot via
  `scripts/gate-g1.sh` at **0.621 s**, ~5x under budget. It requires a snapshot restore
  to test honestly (a warm VM's disk/page cache makes every run look
  artificially fast), so it is not re-run on every code change — only at
  packaging gates. The app-internal number tracks regressions between gates.

### 2. Idle CPU (< 10%, 30 s average)

`pidstat -p <pid> 1 30` sampled with the shell fully idle (no windows opened,
no user interaction) after the app has settled. Averaged over the 30 s window
by `pidstat`'s own summary line. Because there is no compositor, this number
is purely the app's own event-driven cost (X11 `PropertyNotify` watcher +
QTimer clock tick + any auto-advancing widget like the carousel) — there is
no compositor overhead to separately account for.

### 3. Idle RSS (< 200 MB)

`VmRSS` from `/proc/<pid>/status`, read right after the CPU sample. This is
the single-process budget: one `QApplication` hosting dock + menu + desktop
widget grid + CMS cache, so there is only one number to track (see
`design.md` for why single-process was chosen).

### 4. 1280x720 rendering

Not a number — a visual check. `benchmarks/results/<date>_screenshots/`
holds full-desktop captures at 1280x720 in both themes, plus the app menu and
Widget Store overlays open, taken with compositing off. Captured via a small
PyQt5 grab script (`app.primaryScreen().grabWindow(0).save(...)`) run inside
the VM, since no `scrot`/`import`/`maim` is installed there — screenshotting
locally and trusting scaling would hide exactly the clipping/overlap bugs
this check exists to catch (see `results/2026-07-06.md` for a case where this
caught a real one).

### 5. Usability

Not automatable from this environment. The roadmap's Phase H asks for a
5-person cold-user test ("open a music/video app", pass = 4/5 within 60 s),
recorded in `usability.md`. That requires real testers and has **not** been
run yet — see `usability.md` for the protocol and current status. Do not
treat the screenshots in `results/` as a substitute; they only demonstrate
that the surfaces render without layout bugs, not that a first-time user can
navigate them.

## Honesty notes

- All idle-CPU/RSS numbers here are from a warm dev VM reused across many
  runs in one session, not a freshly-restored snapshot. That's fine for
  these two budgets (they measure steady-state behavior, not first-boot
  disk/cache effects) but is *not* fine for the startup-time budget, which is
  why login-to-visible is sourced from the G1 gate instead.
- Numbers will vary run-to-run by the amounts shown in the p50/p95 table in
  `results/`; report a range, not a single cherry-picked run.
