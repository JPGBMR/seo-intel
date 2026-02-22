from __future__ import annotations

import json
from datetime import date
from typing import Dict

import requests
from flask import Flask, Response, render_template, request, send_file, url_for

from modules import exporter, google_trends, merge_ranker, reddit_hot, rss_trends

app = Flask(__name__)
app.config["SECRET_KEY"] = "traffic-magnet-secret"
app.config["TEMPLATES_AUTO_RELOAD"] = True

_DEFAULT_FEEDS = ",".join(
    [
        "https://techcrunch.com/feed/",
        "https://hnrss.org/frontpage",
        "https://www.theverge.com/rss/index.xml",
    ]
)
DEFAULTS = {
    "keywords": "",
    "geo": "US",
    "subreddits": "Entrepreneur,Startups,SaaS",
    "feeds": _DEFAULT_FEEDS,
    "lookback": "3",
    "limit": "100",
    "report_date": date.today().strftime("%Y-%m-%d"),
}

_SESSION: requests.Session | None = None


def get_session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": "traffic-magnet-finder/1.0 (+https://github.com/)",
                "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
            }
        )
        _SESSION = session
    return _SESSION


def parse_params(args) -> Dict[str, object]:
    def get_value(key: str) -> str:
        raw = args.get(key)
        if raw is None or not str(raw).strip():
            return DEFAULTS.get(key, "")
        return str(raw).strip()

    keywords_raw = args.get("keywords", DEFAULTS["keywords"]) or ""
    keyword_list = [k.strip() for k in keywords_raw.split(",") if k.strip()]

    subreddits_raw = get_value("subreddits")
    subreddits = [s.strip() for s in subreddits_raw.split(",") if s.strip()]

    feeds_raw = get_value("feeds")
    feed_urls = [f.strip() for f in feeds_raw.split(",") if f.strip()]

    geo = get_value("geo") or DEFAULTS["geo"]
    lookback = _safe_int(get_value("lookback"), 3)
    limit = _safe_int(get_value("limit"), 100)
    report_date = get_value("report_date") or DEFAULTS["report_date"]

    return {
        "keywords_raw": keywords_raw,
        "keywords": keyword_list,
        "geo": geo.upper(),
        "subreddits_raw": subreddits_raw,
        "subreddits": subreddits,
        "feeds_raw": feeds_raw,
        "feeds": feed_urls,
        "lookback": lookback,
        "limit": limit,
        "report_date": report_date,
    }


def _safe_int(value: str, default: int) -> int:
    try:
        parsed = int(float(value))
        return parsed if parsed > 0 else default
    except (ValueError, TypeError):
        return default


def compute_results(params: Dict[str, object]):
    session = get_session()
    items = []
    warnings: list[str] = []

    trends_items, trends_warnings = google_trends.fetch_trends(
        session, params.get("geo", "US"), params.get("limit", 100)
    )
    items.extend(trends_items)
    warnings.extend(trends_warnings)

    reddit_items, reddit_warnings = reddit_hot.fetch_hot(
        session, params.get("subreddits", []), params.get("limit", 100)
    )
    items.extend(reddit_items)
    warnings.extend(reddit_warnings)

    rss_items, rss_warnings = rss_trends.fetch_feeds(
        session, params.get("feeds", []), params.get("limit", 100)
    )
    items.extend(rss_items)
    warnings.extend(rss_warnings)

    df, summary = merge_ranker.merge_topics(
        items,
        keywords=params.get("keywords", []),
        lookback_days=params.get("lookback", 3),
    )

    return df, summary, warnings


@app.route("/")
def index():
    params = parse_params(request.args)
    return render_template("index.html", params=params, defaults=DEFAULTS)


@app.route("/results")
def results():
    params = parse_params(request.args)
    df, summary, warnings = compute_results(params)

    topics = []
    if df is not None and not df.empty:
        for _, row in df.iterrows():
            topics.append(
                {
                    "Topic": row.get("Topic"),
                    "Mentions": int(row.get("Mentions", 0)),
                    "Source": row.get("Source"),
                    "Trend_Score": float(row.get("Trend_Score", 0.0)),
                    "Date": row.get("Date"),
                    "sources_list": row.get("sources_list", []),
                }
            )

    chart_df = df.head(15) if df is not None and not df.empty else None
    chart_data = {
        "labels": chart_df["Topic"].tolist() if chart_df is not None else [],
        "scores": [float(x) for x in chart_df["Trend_Score"].tolist()] if chart_df is not None else [],
    }
    chart_json = json.dumps(chart_data)
    query_params = request.args.to_dict(flat=True)
    export_csv_url = url_for("export_csv", **query_params)
    export_json_url = url_for("export_json", **query_params)

    return render_template(
        "results.html",
        params=params,
        topics=topics,
        summary=summary,
        warnings=warnings,
        chart_data=chart_json,
        query_params=query_params,
        export_csv_url=export_csv_url,
        export_json_url=export_json_url,
    )


@app.route("/export/csv")
def export_csv():
    params = parse_params(request.args)
    df, _, warnings = compute_results(params)
    csv_buffer = exporter.dataframe_to_csv(df)
    response = send_file(
        csv_buffer,
        mimetype="text/csv",
        as_attachment=True,
        download_name="trending_topics.csv",
    )
    if warnings:
        response.headers["X-Warnings"] = "; ".join(warnings)
    return response


@app.route("/export/json")
def export_json():
    params = parse_params(request.args)
    df, _, warnings = compute_results(params)
    json_buffer = exporter.dataframe_to_json(df)
    payload = json_buffer.getvalue()
    response = Response(payload, mimetype="application/json")
    if warnings:
        response.headers["X-Warnings"] = "; ".join(warnings)
    response.headers["Content-Disposition"] = "attachment; filename=trending_topics.json"
    return response


if __name__ == "__main__":
    app.run(debug=True)
