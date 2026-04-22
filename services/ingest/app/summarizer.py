from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import TypeVar

from openai import OpenAI
from openai import APIConnectionError, APIError
from pydantic import BaseModel, Field
from pydantic import ValidationError

from clu_core.models import (
    AIConfig,
    AppConfig,
    DailySnapshot,
    SnapshotSection,
    StoryCluster,
    WatchItem,
)


class AIClusterInterpretation(BaseModel):
    cluster_id: str
    summary: str
    what_changed: str
    why_now: str
    why_it_matters: str
    risk_level: str
    risk_summary: str
    watch_points: list[str] = Field(default_factory=list)


class AISectionInterpretation(BaseModel):
    section_id: str
    summary: str
    narrative: str
    what_changed: str
    why_now: str
    risk_summary: str


class AIInterpretationPass(BaseModel):
    cluster_updates: list[AIClusterInterpretation] = Field(default_factory=list)
    section_updates: list[AISectionInterpretation] = Field(default_factory=list)
    generation_notes: list[str] = Field(default_factory=list)


class AIGlobalBrief(BaseModel):
    lead_summary: str
    what_changed_summary: str
    outlook: str
    risk_summary: str
    themes: list[str] = Field(default_factory=list)
    top_story_ids: list[str] = Field(default_factory=list)
    watch_items: list[WatchItem] = Field(default_factory=list)
    generation_notes: list[str] = Field(default_factory=list)


T = TypeVar("T", bound=BaseModel)
META_PHRASES = (
    "would generally",
    "here is an example",
    "based on the information provided",
    "based on the dataset",
    "the lead summary",
    "this summary",
)


def _preferred_top_clusters(clusters: list[StoryCluster]) -> list[StoryCluster]:
    robust = [
        cluster
        for cluster in clusters
        if len(cluster.source_ids) >= 2 or cluster.significance == "high" or cluster.risk_level == "high"
    ]
    return robust or clusters


def _build_client(ai_config: AIConfig) -> OpenAI:
    api_key = os.getenv(ai_config.api_key_env, "")
    base_url = ai_config.base_url or None
    provider = ai_config.provider.lower()
    if provider == "ollama":
        return OpenAI(
            base_url=base_url or "http://host.docker.internal:11434/v1/",
            api_key=api_key or "ollama",
        )
    return OpenAI(
        base_url=base_url,
        api_key=api_key,
    )


def _has_usable_ai_credentials(ai_config: AIConfig) -> bool:
    if ai_config.provider.lower() == "ollama":
        return True
    return bool(os.getenv(ai_config.api_key_env, ""))


def _json_schema_payload(model_class: type[T]) -> dict:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": model_class.__name__,
            "schema": model_class.model_json_schema(),
        },
    }


def _structured_chat_completion(
    client: OpenAI,
    ai_config: AIConfig,
    *,
    system_prompt: str,
    user_prompt: str,
    model_class: type[T],
) -> T:
    completion = client.chat.completions.create(
        model=ai_config.model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=_json_schema_payload(model_class),
    )
    content = completion.choices[0].message.content or "{}"
    return model_class.model_validate_json(content)


