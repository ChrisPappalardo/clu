from __future__ import annotations

import math
import re
from collections import defaultdict
from datetime import datetime, timezone

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
    "says",
    "say",
    "report",
    "reports",
    "today",
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
    "blockade",
    "seized",
    "strike",
    "missile",
    "fire",
}

SOURCE_QUALITY_HINTS = {
    "npr": 0.22,
    "guardian": 0.18,
    "associated press": 0.25,
    "usgs": 0.28,
    "open-meteo": 0.2,
    "world bank": 0.18,
    "fred": 0.18,
}


def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [token for token in tokens if token not in STOPWORDS and len(token) > 2]


def _token_set(text: str) -> set[str]:
    return set(_tokenize(text))


def _cluster_key_from_tokens(tokens: set[str], fallback: str) -> str:
    basis = sorted(tokens)[:4]
    if not basis:
        basis = [fallback]
    return "-".join(basis)


def _source_quality_bonus(source_name: str, source_id: str) -> float:
    normalized = f"{source_name} {source_id}".lower()
    for hint, bonus in SOURCE_QUALITY_HINTS.items():
        if hint in normalized:
            return bonus
    return 0.0


def _importance_score(item: SnapshotItem, generated_at: datetime) -> float:
    recency_bonus = 0.0
    if item.published_at is not None:
        delta_hours = max((generated_at - item.published_at).total_seconds() / 3600.0, 0.0)
        recency_bonus = max(0.0, 24.0 - min(delta_hours, 24.0)) / 24.0
    significance_bonus = 0.0
    combined_tokens = _token_set(f"{item.title} {item.summary}")
    significance_hits = len(combined_tokens & SIGNIFICANCE_TERMS)
    if significance_hits:
        significance_bonus = min(0.5, 0.18 * significance_hits)
    source_bonus = _source_quality_bonus(item.source_name, item.source_id)
    length_bonus = 0.08 if len(combined_tokens) >= 6 else 0.0
    return round(0.45 + recency_bonus + significance_bonus + source_bonus + length_bonus, 3)


def _build_previous_cluster_lookup(history: list[DailySnapshot]) -> dict[str, StoryCluster]:
    lookup: dict[str, StoryCluster] = {}
    for snapshot in history:
        for cluster in snapshot.clusters:
            lookup[cluster.id] = cluster
    return lookup


def _cluster_signature(cluster_id: str) -> str:
    parts = cluster_id.split(":", 2)
    if len(parts) == 3:
        return parts[2]
    return cluster_id


def _cluster_token_signature(cluster: StoryCluster) -> set[str]:
    return _token_set(" ".join([cluster.title, cluster.summary, *cluster.developments]))


def _jaccard_similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def _continuity_matches(
    section_id: str,
    cluster_tokens: set[str],
    cluster_key: str,
    previous_lookup: dict[str, StoryCluster],
) -> list[str]:
    matches: list[tuple[str, float]] = []
    for prev_id, prev_cluster in previous_lookup.items():
        if prev_cluster.section != section_id:
            continue
        similarity = _jaccard_similarity(cluster_tokens, _cluster_token_signature(prev_cluster))
        if _cluster_signature(prev_cluster.id) == cluster_key:
            similarity = max(similarity, 0.95)
        if similarity >= 0.3:
            matches.append((prev_id, similarity))
    matches.sort(key=lambda row: row[1], reverse=True)
    return [match_id for match_id, _ in matches[:3]]


def _assign_cluster_keys(items: list[SnapshotItem]) -> dict[str, list[SnapshotItem]]:
    groups: list[dict] = []
    for item in items:
        tokens = _token_set(f"{item.title} {item.summary}")
        matched_group = None
        best_similarity = 0.0
        for group in groups:
            similarity = _jaccard_similarity(tokens, group["tokens"])
            if similarity > best_similarity and similarity >= 0.34:
                matched_group = group
                best_similarity = similarity
        if matched_group is None:
            cluster_key = _cluster_key_from_tokens(tokens, item.source_id)
            new_group = {
                "key": cluster_key,
                "tokens": set(tokens),
                "items": [item],
            }
            groups.append(new_group)
            item.cluster_key = cluster_key
        else:
            matched_group["tokens"].update(tokens)
            matched_group["items"].append(item)
            item.cluster_key = matched_group["key"]

    return {group["key"]: group["items"] for group in groups}


def _cluster_risk_level(cluster_tokens: set[str], significance: str) -> str:
    if significance == "high" or {"war", "attack", "earthquake", "storm", "sanction"} & cluster_tokens:
        return "high"
    if significance == "medium" or {"rates", "inflation", "tariff", "blockade"} & cluster_tokens:
        return "medium"
    return "low"


