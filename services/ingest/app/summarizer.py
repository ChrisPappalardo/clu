from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime

from openai import OpenAI
from pydantic import BaseModel, Field

from clu_core.models import (
    AppConfig,
    CollectedSourceData,
    DailySnapshot,
    SnapshotSection,
)


class AISectionSummary(BaseModel):
    section_id: str
    summary: str


class AIBrief(BaseModel):
    lead_summary: str
    themes: list[str] = Field(default_factory=list)
    section_summaries: list[AISectionSummary] = Field(default_factory=list)
    generation_notes: list[str] = Field(default_factory=list)


def _heuristic_brief(
    config: AppConfig,
    collected: list[CollectedSourceData],
    generated_at: datetime,
) -> DailySnapshot:
    section_map: dict[str, dict] = defaultdict(lambda: {"items": [], "metrics": []})
    attributions = []
    notes: list[str] = []
    for payload in collected:
        attributions.append(payload.source)
        notes.extend(payload.notes)
        section_map[payload.section]["items"].extend(payload.items)
        section_map[payload.section]["metrics"].extend(payload.metrics)

    sections: list[SnapshotSection] = []
    for section_id, content in section_map.items():
        items = sorted(
            content["items"],
            key=lambda item: item.published_at or generated_at,
            reverse=True,
        )[: config.briefing.max_headlines_per_section]
        metrics = content["metrics"][: config.briefing.max_headlines_per_section]
        summary_parts = []
        if items:
            summary_parts.append(f"{len(items)} notable items collected.")
        if metrics:
            summary_parts.append(f"{len(metrics)} structured signals updated.")
        sections.append(
            SnapshotSection(
                id=section_id,
                title=section_id.replace("-", " ").title(),
                kind="mixed" if items and metrics else ("news" if items else "data"),
                summary=" ".join(summary_parts) or "No significant updates collected.",
                items=items,
                metrics=metrics,
            )
        )

    sections = sections[: config.briefing.max_sections]
    return DailySnapshot(
        snapshot_id=generated_at.strftime("%Y%m%d"),
        snapshot_date=generated_at.date().isoformat(),
        generated_at=generated_at,
        timezone=config.user.timezone,
        lead_summary="Today's briefing is available. AI synthesis was not used, so section summaries are heuristic.",
        themes=[section.title for section in sections[:3]],
        sections=sections,
        source_attributions=attributions,
        generation_notes=notes + ["Generated with heuristic fallback summarization."],
    )


def synthesize_snapshot(
    config: AppConfig,
    collected: list[CollectedSourceData],
    generated_at: datetime,
) -> DailySnapshot:
    api_key = os.getenv("OPENAI_API_KEY")
    if not config.ai.enabled or not api_key:
        return _heuristic_brief(config, collected, generated_at)

    heuristic = _heuristic_brief(config, collected, generated_at)
    client = OpenAI(api_key=api_key)
    source_payload = [
        {
            "source_id": payload.source.source_id,
            "display_name": payload.source.display_name,
            "section": payload.section,
            "notes": payload.notes,
            "items": [
                {
                    "title": item.title,
                    "summary": item.summary,
                    "source_name": item.source_name,
                    "published_at": item.published_at.isoformat() if item.published_at else None,
                }
                for item in payload.items[:10]
            ],
            "metrics": [
                {
                    "label": metric.label,
                    "value": metric.value,
                    "change": metric.change,
                    "context": metric.context,
                }
                for metric in payload.metrics[:10]
            ],
        }
        for payload in collected
    ]
    response = client.responses.parse(
        model=config.ai.model,
        input=[
            {
                "role": "system",
                "content": (
                    "You create a concise but high-leverage daily world briefing. "
                    "Keep the tone neutral, synthesize cross-source patterns, and do not invent facts."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Using the collected signal below, produce a briefing lead, 3 to 6 themes, and one short summary per section. "
                    f"User preferences: {json.dumps(config.briefing.model_dump(), default=str)}. "
                    f"Collected sources: {json.dumps(source_payload, default=str)}"
                ),
            },
        ],
        text_format=AIBrief,
    )
    brief = response.output_parsed
    section_summaries = {row.section_id: row.summary for row in brief.section_summaries}

    sections = [
        section.model_copy(update={"summary": section_summaries.get(section.id, section.summary)})
        for section in heuristic.sections
    ]
    return heuristic.model_copy(
        update={
            "lead_summary": brief.lead_summary,
            "themes": brief.themes or heuristic.themes,
            "sections": sections,
            "generation_notes": heuristic.generation_notes + brief.generation_notes,
        }
    )

