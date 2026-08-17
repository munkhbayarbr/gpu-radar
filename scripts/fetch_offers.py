#!/usr/bin/env python3
"""Fetch live rental offers from the Vast.ai public marketplace API.

Writes data/offers.json (current snapshot, compact) and updates
data/history.json (per-day, per-GPU price aggregates for charts).
No API key required — the bundles search endpoint is public.
"""
import json
import os
import statistics
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

API = "https://console.vast.ai/api/v0/search/asks/"
QUERY = {
    "rentable": {"eq": True},
    "verified": {"eq": True},
    "external": {"eq": False},
    "rented": {"eq": False},
    "type": "on-demand",
    "order": [["dph_total", "asc"]],
    "allocated_storage": 5.0,
    "limit": 3000,
}

KEEP = [
    "id", "gpu_name", "num_gpus", "dph_total", "gpu_ram", "dlperf",
    "dlperf_per_dphtotal", "reliability2", "geolocation", "cuda_max_good",
    "inet_down", "inet_up", "disk_space", "static_ip", "min_bid",
    "cpu_cores_effective", "cpu_ram", "hosting_type",
]
ROUND = {
    "dph_total": 4, "dlperf": 1, "dlperf_per_dphtotal": 1, "reliability2": 4,
    "cuda_max_good": 1, "inet_down": 0, "inet_up": 0, "disk_space": 0,
    "min_bid": 4, "cpu_cores_effective": 0, "cpu_ram": 0,
}
HISTORY_MAX_DAYS = 730


def fetch():
    body = json.dumps({"select_cols": KEEP, "q": QUERY}).encode()
    headers = {"User-Agent": "gpu-radar/1.0",
               "Content-Type": "application/json"}
    # Unauthenticated requests are capped at 64 results; a key lifts the cap.
    key = os.environ.get("VAST_API_KEY", "").strip()
    if key:
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(API, data=body, method="PUT",
                                 headers=headers)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["offers"]


def compact(o):
    out = {}
    for k in KEEP:
        v = o.get(k)
        if isinstance(v, float) and k in ROUND:
            v = round(v, ROUND[k]) if ROUND[k] else int(round(v))
        out[k] = v
    return out


def update_history(offers, today):
    path = DATA / "history.json"
    history = json.loads(path.read_text()) if path.exists() else {}
    per_gpu = {}
    for o in offers:
        if not o["num_gpus"] or not o["dph_total"]:
            continue
        per_gpu.setdefault(o["gpu_name"], []).append(
            o["dph_total"] / o["num_gpus"])
    for gpu, prices in per_gpu.items():
        entries = [e for e in history.get(gpu, []) if e["d"] != today]
        entries.append({
            "d": today,
            "min": round(min(prices), 4),
            "med": round(statistics.median(prices), 4),
            "n": len(prices),
        })
        history[gpu] = sorted(entries, key=lambda e: e["d"])[-HISTORY_MAX_DAYS:]
    path.write_text(json.dumps(history, separators=(",", ":")))


def main():
    DATA.mkdir(exist_ok=True)
    offers = [compact(o) for o in fetch()]
    now = datetime.now(timezone.utc)
    snapshot = {"updated": now.isoformat(timespec="seconds"), "offers": offers}
    (DATA / "offers.json").write_text(
        json.dumps(snapshot, separators=(",", ":")))
    update_history(offers, now.strftime("%Y-%m-%d"))
    print(f"fetched {len(offers)} offers")


if __name__ == "__main__":
    main()