def _cluster_support_penalty(source_count: int, cluster_tokens: set[str]) -> float:
    # Penalize thin single-source stories unless they contain obviously high-significance terms.
    if source_count >= 2:
        return 0.0
    if {"war", "attack", "earthquake", "storm", "sanction", "ceasefire"} & cluster_tokens:
        return 0.0
    return 0.28


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
            section_items[payload.section].append(item)
        section_metrics[payload.section].extend(payload.metrics)

    all_clusters: list[StoryCluster] = []
    sections: list[SnapshotSection] = []
    ordered_sections = config.briefing.include_sections or list(section_items.keys() | section_metrics.keys())
    cluster_run_id = generated_at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    for section_id in ordered_sections:
        items = section_items.get(section_id, [])
        metrics = section_metrics.get(section_id, [])
        grouped = _assign_cluster_keys(items)

        section_clusters: list[StoryCluster] = []
        for cluster_key, cluster_items in grouped.items():
            cluster_items.sort(
                key=lambda item: (item.importance_score, item.published_at or generated_at),
                reverse=True,
            )
            cluster_tokens = set().union(*[_token_set(f"{item.title} {item.summary}") for item in cluster_items]) if cluster_items else set()
            title = max((item.title for item in cluster_items), key=len)
            summary = next((item.summary for item in cluster_items if item.summary), title)
            source_ids = sorted({item.source_id for item in cluster_items})
            source_names = sorted({item.source_name for item in cluster_items})
            source_quality = sum(_source_quality_bonus(item.source_name, item.source_id) for item in cluster_items) / max(len(cluster_items), 1)
            source_diversity_bonus = math.log(len(source_ids) + 1.0, 2) * 0.3
            support_penalty = _cluster_support_penalty(len(source_ids), cluster_tokens)
            importance = round(
                sum(item.importance_score for item in cluster_items) / max(len(cluster_items), 1)
                + source_diversity_bonus
                + source_quality,
                3,
            )
            importance = round(
                importance - support_penalty,
                3,
            )

            related_previous = _continuity_matches(section_id, cluster_tokens, cluster_key, previous_lookup)
            novelty = 0.3 if related_previous else 1.0
            significance = "high" if importance >= 1.9 else ("medium" if importance >= 1.22 else "low")
            risk_level = _cluster_risk_level(cluster_tokens, significance)
            cluster_id = f"{cluster_run_id}:{section_id}:{cluster_key}"

            for item in cluster_items:
                item.novelty_score = novelty
                item.cluster_key = cluster_key

            section_clusters.append(
                StoryCluster(
                    id=cluster_id,
                    section=section_id,
                    title=title,
                    summary=summary,
                    what_changed=(
                        "This story is continuing from the previous snapshot with new reporting."
                        if related_previous
                        else "This is a newly emerged cluster in the current snapshot."
                    ),
                    why_now="It rose to the top because of recency, source quality, and overlap across sources.",
                    why_it_matters="This is one of the most relevant developments in the section based on recency, source overlap, and topic significance.",
                    risk_level=risk_level,
                    risk_summary=(
                        "This cluster carries higher operational or geopolitical risk and should be watched for rapid updates."
                        if risk_level == "high"
                        else "This cluster could become more significant if follow-up reporting confirms further escalation or broader impact."
                    ),
                    importance_score=importance,
                    novelty_score=novelty,
                    significance=significance,
                    item_ids=[item.id for item in cluster_items],
                    source_ids=source_ids,
                    source_names=source_names,
                    geography=sorted({geo for item in cluster_items for geo in item.geography}),
                    topics=sorted({topic for item in cluster_items for topic in item.topics}),
                    watch_points=[
                        "Watch for follow-up reporting, official statements, and second-order policy, diplomatic, or market effects."
                    ],
                    developments=[item.title for item in cluster_items[:3]],
                    related_previous_cluster_ids=related_previous,
                )
            )

        section_clusters.sort(
            key=lambda cluster: (cluster.importance_score, cluster.novelty_score, len(cluster.source_ids)),
            reverse=True,
        )
        items.sort(key=lambda item: (item.importance_score, item.novelty_score, item.published_at or generated_at), reverse=True)
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

    all_clusters.sort(
        key=lambda cluster: (cluster.importance_score, cluster.novelty_score, len(cluster.source_ids)),
        reverse=True,
    )
    continuing = [cluster.id for cluster in all_clusters if cluster.related_previous_cluster_ids]
    newly_emerged = [cluster.id for cluster in all_clusters if not cluster.related_previous_cluster_ids]
    matched_previous = {related for cluster in all_clusters for related in cluster.related_previous_cluster_ids}
    dropped = sorted(previous_cluster_ids - matched_previous)

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
