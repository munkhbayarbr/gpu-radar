#!/usr/bin/env python3
"""Submit all site URLs to IndexNow (Bing, DuckDuckGo, Yandex, Naver...).

Runs after deploy. On scheduled runs, only pings during the 00:xx UTC run
to avoid daily spam; pushes and manual dispatches always ping.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

KEY = "196ae58d54584ad1a57740e0086901ac"
HOST = "munkhbayarbr.github.io"
URLS_FILE = Path(__file__).resolve().parent.parent / "dist" / "urls.txt"

event = os.environ.get("GITHUB_EVENT_NAME", "")
if event == "schedule" and datetime.now(timezone.utc).hour != 0:
    print("scheduled run outside 00:xx UTC — skipping IndexNow ping")
    sys.exit(0)

urls = [u for u in URLS_FILE.read_text().splitlines() if u.strip()]
body = json.dumps({
    "host": HOST,
    "key": KEY,
    "keyLocation": f"https://{HOST}/gpu-radar/{KEY}.txt",
    "urlList": urls,
}).encode()
req = urllib.request.Request(
    "https://api.indexnow.org/indexnow", data=body, method="POST",
    headers={"Content-Type": "application/json; charset=utf-8"})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"IndexNow: HTTP {r.status} for {len(urls)} urls")
except urllib.error.HTTPError as e:
    print(f"IndexNow: HTTP {e.code} — {e.read()[:200]}")
