"""Generic RSS trend feed fetching."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Iterable, List, Tuple

import feedparser
import requests
from dateutil import parser as date_parser

DEFAULT_TIMEOUT = 8


def fetch_feeds(
    session: requests.Session, feed_urls: Iterable[str], limit: int = 100
) -> Tuple[List[dict], List[str]]:
    """Fetch entries from a list of RSS feeds."""
    warnings: List[str] = []
    items: List[dict] = []

    for feed_url in feed_urls:
        url = feed_url.strip()
        if not url:
            continue
        try:
            content = _get_with_retry(session, url)
        except requests.RequestException as exc:  # pragma: no cover - network path
            warnings.append(f"Feed {url} skipped ({exc}).")
            continue
        feed = feedparser.parse(content)
        entries = feed.entries[:limit]
        source_label = feed.feed.get("title") if feed.feed else url
        for entry in entries:
            title = entry.get("title", "").strip()
            link = entry.get("link", url)
            published = _parse_date(entry.get("published") or entry.get("updated"))
            if not title:
                continue
            items.append(
                {
                    "title": title,
                    "link": link,
                    "published": published,
                    "source": source_label or url,
                    "source_type": "rss",
                }
            )
        if not entries:
            warnings.append(f"Feed {url} returned no entries.")

    if not items:
        warnings.append("General RSS feeds returned no topics.")

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
