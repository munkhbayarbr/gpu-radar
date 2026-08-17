#!/usr/bin/env python3
"""Build the static site into dist/ from data/offers.json + data/history.json.

Bakes real offer data into the HTML so pages are fully crawlable; app.js
re-renders client-side for filtering. Per-GPU landing pages are generated
for every model with enough offers (programmatic SEO surface).
"""
import html
import json
import os
import shutil
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SITE = ROOT / "site"
DIST = ROOT / "dist"

BASE = os.environ.get("SITE_BASE", "/gpu-radar")
ORIGIN = os.environ.get("SITE_ORIGIN", "https://munkhbayarbr.github.io")
REF_ID = "471952"
RENT_URL = f"https://cloud.vast.ai/?ref_id={REF_ID}"
SITE_NAME = "GPU Radar"
TAGLINE = "Live cloud GPU rental deals"
MIN_OFFERS_FOR_PAGE = 5
FEATURED = ["RTX 4090", "RTX 5090", "RTX 3090", "A100 SXM4", "H100 SXM",
            "RTX PRO 6000 WS", "RTX 5080", "L40S", "A100 PCIE", "H200"]
INDEXNOW_KEY = "196ae58d54584ad1a57740e0086901ac"
RUNPOD_URL = "https://www.runpod.io/"  # swap for affiliate link when approved
VAST_TO_RUNPOD = {
    "RTX 4090": "NVIDIA GeForce RTX 4090",
    "RTX 5090": "NVIDIA GeForce RTX 5090",
    "RTX 5080": "NVIDIA GeForce RTX 5080",
    "RTX 4080": "NVIDIA GeForce RTX 4080",
    "RTX 4080S": "NVIDIA GeForce RTX 4080 SUPER",
    "RTX 4070 Ti": "NVIDIA GeForce RTX 4070 Ti",
    "RTX 3090": "NVIDIA GeForce RTX 3090",
    "RTX 3090 Ti": "NVIDIA GeForce RTX 3090 Ti",
    "RTX 3080": "NVIDIA GeForce RTX 3080",
    "RTX 3080 Ti": "NVIDIA GeForce RTX 3080 Ti",
    "RTX 3070": "NVIDIA GeForce RTX 3070",
    "A100 SXM4": "NVIDIA A100-SXM4-80GB",
    "A100 PCIE": "NVIDIA A100 80GB PCIe",
    "H100 SXM": "NVIDIA H100 80GB HBM3",
    "H100 PCIE": "NVIDIA H100 PCIe",
    "H100 NVL": "NVIDIA H100 NVL",
    "H200": "NVIDIA H200",
    "H200 NVL": "NVIDIA H200 NVL",
    "B200": "NVIDIA B200",
    "L4": "NVIDIA L4",
    "L40": "NVIDIA L40",
    "L40S": "NVIDIA L40S",
    "A40": "NVIDIA A40",
    "RTX A2000": "NVIDIA RTX A2000",
    "RTX A4000": "NVIDIA RTX A4000",
    "RTX A4500": "NVIDIA RTX A4500",
    "RTX A5000": "NVIDIA RTX A5000",
    "RTX A6000": "NVIDIA RTX A6000",
    "RTX 2000Ada": "NVIDIA RTX 2000 Ada Generation",
    "RTX 4000Ada": "NVIDIA RTX 4000 Ada Generation",
    "RTX 5000Ada": "NVIDIA RTX 5000 Ada Generation",
    "RTX 6000Ada": "NVIDIA RTX 6000 Ada Generation",
    "RTX PRO 6000 WS": "NVIDIA RTX PRO 6000 Blackwell Workstation Edition",
    "RTX PRO 6000 S": "NVIDIA RTX PRO 6000 Blackwell Server Edition",
    "RTX PRO 5000": "NVIDIA RTX PRO 5000 Blackwell",
    "RTX PRO 4500": "NVIDIA RTX PRO 4500 Blackwell",
    "RTX PRO 4000": "NVIDIA RTX PRO 4000 Blackwell",
    "Tesla V100": "Tesla V100-PCIE-16GB",
}


def slugify(name):
    return "".join(c if c.isalnum() or c == "-" else "-"
                   for c in name.lower().replace(" ", "-")).strip("-")


def esc(s):
    return html.escape(str(s))


