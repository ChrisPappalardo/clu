from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from openai import OpenAI
from pydantic import BaseModel, Field

from clu_core.models import (
    AppConfig,
    DailySnapshot,
    SnapshotSection,
    StoryCluster,
    WatchItem,
)


class AIClusterUpdate(BaseModel):
    cluster_id: str
    summary: str
    why_it_matters: str
    watch_points: list[str] = Field(default_factory=list)


class AISectionUpdate(BaseModel):
    section_id: str
    summary: str
    narrative: str


class AIBrief(BaseModel):
    lead_summary: str
    outlook: str
    themes: list[str] = Field(default_factory=list)
    top_story_ids: list[str] = Field(default_factory=list)
    watch_items: list[WatchItem] = Field(default_factory=list)
    cluster_updates: list[AIClusterUpdate] = Field(default_factory=list)
    section_updates: list[AISectionUpdate] = Field(default_factory=list)
    generation_notes: list[str] = Field(default_factory=list)


def build_snapshot_payload(
    config: AppConfig,
    generated_at: datetime,
    sections: list[SnapshotSection],
    clusters: list[StoryCluster],
    source_attributions,
    notes: list[str],
    memory,
) -> DailySnapshot:
    snapshot_id = generated_at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return DailySnapshot(
        snapshot_id=snapshot_id,
        snapshot_date=generated_at.date().isoformat(),
        generated_at=generated_at,
        timezone=config.user.timezone,
        lead_summary="Today's briefing is available. AI synthesis was not used, so story ranking and narratives are heuristic.",
        outlook="Watch the top-ranked stories for confirmation, official responses, and follow-on market or policy effects.",
        themes=[cluster.title for cluster in clusters[:3]],
        top_story_ids=[cluster.id for cluster in clusters[:5]],
        watch_items=[
            WatchItem(
                label=cluster.title,
                note="Monitor for fresh facts, official statements, and downstream consequences.",
                section_id=cluster.section,
            )
            for cluster in clusters[:3]
        ],
        sections=sections,
        clusters=clusters,
        memory=memory,
        source_attributions=source_attributions,
        generation_notes=notes + ["Generated with heuristic fallback briefing."],
    )


def synthesize_snapshot(
    config: AppConfig,
    base_snapshot: DailySnapshot,
    history: list[DailySnapshot],
) -> DailySnapshot:
    api_key = os.getenv("OPENAI_API_KEY")
    if not config.ai.enabled or not api_key:
        return base_snapshot

    client = OpenAI(api_key=api_key)
    source_payload = {
        "preferences": config.briefing.model_dump(),
        "history_summary": [
            {
                "snapshot_id": snapshot.snapshot_id,
                "snapshot_date": snapshot.snapshot_date,
                "lead_summary": snapshot.lead_summary,
                "themes": snapshot.themes,
                "top_clusters": [
                    {
                        "id": cluster.id,
                        "title": cluster.title,
                        "summary": cluster.summary,
                        "why_it_matters": cluster.why_it_matters,
                    }
                    for cluster in snapshot.clusters[:5]
                ],
            }
            for snapshot in history[-config.ai.history_window_days :]
        ],
        "current_snapshot": {
            "snapshot_date": base_snapshot.snapshot_date,
            "memory": base_snapshot.memory.model_dump(mode="json"),
            "clusters": [
                {
                    "id": cluster.id,
                    "section": cluster.section,
                    "title": cluster.title,
                    "summary": cluster.summary,
                    "importance_score": cluster.importance_score,
                    "novelty_score": cluster.novelty_score,
                    "significance": cluster.significance,
                    "source_names": cluster.source_names,
                    "developments": cluster.developments,
                    "related_previous_cluster_ids": cluster.related_previous_cluster_ids,
                }
                for cluster in base_snapshot.clusters[:15]
            ],
            "sections": [
                {
                    "id": section.id,
                    "title": section.title,
                    "summary": section.summary,
                    "top_cluster_ids": [cluster.id for cluster in section.clusters[:5]],
                    "metrics": [
                        {
                            "label": metric.label,
                            "value": metric.value,
                            "change": metric.change,
                            "context": metric.context,
                        }
                        for metric in section.metrics[:8]
                    ],
                }
                for section in base_snapshot.sections
            ],
        },
    }

    response = client.responses.parse(
        model=config.ai.model,
        input=[
            {
                "role": "system",
                "content": (
                    "You create a neutral, high-leverage daily world briefing. "
                    "Prioritize what changed, what matters most, and what to watch next. "
                    "Use prior snapshot context when present. Do not invent facts."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Given the current ranked story clusters, section metrics, and prior briefing history, "
                    "produce a structured morning briefing. "
                    f"Payload: {json.dumps(source_payload, default=str)}"
                ),
            },
        ],
        text_format=AIBrief,
    )
    brief = response.output_parsed

    cluster_updates = {row.cluster_id: row for row in brief.cluster_updates}
    section_updates = {row.section_id: row for row in brief.section_updates}

    updated_clusters = []
    for cluster in base_snapshot.clusters:
        update = cluster_updates.get(cluster.id)
        if update is None:
            updated_clusters.append(cluster)
            continue
        updated_clusters.append(
            cluster.model_copy(
                update={
                    "summary": update.summary,
                    "why_it_matters": update.why_it_matters,
                    "watch_points": update.watch_points or cluster.watch_points,
                }
            )
        )
    cluster_lookup = {cluster.id: cluster for cluster in updated_clusters}

    updated_sections = []
    for section in base_snapshot.sections:
        update = section_updates.get(section.id)
        updated_sections.append(
            section.model_copy(
                update={
                    "summary": update.summary if update else section.summary,
                    "narrative": update.narrative if update else section.narrative,
                    "clusters": [cluster_lookup[cluster.id] for cluster in section.clusters if cluster.id in cluster_lookup],
                }
            )
        )

    top_story_ids = [story_id for story_id in brief.top_story_ids if story_id in cluster_lookup]
    if not top_story_ids:
        top_story_ids = base_snapshot.top_story_ids

    return base_snapshot.model_copy(
        update={
            "lead_summary": brief.lead_summary,
            "outlook": brief.outlook,
            "themes": brief.themes or base_snapshot.themes,
            "top_story_ids": top_story_ids,
            "watch_items": brief.watch_items or base_snapshot.watch_items,
            "sections": updated_sections,
            "clusters": updated_clusters,
            "generation_notes": base_snapshot.generation_notes + brief.generation_notes,
        }
    )