def _contains_meta_language(text: str | None) -> bool:
    if not text:
        return False
    lowered = text.lower()
    return any(phrase in lowered for phrase in META_PHRASES)


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
    preferred_top = _preferred_top_clusters(clusters)
    return DailySnapshot(
        snapshot_id=snapshot_id,
        snapshot_date=generated_at.date().isoformat(),
        generated_at=generated_at,
        timezone=config.user.timezone,
        lead_summary="Today's briefing is available. AI synthesis was not used, so story ranking and interpretation are heuristic.",
        what_changed_summary=(
            memory.continuity_note
            if memory.continuity_note
            else "No prior snapshot is available yet, so this is a first-pass morning baseline."
        ),
        outlook="Watch the top-ranked stories for confirmation, official responses, and follow-on market or policy effects.",
        risk_summary="Risk remains heuristic until AI interpretation is enabled; use top stories and watch items as the main signal.",
        themes=[cluster.title for cluster in clusters[:3]],
        top_story_ids=[cluster.id for cluster in preferred_top[:5]],
        watch_items=[
            WatchItem(
                label=cluster.title,
                note=(cluster.watch_points[0] if cluster.watch_points else "Monitor for fresh facts and downstream consequences."),
                section_id=cluster.section,
            )
            for cluster in preferred_top[:3]
        ],
        sections=[
            section.model_copy(
                update={
                    "what_changed": (
                        "No significant new developments were detected."
                        if not section.clusters
                        else f"{len(section.clusters)} main story clusters are driving this section."
                    ),
                    "why_now": (
                        "This section matters now because the leading stories or indicators are active in the current snapshot."
                    ),
                    "risk_summary": (
                        "Risk is driven by the most prominent cluster in this section."
                        if section.clusters
                        else "No immediate section-level risk signal was identified."
                    ),
                }
            )
            for section in sections
        ],
        clusters=[
            cluster.model_copy(
                update={
                    "what_changed": cluster.what_changed
                    or (
                        "This story appears to be continuing from the prior snapshot."
                        if cluster.related_previous_cluster_ids
                        else "This story appears new in the current snapshot."
                    ),
                    "why_now": cluster.why_now
                    or "It is showing up near the top because of recency, source overlap, and topic significance.",
                    "risk_level": cluster.risk_level or ("high" if cluster.significance == "high" else "medium"),
                    "risk_summary": cluster.risk_summary
                    or "Risk remains heuristic; look for official actions, escalation, and second-order effects.",
                }
            )
            for cluster in clusters
        ],
        memory=memory,
        source_attributions=source_attributions,
        generation_notes=notes + ["Generated with heuristic fallback briefing."],
    )


def _history_payload(config: AppConfig, history: list[DailySnapshot]) -> list[dict]:
    return [
        {
            "snapshot_id": snapshot.snapshot_id,
            "snapshot_date": snapshot.snapshot_date,
            "lead_summary": snapshot.lead_summary,
            "what_changed_summary": snapshot.what_changed_summary,
            "themes": snapshot.themes,
            "top_clusters": [
                {
                    "id": cluster.id,
                    "title": cluster.title,
                    "summary": cluster.summary,
                    "what_changed": cluster.what_changed,
                    "why_it_matters": cluster.why_it_matters,
                }
                for cluster in snapshot.clusters[:5]
            ],
        }
        for snapshot in history[-config.ai.history_window_days :]
    ]


