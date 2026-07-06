# CMS content schema

The widget engine's CMS-fed widgets (the carousel and quick-launch tiles;
news is CMS-fed too when enabled) consume one JSON document with three
sections. This is the schema JioPC's real CMS must produce; `feed.json` in
this folder is a mock instance of it with 6 entries per section, and
`serve.py` serves it over HTTP for testing live fetch/refresh.

## Top-level shape

```json
{
  "version": 1,
  "fetched_hint_minutes": 240,
  "carousel": [ ... ],
  "news": [ ... ],
  "tiles": [ ... ]
}
```

| Field | Type | Required | Meaning |
|---|---|---|---|
| `version` | int | yes | Schema version. The client does not currently branch on it, but a future breaking change to any section's item shape should bump it. |
| `fetched_hint_minutes` | int | yes | Advisory only — how fresh the producer intends this feed to be. The client does not currently read it (see Known limitations in `design.md`); refresh cadence is controlled client-side by `cms_refresh_minutes` in `settings.json`. |
| `carousel` | array | yes (may be empty) | Hero/featured carousel items. |
| `news` | array | yes (may be empty) | Headline items. |
| `tiles` | array | yes (may be empty) | Quick-launch tile items. |

A feed missing any of the three section keys is rejected (`_valid()` in
`src/widgets/cms.py`) and treated as a failed fetch — the widget keeps
serving whatever it had cached rather than accept a malformed document.
Empty arrays are valid and simply render an empty section, not an error.

## `carousel[]` — hero/featured items

```json
{
  "id": "c1",
  "title": "Got a doubt? We've got you.",
  "subtitle": "CBSE / JEE / NEET / UPSC - Khan Academy, Testbook and more on your TV",
  "image": "edu.png",
  "image_url": "https://images.unsplash.com/photo-1513542789411-b6a5d4f31634?w=800&q=75",
  "cta_label": "Start learning",
  "cta_action": "url:https://www.khanacademy.org"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | Stable identifier; used as the widget's re-render key on refresh. |
| `title` | string | yes | Headline text, rendered large. |
| `subtitle` | string | yes | One or two lines of supporting text. |
| `image` | string | no | Filename of a bundled local asset under `src/widgets/assets/`. Checked **first** — if present and the file exists, it is decoded (size-capped at 1100px, cached in-process) with no network access at all. This is what the shipped `default_feed.json` uses, so the default desktop never depends on the network for its hero images. |
| `image_url` | string | no | Absolute `http(s)` URL, used **only if `image` is absent or the named asset is missing**. Fetched asynchronously via `widgets/image_cache.py`; while pending or on failure the card simply has no image yet (text/CTA still render over the themed scrim) rather than a broken-image icon. |
| `cta_label` | string | yes | Button text. |
| `cta_action` | string | yes | An action string in the `app:` / `url:` namespace — see Action strings below. |

The mock feed in this folder (`feed.json`) deliberately omits `image` and
leaves `image_url` empty for every entry, to exercise the no-image fallback
path distinctly from the bundled default feed (`src/widgets/default_feed.json`),
which sets `image` on every entry to demonstrate the local-asset path.

## `news[]` — headline items

```json
{
  "id": "n1",
  "headline": "ISRO launches new satellite successfully",
  "source": "PTI",
  "ts": 1781100000,
  "url": "https://www.isro.gov.in"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | Stable identifier. |
| `headline` | string | yes | Headline text. |
| `source` | string | yes | Publisher name, shown as a small label. |
| `ts` | int | yes | Unix epoch seconds. The widget derives relative time ("2h ago") from this at render time; it does not re-derive it from `fetched_hint_minutes` or wall-clock fetch time. |
| `url` | string | yes | Opened on click via the same `url:` action string described below (the widget wraps it as `run_action(f"url:{url}")`), so it goes through the identical action-execution path as carousel/tile actions. |

## `tiles[]` — quick-launch items

```json
{
  "id": "t1",
  "label": "Study for exams",
  "icon": "applications-education",
  "action": "url:https://www.khanacademy.org"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | Stable identifier. |
| `label` | string | yes | Tile caption, shown under the icon. |
| `icon` | string | no | A freedesktop icon-theme name (`QIcon.fromTheme`). Absent/unresolvable → the tile falls back to the label's first letter on a coloured badge, never a blank icon. |
| `action` | string | yes | An action string — see below. |

Only the first `_COLS * rows-that-fit` tiles are ever shown at once — the
widget adapts to how many rows its grid cell actually has room for at the
current screen resolution (see `design.md`, Component C), so a producer
supplying more than 6 tiles is not wrong, but only the first 6 in feed order
will ever be reachable by this client.

## Action strings

Both `carousel[].cta_action` and `tiles[].action` share one namespaced
action format, parsed by `widgets/engine.py:execute_action`:

| Prefix | Example | Behavior |
|---|---|---|
| `app:` | `app:org.gnome.Calculator.desktop` | Resolves the `.desktop` id (the `.desktop` suffix is stripped if present) via the same app index the application menu uses, and launches it exactly like a dock/menu click. Unknown id → silently a no-op, no crash. |
| `url:` | `url:https://www.khanacademy.org` | Opens the URL via `QDesktopServices.openUrl`, i.e. the user's configured default browser. |

Any other/unrecognised prefix (or an empty payload) is silently a no-op
rather than raising, so a malformed or forward-looking action from a newer
CMS never crashes the shell.

## Fetch, cache, and refresh behavior (implemented in `widgets/cms.py`)

1. On construction, `CmsService` serves the best content available with
   **no network wait**: last-good cache (`~/.cache/jiopc/home/feed.json`) if
   present and schema-valid, else the bundled `default_feed.json` shipped in
   the package, else an empty feed. A widget is never blank-and-stuck and
   startup is never blocked on the network.
2. `refresh()` fetches the configured endpoint (`cms_endpoint` in
   `settings.json`; defaults to the bundled feed file so refresh works with
   zero setup) on a background `QThread` with a 5 s timeout, so a slow or
   dead endpoint never blocks the UI thread.
3. On success: the cache file is atomically replaced (write-to-temp +
   rename, via `core/store.py`) and `content_updated` is emitted so every
   subscribed widget re-renders.
4. On failure (timeout, connection error, HTTP error, invalid JSON, or a
   feed missing a required section): the failure is logged and the
   previous content keeps serving unchanged — this is the offline-graceful-
   degradation path, verified in `benchmarks/results/2026-07-06.md` and
   `screenshots/offline_*.png` by pointing `cms_endpoint` at an unreachable
   address and confirming no crash and no blank widget.
5. Refresh cadence: `refresh()` is always called once at session start
   (`widgets/desktop.py:start()`) — the spec's default. A repeat cadence is
   configurable via `cms_refresh_minutes` in `settings.json` (int, minutes;
   `0` or absent = session-start only, matching the default). When set, the
   CMS service also refreshes on that timer for the rest of the session.

## Testing with the mock server

```bash
python3 cms-mock/serve.py            # serves feed.json on :8765
```

Then set `"cms_endpoint": "http://127.0.0.1:8765/feed.json"` in
`~/.config/jiopc/home/settings.json` and restart the shell to demo a live
fetch; stop the server (or point the endpoint at an unreachable host) to
demo offline degradation.