def unit_price(o):
    return o["dph_total"] / o["num_gpus"] if o["num_gpus"] else o["dph_total"]


def gpu_stats(offers):
    stats = {}
    for o in offers:
        stats.setdefault(o["gpu_name"], []).append(o)
    out = {}
    for name, offs in stats.items():
        prices = sorted(unit_price(o) for o in offs)
        bids = sorted(o["min_bid"] / o["num_gpus"] for o in offs
                      if o.get("min_bid") and o["num_gpus"])
        out[name] = {
            # p10 of current min-bids: robust "spot from" (raw min is often
            # a stale outlier like $0.006/hr that reads as fake)
            "bid": bids[len(bids) // 10] if bids else None,
            "name": name,
            "slug": slugify(name),
            "count": len(offs),
            "min": prices[0],
            "med": statistics.median(prices),
            "vram": max(o["gpu_ram"] or 0 for o in offs) // 1024,
            "dlperf": statistics.median(
                [o["dlperf"] for o in offs if o.get("dlperf")] or [0]),
            "offers": sorted(offs, key=unit_price),
        }
    return out


def offer_rows(offers, limit=None):
    rows = []
    for o in offers[:limit]:
        loc = esc(o.get("geolocation") or "—")
        rel = f"{(o.get('reliability2') or 0) * 100:.1f}%"
        bid = (o.get("min_bid") / o["num_gpus"]
               if o.get("min_bid") and o["num_gpus"] else None)
        rows.append(
            f"<tr><td class='gpu'>{esc(o['gpu_name'])}"
            f"<span class='xn'>×{o['num_gpus']}</span></td>"
            f"<td class='num price'>${unit_price(o):.3f}</td>"
            f"<td class='num dim'>{f'${bid:.3f}' if bid else '—'}</td>"
            f"<td class='num'>${o['dph_total']:.3f}</td>"
            f"<td class='num'>{(o['gpu_ram'] or 0) // 1024} GB</td>"
            f"<td class='num'>{o.get('dlperf') or 0:.0f}</td>"
            f"<td class='num'>{rel}</td>"
            f"<td>{loc}</td>"
            f"<td><a class='rent' href='{RENT_URL}' target='_blank' "
            f"rel='sponsored noopener'>Rent →</a></td></tr>")
    return "\n".join(rows)


TABLE_HEAD = ("<thead><tr><th>GPU</th><th>$/hr per GPU</th>"
              "<th>Spot $/GPU</th><th>$/hr total</th>"
              "<th>VRAM</th><th>DLPerf</th><th>Reliability</th>"
              "<th>Location</th><th></th></tr></thead>")


def page(title, desc, canonical, body, extra_head=""):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{canonical}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="website">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📡</text></svg>">
<link rel="alternate" type="application/rss+xml" title="{SITE_NAME} daily GPU deals" href="{BASE}/deals.xml">
<link rel="stylesheet" href="{BASE}/style.css">
{extra_head}
</head>
<body>
<header class="top">
  <a class="brand" href="{BASE}/">📡 {SITE_NAME}</a>
  <nav><a href="{BASE}/#deals">Deals</a> <a href="{BASE}/#fit">Fit calculator</a> <a href="{BASE}/#gpus">GPUs</a> <a href="{BASE}/deals.xml" title="Daily deals RSS feed">RSS</a></nav>
</header>
{body}
<footer>
  <p>{SITE_NAME} tracks live on-demand offers on the Vast.ai marketplace.
  Prices refresh hourly. Links to Vast.ai are referral links — they cost you
  nothing and support this site.</p>
  <p>Not affiliated with Vast.ai. Data provided as-is; verify before renting.</p>
</footer>
<script src="{BASE}/app.js" defer></script>
</body>
</html>"""


def build_feed(stats, history, updated_iso):
    """RSS deals feed: one item per featured GPU per day (guid = slug+date),
    flagged as a DEAL when today's min undercuts the 7-day baseline."""
    from datetime import datetime
    dt = datetime.fromisoformat(updated_iso)
    day = dt.strftime("%Y-%m-%d")
    pub = dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
    items = []
    for name in FEATURED:
        s = stats.get(name)
        if not s:
            continue
        entries = history.get(name, [])
        prior = [e["min"] for e in entries if e["d"] != day][-7:]
        baseline = statistics.median(prior) if len(prior) >= 3 else None
        deal = baseline and s["min"] <= 0.92 * baseline
        pct = f" — {round((1 - s['min'] / baseline) * 100)}% below the 7-day typical low" \
            if deal else ""
        spot = f", spot ~${s['bid']:.3f}/hr" if s.get("bid") else ""
        title = (f"{'DEAL: ' if deal else ''}{name} from ${s['min']:.3f}/hr"
                 f"{pct}")
        desc = (f"{name}: cheapest verified on-demand offer ${s['min']:.3f}/hr"
                f" per GPU (median ${s['med']:.3f}/hr{spot}, "
                f"{s['count']} offers, up to {s['vram']} GB VRAM).")
        url = f"{ORIGIN}{BASE}/gpu/{s['slug']}/"
        items.append(
            f"<item><title>{esc(title)}</title><link>{url}</link>"
            f"<guid isPermaLink=\"false\">{s['slug']}-{day}</guid>"
            f"<pubDate>{pub}</pubDate>"
            f"<description>{esc(desc)}</description></item>")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0"><channel>'
        f"<title>{SITE_NAME} — daily GPU deals</title>"
        f"<link>{ORIGIN}{BASE}/</link>"
        "<description>Cheapest cloud GPU rentals on the Vast.ai marketplace, "
        "with deal alerts when prices drop below their 7-day typical low."
        "</description>"
        f"<lastBuildDate>{pub}</lastBuildDate>"
        + "".join(items) + "</channel></rss>")