def _current_payload(base_snapshot: DailySnapshot, config: AppConfig) -> dict:
    return {
        "snapshot_date": base_snapshot.snapshot_date,
        "memory": base_snapshot.memory.model_dump(mode="json"),
        "clusters": [
            {
                "id": cluster.id,
                "section": cluster.section,
                "title": cluster.title,
                "summary": cluster.summary,
                "what_changed": cluster.what_changed,
                "why_now": cluster.why_now,
                "importance_score": cluster.importance_score,
                "novelty_score": cluster.novelty_score,
                "significance": cluster.significance,
                "source_names": cluster.source_names,
                "developments": cluster.developments,
                "related_previous_cluster_ids": cluster.related_previous_cluster_ids,
            }
            for cluster in base_snapshot.clusters[: max(10, config.ai.max_input_items_per_section)]
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
    }


def _run_interpretation_pass(
    client: OpenAI,
    config: AppConfig,
    history_payload: list[dict],
    current_payload: dict,
) -> AIInterpretationPass:
    return _structured_chat_completion(
        client,
        config.ai,
        system_prompt=(
            "You are an analyst producing structured morning-briefing interpretations. "
            "For each cluster and section, explain what changed, why it matters now, and the main risk. "
            "Be neutral, concise, and avoid speculation beyond the provided evidence. "
            "Do not overstate thin single-source stories unless they are clearly high-significance."
        ),
        user_prompt=(
            "Interpret the current ranked clusters and sections in light of the recent snapshot history. "
            f"Preferences: {json.dumps(config.briefing.model_dump(), default=str)}. "
            f"History: {json.dumps(history_payload, default=str)}. "
            f"Current snapshot: {json.dumps(current_payload, default=str)}."
        ),
        model_class=AIInterpretationPass,
    )


def _run_global_brief_pass(
    client: OpenAI,
    config: AppConfig,
    history_payload: list[dict],
    enriched_snapshot: DailySnapshot,
) -> AIGlobalBrief:
    return _structured_chat_completion(
        client,
        config.ai,
        system_prompt=(
            "You create a neutral, high-leverage daily world briefing. "
            "Summarize what changed since the prior briefing, identify the biggest risks, and tell the reader what to watch next. "
            "Do not invent facts. Prefer clusters with broader source support or clearly high significance when selecting top stories. "
            "Avoid repeating the same point across lead summary, themes, and watch items. "
            "Write direct declarative prose only. Do not mention prompts, datasets, examples, or how the summary was produced."
        ),
        user_prompt=(
            "Using the enriched snapshot below, produce the final top-level morning briefing. "
            f"Preferences: {json.dumps(config.briefing.model_dump(), default=str)}. "
            f"History: {json.dumps(history_payload, default=str)}. "
            f"Enriched snapshot: {json.dumps(enriched_snapshot.model_dump(mode='json'), default=str)}"
        ),
        model_class=AIGlobalBrief,
    )


def synthesize_snapshot(
    config: AppConfig,
    base_snapshot: DailySnapshot,
    history: list[DailySnapshot],
) -> DailySnapshot:
    if not config.ai.enabled or not _has_usable_ai_credentials(config.ai):
        return base_snapshot

    client = _build_client(config.ai)
    history_payload = _history_payload(config, history)
    current_payload = _current_payload(base_snapshot, config)

    try:
        interpretation = _run_interpretation_pass(client, config, history_payload, current_payload)
        cluster_updates = {row.cluster_id: row for row in interpretation.cluster_updates}
        section_updates = {row.section_id: row for row in interpretation.section_updates}

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
                        "what_changed": update.what_changed,
                        "why_now": update.why_now,
                        "why_it_matters": update.why_it_matters,
                        "risk_level": update.risk_level if update.risk_level in {"high", "medium", "low"} else cluster.risk_level,
                        "risk_summary": update.risk_summary,
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
                        "what_changed": update.what_changed if update else section.what_changed,
                        "why_now": update.why_now if update else section.why_now,
                        "risk_summary": update.risk_summary if update else section.risk_summary,
                        "clusters": [cluster_lookup[cluster.id] for cluster in section.clusters if cluster.id in cluster_lookup],
                    }
                )
            )

        enriched_snapshot = base_snapshot.model_copy(
            update={
                "sections": updated_sections,
                "clusters": updated_clusters,
                "generation_notes": [
                    note
                    for note in base_snapshot.generation_notes
                    if note != "Generated with heuristic fallback briefing."
                ]
                + interpretation.generation_notes,
            }
        )

        global_brief = _run_global_brief_pass(client, config, history_payload, enriched_snapshot)
        if _contains_meta_language(global_brief.lead_summary) or _contains_meta_language(global_brief.what_changed_summary):
            raise ValueError("AI global brief contained meta/template language.")
        top_story_ids = [story_id for story_id in global_brief.top_story_ids if story_id in cluster_lookup]
        if not top_story_ids:
            top_story_ids = [cluster.id for cluster in _preferred_top_clusters(enriched_snapshot.clusters)[:5]]

        return enriched_snapshot.model_copy(
            update={
                "lead_summary": global_brief.lead_summary,
                "what_changed_summary": global_brief.what_changed_summary,
                "outlook": global_brief.outlook,
                "risk_summary": global_brief.risk_summary,
                "themes": global_brief.themes or enriched_snapshot.themes,
                "top_story_ids": top_story_ids,
                "watch_items": global_brief.watch_items or enriched_snapshot.watch_items,
                "generation_notes": enriched_snapshot.generation_notes + global_brief.generation_notes,
            }
        )
    except (APIConnectionError, APIError, ValidationError, ValueError, json.JSONDecodeError) as exc:
        return base_snapshot.model_copy(
            update={
                "generation_notes": base_snapshot.generation_notes
                + [f"AI synthesis failed and fell back to heuristic briefing: {exc}"],
            }
        )
