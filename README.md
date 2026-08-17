# 📡 GPU Radar

Live cloud GPU rental deal tracker for the Vast.ai marketplace.

**Live site:** https://munkhbayarbr.github.io/gpu-radar/

- Hourly snapshot of every verified on-demand offer (price, VRAM, DLPerf,
  reliability, location) via the public Vast.ai search API
- Programmatic SEO: one landing page per GPU model with live prices + FAQ
- "Will my model fit?" VRAM calculator that recommends the cheapest fitting GPU
- Daily price history per GPU (accumulates in `data/history.json`)
- Zero infra: GitHub Actions cron → static build → GitHub Pages

## How it works

```
scripts/fetch_offers.py   # Vast.ai API -> data/offers.json + history.json
scripts/build_pages.py    # data -> dist/ (index, gpu/<slug>/, sitemap)
site/                     # css + client js (filters, calculator, sparkline)
.github/workflows/deploy.yml  # hourly cron: fetch -> commit -> build -> Pages
```

Local build:

```sh
VAST_API_KEY=$(cat ~/.config/vastai/vast_api_key) python3 scripts/fetch_offers.py
SITE_BASE="" python3 scripts/build_pages.py
python3 -m http.server -d dist 8080
```

## Monetization

Outbound rent links carry a Vast.ai referral id (3% of referred users'
lifetime spend, disclosed in the footer).