def runpod_compare_rows(stats, runpod):
    rows = []
    for name in FEATURED:
        s = stats.get(name)
        rp = runpod.get(VAST_TO_RUNPOD.get(name, ""))
        if not s or not rp:
            continue
        bid = "~${:.3f}".format(s["bid"]) if s.get("bid") else "—"
        comm = "${:.2f}".format(rp["community"]) if rp["community"] else "—"
        sec = "${:.2f}".format(rp["secure"]) if rp["secure"] else "—"
        rows.append(
            f"<tr><td class='gpu'><a href='{BASE}/gpu/{s['slug']}/'>"
            f"{esc(name)}</a></td>"
            f"<td class='num price'>${s['min']:.3f}</td>"
            f"<td class='num dim'>{bid}</td>"
            f"<td class='num'>{comm}</td>"
            f"<td class='num'>{sec}</td></tr>")
    return "\n".join(rows)


def build_index(stats, updated, offers, runpod):
    cards = []
    featured = [g for g in FEATURED if g in stats]
    for name in featured:
        s = stats[name]
        spot = f" · spot ~${s['bid']:.3f}" if s.get("bid") else ""
        cards.append(f"""<a class="card" href="{BASE}/gpu/{s['slug']}/">
  <h3>{esc(name)}</h3>
  <p class="big">${s['min']:.3f}<span>/hr</span></p>
  <p class="sub">{s['vram']} GB · {s['count']} offers{spot}</p>
</a>""")
    cheapest = sorted(offers, key=unit_price)
    cmp_rows = runpod_compare_rows(stats, runpod)
    compare_section = f"""<section id="compare">
  <h2>Vast.ai vs RunPod — price per GPU/hr</h2>
  <p class="note">Vast prices are live marketplace lows (on-demand and
  interruptible spot); <a href="{RUNPOD_URL}" target="_blank"
  rel="noopener">RunPod</a> prices are current list rates
  (community / secure cloud).</p>
  <div class="tablewrap"><table>
  <thead><tr><th>GPU</th><th>Vast on-demand</th><th>Vast spot</th>
  <th>RunPod community</th><th>RunPod secure</th></tr></thead>
  <tbody>{cmp_rows}</tbody></table></div>
</section>""" if cmp_rows else ""
    body = f"""
<main>
<section class="hero">
  <h1>Cheapest cloud GPUs, right now</h1>
  <p class="lede">Live prices from the Vast.ai GPU marketplace — {len(offers)}
  verified on-demand offers across {len(stats)} GPU models.
  Updated <span id="updated">{esc(updated)}</span>.</p>
  <a class="cta" href="{RENT_URL}" target="_blank" rel="sponsored noopener">Rent a GPU on Vast.ai →</a>
</section>
<section id="gpus">
  <h2>Popular GPUs — lowest price per GPU/hr</h2>
  <div class="cards">{''.join(cards)}</div>
</section>
{compare_section}
<section id="fit">
  <h2>Will my model fit? 🧮</h2>
  <p>Pick a model size and quantization — we estimate VRAM and find the cheapest GPU that fits.</p>
  <div class="fitbox">
    <label>Model size
      <select id="fit-params">
        <option value="3">3B</option><option value="7">7B</option>
        <option value="8" selected>8B</option><option value="13">13B</option>
        <option value="32">32B</option><option value="70">70B</option>
        <option value="123">123B</option>
      </select></label>
    <label>Quantization
      <select id="fit-quant">
        <option value="2">FP16</option><option value="1">INT8</option>
        <option value="0.6" selected>4-bit</option>
      </select></label>
    <div id="fit-result" class="fitresult"></div>
  </div>
</section>
<section id="deals">
  <h2>All offers</h2>
  <div class="filters">
    <select id="f-gpu"><option value="">All GPUs</option></select>
    <select id="f-vram"><option value="0">Any VRAM</option>
      <option value="12">≥12 GB</option><option value="16">≥16 GB</option>
      <option value="24">≥24 GB</option><option value="48">≥48 GB</option>
      <option value="80">≥80 GB</option><option value="96">≥96 GB</option></select>
    <input id="f-price" type="number" step="0.05" min="0" placeholder="Max $/hr per GPU">
    <select id="f-ngpu"><option value="0">Any count</option>
      <option value="1">1× GPU</option><option value="2">2×+</option>
      <option value="4">4×+</option><option value="8">8×</option></select>
  </div>
  <div class="tablewrap"><table id="offers">{TABLE_HEAD}
  <tbody>{offer_rows(cheapest, 50)}</tbody></table></div>
  <p id="offers-note" class="note">Showing 50 cheapest offers — use the filters to search all {len(offers)}.</p>
</section>
</main>"""
    title = f"{SITE_NAME} — {TAGLINE} | RTX 4090, 5090, A100, H100 prices"
    desc = (f"Live cloud GPU rental prices from the Vast.ai marketplace. "
            f"RTX 4090 from ${stats['RTX 4090']['min']:.2f}/hr, "
            f"RTX 5090 from ${stats['RTX 5090']['min']:.2f}/hr. "
            f"Updated hourly.") if "RTX 4090" in stats and "RTX 5090" in stats \
        else f"Live cloud GPU rental prices, updated hourly."
    return page(title, desc, f"{ORIGIN}{BASE}/", body)


