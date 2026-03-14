# Deployment (make it live from GitHub)

## Option A — Streamlit Community Cloud (fastest)
1) Ensure these files are in the repo:
   - `requirements.txt` (this repo uses `-e .[dashboard]`)
   - App entrypoint: `src/stock_scout/dashboard/streamlit_app.py`
2) Go to Streamlit Community Cloud → **New app**.
3) Select:
   - Repo: `vanshchwdhary/AlphaFinder`
   - Branch: `main`
   - Main file path: `src/stock_scout/dashboard/streamlit_app.py`
4) Deploy.

Notes:
- First run: if the DB is empty, the app shows a **Bootstrap** button to fetch data and generate signals.
- For larger universes, move to a hosted Postgres DB and run the pipeline on a schedule (Option B).

### Custom domain with Streamlit Community Cloud
Streamlit Community Cloud apps cannot be directly hosted on your own domain (no native `CNAME` custom domain).

You have two practical choices:
1) **Redirect** your domain → Streamlit app URL (easy; browser URL changes to `.streamlit.app`)
2) **Re-deploy** the app on a host that supports custom domains (Render/Fly/VPS + reverse proxy)

#### Redirect (recommended if you want to keep Streamlit hosting)
If your DNS provider does not support HTTP forwarding, use Cloudflare (free) for DNS + redirects:
- Move DNS to Cloudflare (change nameservers at your registrar).
- Add a redirect rule:
  - Source: `farmfixer.xyz/*`
  - Destination: `https://YOUR_APP.streamlit.app/$1`
  - Status: `301`
- Add another rule for `www.farmfixer.xyz/*` (or redirect `www` → apex first).

## Option B — “Production-ish” (Postgres + scheduled pipeline)
Recommended shape:
- **Dashboard**: a web service (Render/Fly/AWS) running Streamlit.
- **Data refresh**: a scheduled job (GitHub Actions cron, or Render cron) running:
  - `stock-scout ingest-prices`
  - `stock-scout ingest-fundamentals`
  - `stock-scout generate-signals`

Steps:
1) Create a managed Postgres DB (Neon/Supabase/Render Postgres).
2) Set `STOCK_SCOUT_DATABASE_URL` to your Postgres connection string.
3) Deploy the Streamlit app and configure the same env var.
4) Add a scheduled workflow that runs the pipeline daily.
