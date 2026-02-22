"""Google Trends RSS fetching utilities."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import List, Tuple

import feedparser
import requests
from dateutil import parser as date_parser

DEFAULT_TIMEOUT = 8


def fetch_trends(session: requests.Session, geo: str = "US", limit: int = 100) -> Tuple[List[dict], List[str]]:
    """Fetch trending topics from Google Trends RSS feed."""
    url = f"https://trends.google.com/trends/trendingsearches/daily/rss?geo={geo.upper()}"
    warnings: List[str] = []
    items: List[dict] = []

    try:
        content = _get_with_retry(session, url)
    except requests.RequestException as exc:  # pragma: no cover - network path
        warnings.append(f"Google Trends unavailable ({exc}).")
        return items, warnings

    feed = feedparser.parse(content)
    entries = feed.entries[:limit]

    for entry in entries:
        title = entry.get("title", "").strip()
        link = entry.get("link", "")
        published = _parse_date(entry.get("published") or entry.get("updated"))
        if not title:
            continue
        items.append(
            {
                "title": title,
                "link": link,
                "published": published,
                "source": f"Google Trends ({geo.upper()})",
                "source_type": "trends",
            }
        )

    if not items:
        warnings.append("Google Trends returned no entries.")

    return items, warnings


def _get_with_retry(session: requests.Session, url: str) -> bytes:
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = session.get(url, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()
            return response.content
        except requests.RequestException as exc:  # pragma: no cover - network path
            last_error = exc
            if attempt == 0:
                time.sleep(0.5)
    raise requests.RequestException(str(last_error))


def _parse_date(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        parsed = date_parser.parse(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)