def build_gpu_page(s, stats, updated, runpod):
    name = s["name"]
    rp = runpod.get(VAST_TO_RUNPOD.get(name, ""))
    spot_txt = (f" Interruptible (spot) instances start around "
                f"<strong>~${s['bid']:.3f}/hr</strong>." if s.get("bid") else "")
    rp_txt = ""
    if rp and (rp["community"] or rp["secure"]):
        parts = []
        if rp["community"]:
            parts.append(f"community ${rp['community']:.2f}/hr")
        if rp["secure"]:
            parts.append(f"secure ${rp['secure']:.2f}/hr")
        rp_txt = (f" For comparison, <a href='{RUNPOD_URL}' target='_blank' "
                  f"rel='noopener'>RunPod</a> lists the {esc(name)} at "
                  f"{' / '.join(parts)}.")
    faq = [
        (f"How much does it cost to rent a {name} in the cloud?",
         f"Right now the cheapest verified {name} on the Vast.ai marketplace "
         f"is ${s['min']:.3f}/hr per GPU; the median across {s['count']} "
         f"offers is ${s['med']:.3f}/hr. Prices change hourly."),
        (f"How much VRAM does a {name} have?",
         f"{name} offers on this page have up to {s['vram']} GB of VRAM."),
        ("Are these prices on-demand or interruptible?",
         "The main price is for verified on-demand (uninterruptible) offers; "
         "the Spot column shows the current minimum bid for the same machine "
         + (f"— {name} spot prices currently start around ~${s['bid']:.3f}/hr."
            if s.get("bid") else ".")),
    ]
    faq_ld = json.dumps({
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": q,
                        "acceptedAnswer": {"@type": "Answer", "text": a}}
                       for q, a in faq]})
    others = "".join(
        f"<a class='chip' href='{BASE}/gpu/{o['slug']}/'>{esc(o['name'])} "
        f"${o['min']:.2f}+</a>"
        for o in sorted(stats.values(), key=lambda x: -x["count"])[:14]
        if o["name"] != name)
    faq_html = "".join(
        f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>"
        for q, a in faq)
    body = f"""
<main>
<section class="hero">
  <h1>{esc(name)} cloud rental price</h1>
  <p class="lede">Cheapest verified {esc(name)} right now:
  <strong>${s['min']:.3f}/hr</strong> per GPU · median ${s['med']:.3f}/hr
  across {s['count']} on-demand offers · up to {s['vram']} GB VRAM.{spot_txt}{rp_txt}
  Updated <span id="updated">{esc(updated)}</span>.</p>
  <a class="cta" href="{RENT_URL}" target="_blank" rel="sponsored noopener">Rent a {esc(name)} on Vast.ai →</a>
</section>
<section>
  <h2>Live {esc(name)} offers</h2>
  <div class="tablewrap"><table>{TABLE_HEAD}
  <tbody>{offer_rows(s['offers'], 25)}</tbody></table></div>
</section>
<section id="history" data-gpu="{esc(name)}">
  <h2>Price history</h2>
  <div id="spark" class="spark"><p class="note">Collecting price history — chart appears after a few days of data.</p></div>
</section>
<section>
  <h2>FAQ</h2>
  {faq_html}
</section>
<section>
  <h2>Other GPUs</h2>
  <div class="chips">{others}</div>
</section>
</main>"""
    title = (f"{name} rental price — from ${s['min']:.3f}/hr | {SITE_NAME}")
    desc = (f"Rent a {name} in the cloud from ${s['min']:.3f}/hr. Live "
            f"comparison of {s['count']} verified Vast.ai offers, with VRAM, "
            f"performance and reliability. Updated hourly.")
    extra = f'<script type="application/ld+json">{faq_ld}</script>'
    return page(title, desc, f"{ORIGIN}{BASE}/gpu/{s['slug']}/", body, extra)


