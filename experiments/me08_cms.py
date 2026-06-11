"""ME-08: offline-first CMS pipeline.

PASS:
- server up   -> fresh content fetched + cached;
- server down -> cached content still served, clean warning, no crash;
- no cache, no server -> valid empty/bundled state, never a traceback.

Run in VM: DISPLAY=:0 python3 experiments/me08_cms.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from widgets import cms  # noqa: E402
from core import store  # noqa: E402

PORT = 8799
FEED = {"version": 1, "fetched_hint_minutes": 60,
        "carousel": [{"id": f"c{i}"} for i in range(6)],
        "news": [{"id": f"n{i}"} for i in range(6)],
        "tiles": [{"id": f"t{i}"} for i in range(6)]}


def main() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="me08-"))
    (tmp / "feed.json").write_text(json.dumps(FEED))
    cache = tmp / "cache_feed.json"
    endpoint = f"http://127.0.0.1:{PORT}/feed.json"

    os.chdir(tmp)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), SimpleHTTPRequestHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    # Scenario A: server up -> fetch + cache.
    data = cms.fetch(endpoint)
    store.write_json(cache, data)
    a = cms.load_cache(cache)
    print(f"A online: carousel={len(data['carousel'])} cached={a is not None}",
          flush=True)
    ok_a = len(data["carousel"]) == 6 and a is not None

    # Scenario B: server down -> fetch fails, cache still serves.
    server.shutdown()
    try:
        cms.fetch(endpoint, timeout=2)
        fetched = True
    except Exception as exc:
        fetched = False
        print(f"B offline: fetch failed cleanly ({type(exc).__name__})", flush=True)
    served = cms.load_cache(cache)
    ok_b = (not fetched) and served is not None and len(served["carousel"]) == 6
    print(f"B offline: served-from-cache={served is not None}", flush=True)

    # Scenario C: no cache, no server -> valid state, no traceback.
    cache.unlink(missing_ok=True)
    content = cms.initial_content(cache)
    ok_c = cms._valid(content)  # noqa: SLF001
    print(f"C cold: initial_content valid={ok_c} "
          f"carousel={len(content.get('carousel', []))} (bundled fallback)",
          flush=True)

    verdict = "PASS" if (ok_a and ok_b and ok_c) else "FAIL"
    print(f"ME-08 {verdict}", flush=True)


if __name__ == "__main__":
    main()
