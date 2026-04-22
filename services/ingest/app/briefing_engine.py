from __future__ import annotations

import math
import re
from collections import defaultdict
from datetime import datetime

from clu_core.models import (
    AppConfig,
    BriefingMemory,
    CollectedSourceData,
    DailySnapshot,
    SnapshotItem,
    SnapshotMetric,
    SnapshotSection,
    StoryCluster,
)


STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "of",
    "for",
    "in",
    "on",
    "at",
    "with",
    "from",
    "by",
    "after",
    "amid",
    "into",
    "over",
    "new",
}

SIGNIFICANCE_TERMS = {
    "war",
    "attack",
    "tariff",
    "election",
    "inflation",
    "earthquake",
    "sanction",
    "ceasefire",
    "outbreak",
    "rates",
    "recession",
    "storm",
}


def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [token for token in tokens if token not in STOPWORDS and len(token) > 2]


def _cluster_key(item: SnapshotItem) -> str:
    tokens = _tokenize(f"{item.title} {item.summary}")
    basis = tokens[:4] if tokens else [item.source_id]
    return "-".join(basis)


def _importance_score(item: SnapshotItem, generated_at: datetime) -> float:
    recency_bonus = 0.0
    if item.published_at is not None:
        delta_hours = max((generated_at - item.published_at).total_seconds() / 3600.0, 0.0)
        recency_bonus = max(0.0, 24.0 - min(delta_hours, 24.0)) / 24.0
    significance_bonus = 0.0
    combined = f"{item.title} {item.summary}".lower()
    if any(term in combined for term in SIGNIFICANCE_TERMS):
        significance_bonus = 0.4
    source_bonus = 0.15 if item.source_name.lower().startswith(("the guardian", "npr", "associated press")) else 0.0
    return round(0.5 + recency_bonus + significance_bonus + source_bonus, 3)


def _build_previous_cluster_lookup(history: list[DailySnapshot]) -> dict[str, StoryCluster]:
    lookup: dict[str, StoryCluster] = {}
    for snapshot in history:
        for cluster in snapshot.clusters:
            lookup[cluster.id] = cluster
    return lookup


def build_sections_and_clusters(
    config: AppConfig,
    collected: list[CollectedSourceData],
    generated_at: datetime,
    history: list[DailySnapshot],
) -> tuple[list[SnapshotSection], list[StoryCluster], BriefingMemory, list, list[str]]:
    section_items: dict[str, list[SnapshotItem]] = defaultdict(list)
    section_metrics: dict[str, list[SnapshotMetric]] = defaultdict(list)
    source_attributions = []
    notes: list[str] = []
    previous_lookup = _build_previous_cluster_lookup(history)
    previous_cluster_ids = set(previous_lookup.keys())

    for payload in collected:
        source_attributions.append(payload.source)
        notes.extend(payload.notes)
        for item in payload.items:
            item.importance_score = _importance_score(item, generated_at)
            item.cluster_key = _cluster_key(item)
            section_items[payload.section].append(item)
        section_metrics[payload.section].extend(payload.metrics)

    all_clusters: list[StoryCluster] = []
    sections: list[SnapshotSection] = []
    for section_id in config.briefing.include_sections or list(section_items.keys() | section_metrics.keys()):
        items = section_items.get(section_id, [])
        metrics = section_metrics.get(section_id, [])

        grouped: dict[str, list[SnapshotItem]] = defaultdict(list)
        for item in items:
            grouped[item.cluster_key or item.id].append(item)

        section_clusters: list[StoryCluster] = []
        for cluster_key, cluster_items in grouped.items():
            titles = [item.title for item in cluster_items]
            title = max(titles, key=len)
            summary = cluster_items[0].summary or title
            source_ids = sorted({item.source_id for item in cluster_items})
            source_names = sorted({item.source_name for item in cluster_items})
            importance = round(
                sum(item.importance_score for item in cluster_items) / max(len(cluster_items), 1)
                + math.log(len(source_ids) + 1.0, 2) * 0.35,
                3,
            )
            novelty = 1.0
            related_previous = [
                prev_id
                for prev_id, prev_cluster in previous_lookup.items()
                if prev_cluster.section == section_id and (
                    cluster_key in prev_cluster.id or prev_cluster.id.split(":", 1)[-1] == cluster_key
                )
            ]
            if related_previous:
                novelty = 0.35
            significance = "high" if importance >= 1.75 else ("medium" if importance >= 1.1 else "low")
            cluster_id = f"{generated_at.strftime('%Y%m%d')}:{section_id}:{cluster_key}"
            for item in cluster_items:
                item.novelty_score = novelty
            section_clusters.append(
                StoryCluster(
                    id=cluster_id,
                    section=section_id,
                    title=title,
                    summary=summary,
                    why_it_matters="This is one of the most relevant developments in the section based on recency, source overlap, and topic significance.",
                    importance_score=importance,
                    novelty_score=novelty,
                    significance=significance,
                    item_ids=[item.id for item in cluster_items],
                    source_ids=source_ids,
                    source_names=source_names,
                    geography=sorted({geo for item in cluster_items for geo in item.geography}),
                    topics=sorted({topic for item in cluster_items for topic in item.topics}),
                    watch_points=["Watch for follow-up reporting, official statements, and market or diplomatic reaction."],
                    developments=[item.title for item in cluster_items[:3]],
                    related_previous_cluster_ids=related_previous,
                )
            )

        section_clusters.sort(
            key=lambda cluster: (cluster.importance_score, cluster.novelty_score),
            reverse=True,
        )
        items.sort(key=lambda item: (item.importance_score, item.published_at or generated_at), reverse=True)
        metrics = metrics[: config.briefing.max_headlines_per_section]
        top_items = items[: config.briefing.max_headlines_per_section]
        top_clusters = section_clusters[: config.briefing.max_headlines_per_section]

        summary_parts = []
        if top_clusters:
            summary_parts.append(f"{len(top_clusters)} story clusters ranked for significance.")
        if metrics:
            summary_parts.append(f"{len(metrics)} structured indicators updated.")
        sections.append(
            SnapshotSection(
                id=section_id,
                title=section_id.replace("-", " ").title(),
                kind="mixed" if top_items and metrics else ("news" if top_items else "data"),
                summary=" ".join(summary_parts) or "No significant updates collected.",
                narrative=None,
                items=top_items,
                metrics=metrics,
                clusters=top_clusters,
            )
        )
        all_clusters.extend(top_clusters)

    all_clusters.sort(key=lambda cluster: (cluster.importance_score, cluster.novelty_score), reverse=True)
    continuing = [cluster.id for cluster in all_clusters if cluster.related_previous_cluster_ids]
    newly_emerged = [cluster.id for cluster in all_clusters if not cluster.related_previous_cluster_ids]
    dropped = sorted(previous_cluster_ids - {related for cluster in all_clusters for related in cluster.related_previous_cluster_ids})

    memory = BriefingMemory(
        prior_snapshot_id=history[-1].snapshot_id if history else None,
        prior_snapshot_date=history[-1].snapshot_date if history else None,
        continuing_cluster_ids=continuing[:10],
        newly_emerged_cluster_ids=newly_emerged[:10],
        dropped_cluster_ids=dropped[:10],
        continuity_note=(
            f"{len(continuing)} continuing stories and {len(newly_emerged)} newly emerged stories compared with the last snapshot."
            if history
            else "No prior snapshot available yet."
        ),
    )
    return sections[: config.briefing.max_sections], all_clusters[:20], memory, source_attributions, notes