def main():
    snapshot = json.loads((DATA / "offers.json").read_text())
    offers = [o for o in snapshot["offers"] if o["dph_total"]]
    updated = snapshot["updated"].replace("T", " ").replace("+00:00", " UTC")
    stats = gpu_stats(offers)
    runpod = {}
    if (DATA / "runpod.json").exists():
        runpod = json.loads((DATA / "runpod.json").read_text())

    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "gpu").mkdir(parents=True)
    (DIST / "data").mkdir()

    (DIST / "index.html").write_text(
        build_index(stats, updated, offers, runpod))
    urls = [f"{ORIGIN}{BASE}/"]
    for s in stats.values():
        if s["count"] < MIN_OFFERS_FOR_PAGE:
            continue
        d = DIST / "gpu" / s["slug"]
        d.mkdir()
        (d / "index.html").write_text(
            build_gpu_page(s, stats, updated, runpod))
        urls.append(f"{ORIGIN}{BASE}/gpu/{s['slug']}/")

    (DIST / f"{INDEXNOW_KEY}.txt").write_text(INDEXNOW_KEY)
    (DIST / "urls.txt").write_text("\n".join(urls))

    history = {}
    if (DATA / "history.json").exists():
        history = json.loads((DATA / "history.json").read_text())
    (DIST / "deals.xml").write_text(
        build_feed(stats, history, snapshot["updated"]))

    (DIST / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(f"<url><loc>{u}</loc></url>" for u in urls)
        + "\n</urlset>")
    (DIST / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {ORIGIN}{BASE}/sitemap.xml\n")
    (DIST / ".nojekyll").write_text("")

    shutil.copy(SITE / "style.css", DIST / "style.css")
    shutil.copy(SITE / "app.js", DIST / "app.js")
    shutil.copy(DATA / "offers.json", DIST / "data" / "offers.json")
    if (DATA / "history.json").exists():
        shutil.copy(DATA / "history.json", DIST / "data" / "history.json")
    print(f"built {len(urls)} pages -> {DIST}")


if __name__ == "__main__":
    main()
