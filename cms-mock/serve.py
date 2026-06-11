#!/usr/bin/env python3
"""Mock CMS server for jiopc-home development and the offline demo.

Serves this directory (so feed.json is reachable) over HTTP. The shell's CMS
endpoint defaults to the bundled feed; point it at this server to demo live
refresh, then stop the server to demo offline degradation.

Usage: python3 cms-mock/serve.py [port]   (default 8765)
       then set settings.json cms_endpoint to http://127.0.0.1:8765/feed.json
"""
from __future__ import annotations

import http.server
import os
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765


def main() -> None:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    handler = http.server.SimpleHTTPRequestHandler
    with http.server.ThreadingHTTPServer(("127.0.0.1", PORT), handler) as httpd:
        print(f"mock CMS on http://127.0.0.1:{PORT}/feed.json", flush=True)
        httpd.serve_forever()


if __name__ == "__main__":
    main()
