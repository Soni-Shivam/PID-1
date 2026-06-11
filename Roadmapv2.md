# ROADMAP v2 — From "Complete" to "Winning"
### jiopc-home · Supersedes the day-plan in JIOPC_CHALLENGE1_ROADMAP.md (Sections 1–4 and 7 of v1 remain authoritative for constraints, MEs, and methodology)
**Context: Phases P, A, B functionally complete on Day 1–2. ~5 days of schedule surplus. This document spends that surplus where judges award points.**

---

## 0. State Audit (what is actually true right now)

**Done & evidenced:** .deb pipeline + autostart (239 ms login-to-visible, 13× under budget) · dock with EWMH type/struts, event-driven running indicators (0% idle CPU), launch/focus, pin/unpin/reorder via context menu, persistence · app menu with search/chips/order-by/recent/recommended strips, live FS-watch reload, Super+Space hotkey · core layer (qt_compat, paths, atomic store, x11) · usage + recommendation engine · 8 MEs passed with logged evidence.

**Open debts (each is scheduled below — none is optional):**
| # | Debt | Severity | Scheduled |
|---|------|----------|-----------|
| D1 | Hardcoded `_C` palettes + inline QSS in dock/widget.py and menu/window.py | HIGH — grows daily, blocks theming | Phase D pulled EARLIER (now Day 3) |
| D2 | Fresh-VM .deb proof unproven (00-clean restore didn't take) | DISQUALIFICATION-CLASS | Gate G1, Day 3 (not Day 14) |
| D3 | Dock + menu never visually confirmed by a human | HIGH — visual quality is a differentiator | Today, 15 min |
| D4 | HotkeyListener/ClientListWatcher not stopped on app quit (closeEvent won't fire) | LOW — add `app.aboutToQuit` cleanup | With D1 sweep |
| D5 | Drag-reorder + hover animation deferred | MED — "reorder" is satisfied by move-left/right; drag is polish | Polish sprint |
| D6 | Flatpak live-match unproven (0 flatpaks in VM) | MED — checklist-adjacent | Gate G1 (install org.gnome.Calculator) |
| D7 | RDP + 720p behavior unknown | MED | Pulled earlier: Day 6 |

---

## 1. The Win Thesis — where points actually come from

Scoring: Functionality 30 · Performance 25 · Code Quality 20 · Docs 15 · Innovation 10.

**What every serious competitor will have:** a dock, a menu, some widgets, a light/dark toggle, a wizard, a .deb. Checklist parity is table stakes — it gets you to ~70%, not to first place.

**What most competitors will NOT have (our edge, in order of leverage):**

1. **Visual quality that matches the reference design.** The Appendix screenshots show a polished, TV-dashboard aesthetic (greeting header, hero carousel, card widgets, pill chips, soft dark surfaces). Most Qt hackathon projects look like default-grey Qt. A shell that *looks like the reference* reads as "this team could ship this" to a Jio judge. → dedicated **Polish Sprint** (Section 5), the single biggest reallocation of our surplus.
2. **Crushing, beautifully-presented performance numbers.** We're at 239 ms vs 3000 ms budget, 0.00% idle CPU, ~117 MB RSS. Present these as a comparison table (budget vs p50 vs p95, margin column) on page one of the README. Performance is 25% of the score and we can max it.
3. **Evidence discipline.** ME logs, committed experiments/, reproducible benchmark scripts, a self-scored EVALUATE table with a proof link per row. Judges checking 50 repos reward the one that pre-did their job (Section 6).
4. **A live extensibility demo.** Writing a widget plugin on camera in <30 s proves "engine, not hardcode" better than any diagram.
5. **The floating-VM story told correctly.** The reassignment-simulation script + video clip shows we understood *their platform*, not just the feature list. Persona detection + 'Try this today' (bonus goals) extend the same narrative: a shell that adapts to the user across any VM.

**Anti-goals (where points are NOT):** more widgets than required before polish is done · clever animations that risk the CPU budget over RDP · refactors of working code · any feature not traceable to the checklist, bonus list, or the reference design.

---

## 2. Revised Schedule (Day 2 = today)

| Day | Block | Output | Gate |
|----|-------|--------|------|
| 2 | **D3 visual confirm** (15 min) → **Phase D: theme engine** (pulled early) | tokens + QSS template + light/dark + settings dialog; dock & menu migrated off `_C`; D4 cleanup | zero hardcoded colors outside themes/ |
| 3 | **Gate G1: fresh-VM proof** (morning) → **Phase C part 1: desktop layer + engine** | ME-07; desktop layer; WidgetPlugin ABC + discovery + layout persistence + arrange mode | **G1: dpkg -i on true 00-clean restore + flatpak match (D2, D6 closed)** |
| 4 | **Phase C part 2: CMS + 4 widgets** | ME-08; cms.py offline-first; greeting/clock, carousel, news, quick-tiles; mock feed + schema doc | offline kill-test green |
| 5 | **Phase E: wizard** + integration of all components | once-only flow, theme+pin choices, tour overlays | wizard re-trigger tests green |
| 6 | **D7 pulled early: RDP + 720p day** (= old Phase I, 4 days early) | xrdp at 720p/1080p; reassignment simulation script + recording; LxQt-intact check | all v1 Phase I tests green |
| 7–8 | **POLISH SPRINT** (Section 5) | reference-design parity pass; drag-reorder; hover scale; empty states; micro-interactions | side-by-side screenshot vs reference |
| 9 | **Bonus goals** (Section 7) | theme import/export · 'Try this today' · persona detection v0 · 1–2 extra plugins | each demoable in <20 s |
| 10 | **Benchmarks (Phase H)** + perf tuning | p50/p95 for all 3 metrics, scripts + CSV + METHODOLOGY.md | all budgets met with ≥3× margin |
| 11 | **Docs day** | README, design.md + Mermaid, INSTALL.md re-proven, cms-schema.md, screenshot set | INSTALL.md copy-paste-tested on 00-clean |
| 12 | **Video + usability test** | 3-min video per Section 8 script; 5-person test logged | video uploaded, link tested incognito |
| 13 | **Submission gate** + slack | full EVALUATE self-score with evidence links; submit | — |
| 14 | pure buffer | — | — |

Two structural changes vs v1: **Phase D before Phase C** (so every widget is born themed — D1 never grows again), and **integration/RDP testing pulled to Day 6** (so the polish sprint reacts to how it actually looks over RDP, not how it looks on the VirtualBox console).

---

## 3. Day 2 Detail — Theme Engine First (Phase D, revised for the existing code)

Everything in v1 Phase D stands, plus migration specifics for the code that now exists:

1. `core/theme.py`: ThemeManager — `load(name)`, `tokens` dict, `apply(app)` (QSS from `style.qss.tmpl` via `string.Template`), `theme_changed` signal. Active theme name in `settings.json`.
2. **Migration:** delete both `_C` dicts. Dock/menu QSS moves into the single template, keyed by `objectName`/dynamic properties already in place (`#MenuRoot`, `chip`, `tile`; add `#DockRoot`, give DockButton a class property). Custom-painted bits (indicator dot) read `theme.tokens["accent"]` and repaint on `theme_changed`.
3. **D4 fix in the same sweep:** in main.py, `app.aboutToQuit.connect(...)` stops the watcher + hotkey threads; remove reliance on closeEvent.
4. Settings dialog (minimal today, prettified in polish sprint): theme picker (light/dark/custom list), accent QColorDialog, font family+size, Save-as-custom. Live-applies.
5. ME-11 first (30 min), then migrate.
**Exit tests:** light↔dark swaps dock+menu live, no restart · `grep -rn "#[0-9a-fA-F]\{6\}" src/ --include=*.py | grep -v themes` → zero · restart persists active theme · threads stop cleanly on quit (no hang, no X errors in log).

---

## 4. Phase C refinements (Days 3–4, building on what exists)

v1 Phase C stands; deltas given the current codebase:
- `ctx` passed to `WidgetPlugin.create_view(ctx)` = `{theme: ThemeManager, cms: CmsClient, launcher: apps.launcher, apps: list[AppEntry]}` — quick-tiles and 'Try this today' reuse the launcher + usage paths already built.
- Desktop layer window: type `_NET_WM_WINDOW_TYPE_DESKTOP` via a new `x11.set_desktop_type()` (same pattern as `set_dock_type`, already proven). ME-07 decides coexist-vs-replace re pcmanfm-qt; whichever wins, write the decision + reason into design.md the same day.
- Greeting widget shares the GECOS/time-of-day helper with the wizard — put it in `core/user.py` once.
- Carousel: pause auto-advance when any normal window is open — the ClientListWatcher already knows; expose `has_normal_windows` on it rather than adding a second X connection.
- CMS images: cache to `~/.cache/jiopc/home/img/<sha1>.<ext>`; placeholder pixmap until loaded; never fetch on the GUI thread (one QThread worker, queue).

---

## 5. The Polish Sprint (Days 7–8) — the differentiator

Goal: side-by-side with the challenge's Appendix screenshots, ours reads as the same product family. This is a *design* sprint executed in Qt; work from a checklist, not vibes.

### 5.1 Design language (derive once, apply everywhere via theme tokens)
- **Dark base like the reference:** deep neutral surfaces (near-black blue-grey), one accent, white text with a muted secondary. Already close — formalize as the `dark` theme tokens and tune by eye over RDP.
- **Typography scale:** one family (system Inter/Cantarell/DejaVu Sans), sizes as tokens: greeting 28–32, section headers 14–15/600, body 11–12, chip 12. Nothing outside the scale.
- **Card system:** every widget = same card recipe (surface color, 14 px radius via the existing mask technique, 16 px inner padding, 12 px gap grid). Consistency reads as quality.
- **Spacing rhythm:** all margins/paddings multiples of a `spacing_unit` token (4 px). Sweep dock + menu + widgets to the grid.
- **Iconography:** Papirus is already installed (pulled in by the lxqt metapackage) — prefer `QIcon.fromTheme` against it; consistent icon set beats mixed hicolor fallbacks.

### 5.2 Component passes (each ≤ half a day, timebox hard)
**Dock:** hover scale animation (pre-rendered 2-size pixmaps + 120 ms QPropertyAnimation per v1) · drag-reorder (QDrag within the row; model.reorder() already exists) · tooltip styling via QSS · subtle 150 ms fade-in on login (windowOpacity steps — verify over RDP, drop if it smears).
**Menu:** greeting line at top ("Good evening, Shivam") reusing core/user.py · chip row horizontal-scrolls at 720p instead of wrapping · keyboard navigation (arrows move grid selection; Enter launches — also helps the usability test) · empty-search state ("No apps match — try a category").
**Desktop/widgets:** hero carousel with image, title, subtitle, CTA button exactly like the reference 'Got a doubt? We've got you' card · news widget as headline list with source+time muted line · quick-tiles 2×2 with icon+label+sub-label · greeting/clock top-left large type.
**Wizard:** full-bleed pages, one idea per page, big Next button, progress dots — first impression of the demo video.

### 5.3 Quality gates for the sprint
- Screenshot ours vs reference side-by-side → a stranger says "same product".
- All polish survives: 1280×720, RDP, light theme, compositing off.
- Idle CPU re-measured after animations land: still ~0% (animations must be event-driven only).

---

## 6. Evidence & Scoring Pack (Day 11, prepared all along)

**README.md structure (judge-first ordering):** hero screenshot → 3-line what/why → **performance table** (metric | budget | our p50 | our p95 | margin) → feature checklist with ✅ per EVALUATE row → install (3 commands) → usage → architecture link → limitations.
**design.md:** architecture Mermaid (process, threads, data flow) · per-component mechanism (lift from v1 HOW blocks + what ME evidence proved) · CMS schema + sequence diagram (fetch/cache/offline) · technology justification · WM note (Ubuntu 24.04 lxqt metapackage ships xfwm4 as session WM; tested against it, compositing on AND off — D2's compositor finding becomes a documented robustness point, with the root cause we identified) · honest limitations (WM_CLASS heuristic %, OnlyShowIn decision, single-monitor assumption).
**Self-scored EVALUATE table** in README or SUBMISSION.md: every checklist row → Yes + link (video timestamp, benchmark CSV, screenshot, script). This is the single highest-leverage doc artifact: it converts judge effort into judge confidence.
**benchmarks/**: METHODOLOGY.md (exact commands, run counts, VM spec, how to reproduce in one command) + results CSVs + the usability test log (5 names anonymized, task, times, pass 4/5).

---

## 7. Bonus Goals (Day 9) — now affordable, specs

Build in this order; each must demo in <20 s or it's cut:
1. **Theme import/export (~30 min):** Export = save active tokens JSON via QFileDialog; Import = copy into user themes dir + switch. Demo: export dark-custom, delete, re-import.
2. **'Try this today' widget (~2 h):** candidates = apps with usage count 0 (recommend.py already computes) + a static list of JioPC feature tips; pick = `random.Random(date.today().isoformat()).choice(...)` so it rotates daily but is stable within a day; one-click launch via ctx.launcher. Reuses everything; pure narrative win.
3. **Persona detection v0 (~3 h):** map category-vector (recommend._category_vector already exists) → 3 hand-defined personas (Student: Education/Science · Creator: Graphics/AudioVideo/Development · Everyday: Network/Office/Utility) by max weighted overlap; persona stored in settings.json; effects: default quick-tiles set + recommended-row weighting + wizard offers persona presets. design.md describes it honestly as a transparent heuristic with thresholds, upgrade path sketched.
4. **Extra plugins (1 h each, max 2):** Pomodoro/focus timer (matches reference!) and a weather tile fed from the same CMS feed (add `weather` section to schema — shows schema extensibility too).

---

## 8. Demo Video v2 — script for 3:00

Recorded at 1920×1080 inside the VM, VirtualBox chrome visible in the first seconds. Cut hard; no dead air; captions over each scene.
- 0:00–0:10 Title card over fresh login: "JioPC Home — full shell, 239 ms to visible" (stopwatch overlay).
- 0:10–0:40 First-run wizard: greeting with real name → pick dark theme (screen re-themes live mid-wizard — money shot) → pin 3 apps → land on finished desktop.
- 0:40–1:05 Dock: launch, indicator dot, second window, click-to-focus, drag-reorder, maximize-respects-dock.
- 1:05–1:30 Menu: Super+Space, type 2 letters → instant filter, category chip, order-by, Recommended row ("apps you haven't tried, ranked by your habits").
- 1:30–1:55 Widgets: arrange mode, drag a card, remove/add; carousel CTA launches an app from CMS content.
- 1:55–2:15 **Live extensibility:** paste a 25-line quote-widget plugin file over SSH → it appears in Add Widgets immediately.
- 2:15–2:35 Offline: kill mock CMS, restart shell on camera → identical content from cache, caption "offline-first by design".
- 2:35–2:50 Floating-VM simulation: wipe VM-local state / fresh session → pins, layout, theme, persona all intact. Caption: "the VM changes; the user's desktop doesn't."
- 2:50–3:00 Performance table card + repo URL.

---

## 9. Updated Risk Register

| Risk | Status | Action |
|------|--------|--------|
| Fresh-VM .deb proof (D2) | **OPEN, disqualification-class** | Gate G1 Day 3 morning; verify snapshot restore actually reverts (check a sentinel file), then INSTALL.md verbatim |
| Visual confirm pending (D3) | OPEN | 15 min today before anything else |
| RDP behavior unknown (D7) | OPEN | Day 6, before polish so polish targets reality |
| Theme debt (D1) | OPEN | Day 2 = today; hard gate via grep |
| Carousel/animations blow CPU over RDP | NEW | every animation lands with a pidstat re-check; drop > polish |
| Usability test logistics (5 people) | NEW | recruit by Day 10; remote screen-share acceptable; log times |
| Scope creep from surplus time | NEW | nothing ships unless traceable to checklist / bonus list / reference design (Section 1 anti-goals) |
| Mock CMS endpoint in demo | NEW | default settings.json points at committed file:// feed so judges get content with zero setup; http server optional |

---

## 10. Operating Cadence (unchanged from v1 but tightened)

Session start: read this file's Section 2 row for today → Claude Code plans before coding → implement → evidence (logs/pidstat/xprop/screenshot) → commit `phase: what` → PROGRESS.md. Timebox polish items to their estimate; ship-or-cut at timeout. Every day ends with the .deb rebuilt and installed in the VM — the package is always the thing being developed, never an afterthought.

*v2 in one line: the checklist is already in reach — spend every surplus hour on visual parity with the reference, crushing benchmark presentation, and evidence that does the judges' work for them.*