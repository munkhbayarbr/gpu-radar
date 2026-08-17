# GPU Radar — launch checklist (your ~30 minutes)

The site is live and self-updating: **https://munkhbayarbr.github.io/gpu-radar/**
Everything below grows traffic/revenue — none of it is needed to keep the site running.

## Revenue (do first)

1. **Confirm your Vast referral link** (5 min). Log in at cloud.vast.ai →
   Account/Settings → *Referral Link* → copy it. I used
   `https://cloud.vast.ai/?ref_id=471952` (your user id). If your real link
   differs, change `REF_ID` in `scripts/build_pages.py` and `RENT_URL` in
   `site/app.js`, then push.
   - Note: Vast docs recommend a **dedicated referral account** — accounts
     that have rented can only cash out once referral earnings exceed
     lifetime instance spend. Credits still offset your own GPU rentals
     either way (you spend real money on Vast, so credits ≈ cash for you).
2. **RunPod affiliate** (10 min) — runpod.io → referral program (3–5%,
   upgrades to 10% cash). Second revenue stream; we can add a RunPod
   comparison section next iteration.

## Distribution / SEO

3. **Google Search Console** (10 min) — add property
   `https://munkhbayarbr.github.io/gpu-radar/`, submit `sitemap.xml`.
   Bing Webmaster Tools too (imports from GSC in one click).
4. **Custom domain later** (~$10/yr, e.g. gpuradar.io or similar) — better
   ranking + enables AdSense as a second monetization layer. Set it in repo
   Settings → Pages, update `SITE_ORIGIN`/`SITE_BASE` env in the workflow.
5. **Post it where renters are** (when you have 3+ days of price history):
   r/MachineLearning, r/LocalLLaMA, r/StableDiffusion, Hacker News
   (Show HN), X. Angle: "I rent GPUs weekly for my avatar startup, so I
   built a live deal tracker." Honest founder-story posts do well.

## Product next steps (I can do any of these on request)

- Price-drop alerts (email or Telegram) — the #1 reason people return
- RunPod + Lambda price columns (true cross-provider comparison)
- Interruptible/bid prices (often 2–3× cheaper — great content hook)
- Weekly "GPU market report" auto-generated page (SEO compounding)
