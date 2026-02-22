"""Topic normalization, similarity, and ranking utilities."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, List, Optional, Sequence

import pandas as pd
from bs4 import BeautifulSoup

TOKEN_PATTERN = re.compile(r"[^a-z0-9\s]")
WHITESPACE_PATTERN = re.compile(r"\s+")


@dataclass
class Cluster:
    normalized: str
    tokens: set
    topic: str
    items: List[dict]
    sources: set
    latest: datetime


def merge_topics(
    items: Sequence[dict],
    keywords: Optional[Iterable[str]] = None,
    lookback_days: int = 3,
) -> tuple[pd.DataFrame, dict]:
    keywords = _prepare_keywords(keywords)
    lookback_days = max(1, int(lookback_days or 1))
    now = datetime.now(timezone.utc)
    clusters: List[Cluster] = []

    for item in items:
        raw_title = item.get("title", "")
        text = _extract_text(raw_title)
        normalized = normalize_topic(text)
        if not normalized:
            continue
        tokens = set(normalized.split())
        if not tokens:
            continue
        published = item.get("published") or now
        if isinstance(published, datetime):
            published_dt = published.astimezone(timezone.utc)
        else:
            published_dt = now
        detail = {
            "title": text,
            "raw_title": raw_title,
            "link": item.get("link"),
            "source": item.get("source"),
            "source_type": item.get("source_type"),
            "published": published_dt,
        }
        cluster = _find_cluster(clusters, tokens)
        if cluster is None:
            clusters.append(
                Cluster(
                    normalized=normalized,
                    tokens=tokens,
                    topic=text,
                    items=[detail],
                    sources={item.get("source_type", "unknown")},
                    latest=published_dt,
                )
            )
        else:
            cluster.items.append(detail)
            cluster.sources.add(item.get("source_type", "unknown"))
            cluster.latest = max(cluster.latest, published_dt)
            if len(text) > len(cluster.topic):
                cluster.topic = text
            cluster.tokens = cluster.tokens.union(tokens)

    records = []
    max_mentions = max((len(cluster.items) for cluster in clusters), default=0)

    for cluster in clusters:
        mentions = len(cluster.items)
        freq_norm = (mentions / max_mentions) if max_mentions else 0
        freq_norm = min(1.0, freq_norm + _keyword_boost(cluster.normalized, keywords))
        source_div = len(cluster.sources) / 3.0
        recency = _recency_boost(cluster.latest, now, lookback_days)
        trend_score = 60 * freq_norm + 25 * source_div + 15 * recency
        records.append(
            {
                "Topic": cluster.topic,
                "Mentions": mentions,
                "Source": "+".join(sorted(cluster.sources)),
                "Trend_Score": round(trend_score, 2),
                "Date": cluster.latest.strftime("%Y-%m-%d %H:%M UTC"),
                "latest_dt": cluster.latest,
                "details": [
                    {
                        "title": detail["title"],
                        "source": detail["source"],
                        "source_type": detail["source_type"],
                        "link": detail["link"],
                        "published": detail["published"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                    }
                    for detail in cluster.items
                ],
                "sources_list": sorted(cluster.sources),
                "Recency": recency,
            }
        )

    records.sort(key=lambda row: row["Trend_Score"], reverse=True)
    df = pd.DataFrame(records)

    summary = {
        "total_topics": len(records),
        "fast_movers": sum(1 for row in records if row["Recency"] >= 0.7),
        "merged_mentions": sum(row["Mentions"] for row in records) if records else 0,
        "lookback_days": lookback_days,
    }

    return df, summary


def _extract_text(value: str) -> str:
    soup = BeautifulSoup(value or "", "html.parser")
    return soup.get_text(" ", strip=True)


def normalize_topic(value: str) -> str:
    lowered = value.lower()
    stripped = TOKEN_PATTERN.sub(" ", lowered)
    collapsed = WHITESPACE_PATTERN.sub(" ", stripped)
    return collapsed.strip()


def _find_cluster(clusters: List[Cluster], tokens: set) -> Optional[Cluster]:
    best_cluster: Optional[Cluster] = None
    best_score = 0.0
    for cluster in clusters:
        score = _jaccard(tokens, cluster.tokens)
        if score >= 0.8 and score > best_score:
            best_cluster = cluster
            best_score = score
    return best_cluster


def _jaccard(tokens_a: set, tokens_b: set) -> float:
    intersection = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)
    if union == 0:
        return 0.0
    return intersection / union


def _recency_boost(latest: datetime, now: datetime, lookback_days: int) -> float:
    age_hours = max(0.0, (now - latest).total_seconds() / 3600)
    window_hours = max(lookback_days * 24.0, 24.0)
    if age_hours <= 24:
        return 1.0
    decay_window = max(window_hours - 24.0, 1.0)
    progress = min(1.0, (age_hours - 24.0) / decay_window)
    return max(0.0, 1.0 - progress)


def _prepare_keywords(keywords: Optional[Iterable[str]]) -> List[str]:
    prepared: List[str] = []
    if not keywords:
        return prepared
    for keyword in keywords:
        term = normalize_topic(keyword)
        if term:
            prepared.append(term)
    return prepared


def _keyword_boost(normalized_topic: str, keywords: Sequence[str]) -> float:
    if not keywords:
        return 0.0
    matches = 0
    for keyword in keywords:
        if not keyword:
            continue
        if re.search(rf"\b{re.escape(keyword)}\b", normalized_topic):
            matches += 1
    return min(0.3, matches * 0.1)
