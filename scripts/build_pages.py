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
        out[name] = {
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
        rows.append(
            f"<tr><td class='gpu'>{esc(o['gpu_name'])}"
            f"<span class='xn'>×{o['num_gpus']}</span></td>"
            f"<td class='num price'>${unit_price(o):.3f}</td>"
            f"<td class='num'>${o['dph_total']:.3f}</td>"
            f"<td class='num'>{(o['gpu_ram'] or 0) // 1024} GB</td>"
            f"<td class='num'>{o.get('dlperf') or 0:.0f}</td>"
            f"<td class='num'>{rel}</td>"
            f"<td>{loc}</td>"
            f"<td><a class='rent' href='{RENT_URL}' target='_blank' "
            f"rel='sponsored noopener'>Rent →</a></td></tr>")
    return "\n".join(rows)


TABLE_HEAD = ("<thead><tr><th>GPU</th><th>$/hr per GPU</th><th>$/hr total</th>"
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
<link rel="stylesheet" href="{BASE}/style.css">
{extra_head}
</head>
<body>
<header class="top">
  <a class="brand" href="{BASE}/">📡 {SITE_NAME}</a>
  <nav><a href="{BASE}/#deals">Deals</a> <a href="{BASE}/#fit">Fit calculator</a> <a href="{BASE}/#gpus">GPUs</a></nav>
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


def build_index(stats, updated, offers):
    cards = []
    featured = [g for g in FEATURED if g in stats]
    for name in featured:
        s = stats[name]
        cards.append(f"""<a class="card" href="{BASE}/gpu/{s['slug']}/">
  <h3>{esc(name)}</h3>
  <p class="big">${s['min']:.3f}<span>/hr</span></p>
  <p class="sub">{s['vram']} GB · {s['count']} offers · median ${s['med']:.3f}</p>
</a>""")
    cheapest = sorted(offers, key=unit_price)
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


def build_gpu_page(s, stats, updated):
    name = s["name"]
    faq = [
        (f"How much does it cost to rent a {name} in the cloud?",
         f"Right now the cheapest verified {name} on the Vast.ai marketplace "
         f"is ${s['min']:.3f}/hr per GPU; the median across {s['count']} "
         f"offers is ${s['med']:.3f}/hr. Prices change hourly."),
        (f"How much VRAM does a {name} have?",
         f"{name} offers on this page have up to {s['vram']} GB of VRAM."),
        ("Are these prices on-demand or interruptible?",
         "All prices shown are verified on-demand (uninterruptible) offers. "
         "Interruptible/bid instances are usually cheaper still."),
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
  across {s['count']} on-demand offers · up to {s['vram']} GB VRAM.
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

    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "gpu").mkdir(parents=True)
    (DIST / "data").mkdir()

    (DIST / "index.html").write_text(build_index(stats, updated, offers))
    urls = [f"{ORIGIN}{BASE}/"]
    for s in stats.values():
        if s["count"] < MIN_OFFERS_FOR_PAGE:
            continue
        d = DIST / "gpu" / s["slug"]
        d.mkdir()
        (d / "index.html").write_text(build_gpu_page(s, stats, updated))
        urls.append(f"{ORIGIN}{BASE}/gpu/{s['slug']}/")

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
