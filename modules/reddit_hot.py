"""Reddit subreddit RSS fetching utilities."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Iterable, List, Tuple

import feedparser
import requests
from dateutil import parser as date_parser

DEFAULT_TIMEOUT = 8


def fetch_hot(
    session: requests.Session, subreddits: Iterable[str], limit: int = 100
) -> Tuple[List[dict], List[str]]:
    """Fetch hot topics from subreddit RSS feeds."""
    warnings: List[str] = []
    items: List[dict] = []

    for subreddit in subreddits:
        sub = subreddit.strip()
        if not sub:
            continue
        url = f"https://www.reddit.com/r/{sub}/.rss"
        try:
            content = _get_with_retry(session, url)
        except requests.RequestException as exc:  # pragma: no cover - network path
            warnings.append(f"Reddit /r/{sub} skipped ({exc}).")
            continue
        feed = feedparser.parse(content)
        entries = feed.entries[:limit]
        for entry in entries:
            title = entry.get("title", "").strip()
            link = entry.get("link", "")
            published = _parse_date(entry.get("updated") or entry.get("published"))
            if not title:
                continue
            items.append(
                {
                    "title": title,
                    "link": link,
                    "published": published,
                    "source": f"Reddit r/{sub}",
                    "source_type": "reddit",
                }
            )
        if not entries:
            warnings.append(f"Reddit /r/{sub} returned no entries.")

    if not items:
        warnings.append("Reddit feeds returned no topics.")

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
