# traffic-magnet-finder

Traffic Magnet Finder is a Flask web app that fuses public Google Trends RSS, subreddit RSS, and curated tech/business RSS feeds to surface fast-rising topics for SEO planning or editorial calendars. It normalizes headlines, groups near-duplicates, scores momentum, and exports ranked CSV/JSON reports.

## Quickstart
1. **Install dependencies**
    ```bash
    python -m venv .venv && .venv\Scripts\activate  # Windows
    pip install -r requirements.txt
    ```
2. **Run the app**
    ```bash
    python app.py
    ```
3. Open http://127.0.0.1:5000 and start exploring trends.

## Form Fields
- **Keywords**: Optional comma list. Whole-word matches add +0.1 to frequency (capped at +0.3) before scoring.
- **Geo**: Two-letter country code for Google Trends daily RSS (default `US`).
- **Subreddits**: Comma-separated subreddit slugs (e.g., `Entrepreneur,Startups,SaaS`).
- **RSS Feeds**: Any comma or newline separated RSS URLs (defaults: TechCrunch, Hacker News, The Verge).
- **Lookback Days**: Recency window used for decay to zero; posts <=24h get full recency credit.
- **Limit per Source**: Max items pulled from each feed (default 100).
- **Report Date**: Stamped in the UI/export for easier record keeping.

## Scoring
For each merged topic cluster:
```
Trend_Score = 60 * freq_norm + 25 * source_diversity + 15 * recency_boost
```
- `freq_norm` = topic mentions / max mentions, then keyword boost (+0.1 each match, max +0.3) applied.
- `source_diversity` in [0,1] = unique source types / 3 (trends, reddit, rss).
- `recency_boost` in [0,1] = 1 for <=24h old, then linear decay to 0 by the chosen lookback window.

## Sample CSV Preview
```
Topic,Mentions,Source,Trend_Score,Date
"ai-powered founders",7,"reddit+rss",82.45,"2025-11-10 02:15 UTC"
"smb cybersecurity grants",4,"trends+rss",71.10,"2025-11-10 01:02 UTC"
```

## Exports & Automation
- **CSV**: `GET /export/csv?...` -> `trending_topics.csv`
- **JSON**: `GET /export/json?...` -> includes per-source `details` (title, link, published).
- Example cron (run daily at 7am, saving JSON):
    ```cron
    0 7 * * * curl "http://127.0.0.1:5000/export/json?geo=US&subreddits=Entrepreneur,Startups" -o ~/reports/trends.json
    ```

## Limitations
- Relies on public RSS only; Google Trends endpoint is daily and region-scoped.
- Reddit RSS may throttle if polled too frequently.
- No persistent storage; every request recomputes live.

## Privacy
No API keys or user data are stored. All processing occurs locally using publicly accessible feeds.
