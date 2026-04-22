from __future__ import annotations

import json
import os
from typing import TypeVar

from openai import OpenAI
from openai import APIConnectionError, APIError
from pydantic import BaseModel, Field
from pydantic import ValidationError

from clu_core.models import AIConfig, AppConfig, CollectedSourceData, SnapshotItem


class ItemEnrichment(BaseModel):
    item_id: str
    content_type: str
    significance: str
    topics: list[str] = Field(default_factory=list)
    geography: list[str] = Field(default_factory=list)
    same_story_hints: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class BatchEnrichment(BaseModel):
    items: list[ItemEnrichment] = Field(default_factory=list)


T = TypeVar("T", bound=BaseModel)


def _build_client(ai_config: AIConfig) -> OpenAI:
    api_key = os.getenv(ai_config.api_key_env, "")
    base_url = ai_config.base_url or None
    provider = ai_config.provider.lower()
    if provider == "ollama":
        return OpenAI(
            base_url=base_url or "http://host.docker.internal:11434/v1/",
            api_key=api_key or "ollama",
        )
    return OpenAI(base_url=base_url, api_key=api_key)


def _json_schema_payload(model_class: type[T]) -> dict:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": model_class.__name__,
            "schema": model_class.model_json_schema(),
        },
    }


def _structured_completion(
    client: OpenAI,
    *,
    model: str,
    system_prompt: str,
    user_prompt: str,
    model_class: type[T],
) -> T:
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=_json_schema_payload(model_class),
    )
    content = completion.choices[0].message.content or "{}"
    return model_class.model_validate_json(content)


def enrich_collected_data(config: AppConfig, collected: list[CollectedSourceData]) -> tuple[list[CollectedSourceData], list[str]]:
    fast_model = config.ai.fast_model
    if not config.ai.enabled or not fast_model:
        return collected, []

    client = _build_client(config.ai)
    notes: list[str] = []
    batch_items: list[SnapshotItem] = [
        item
        for payload in collected
        for item in payload.items
    ][:40]
    if not batch_items:
        return collected, notes

    prompt_items = [
        {
            "item_id": item.id,
            "title": item.title,
            "summary": item.summary,
            "source_name": item.source_name,
            "section": item.section,
        }
        for item in batch_items
    ]

    try:
        enrichment = _structured_completion(
            client,
            model=fast_model,
            system_prompt=(
                "You are a lightweight news classifier. "
                "For each item, classify whether it is hard_news, feature, opinion, analysis, explainer, or mixed. "
                "Estimate significance as high, medium, or low. "
                "Add compact topic and geography tags. "
                "Only include same_story_hints when there is a strong chance that another title in the batch refers to the same underlying event."
            ),
            user_prompt=(
                "Classify the following candidate briefing items for routing, clustering, and ranking. "
                "Keep outputs concise and structured. "
                f"Items: {json.dumps(prompt_items, default=str)}"
            ),
            model_class=BatchEnrichment,
        )
        enrichment_by_id = {item.item_id: item for item in enrichment.items}
        for payload in collected:
            for item in payload.items:
                enriched = enrichment_by_id.get(item.id)
                if enriched is None:
                    continue
                item.topics = sorted(set(item.topics + enriched.topics))
                item.geography = sorted(set(item.geography + enriched.geography))
                item.raw["content_type"] = enriched.content_type
                item.raw["significance_hint"] = enriched.significance
                item.raw["same_story_hints"] = enriched.same_story_hints
                item.raw["classifier_confidence"] = enriched.confidence
        notes.append(f"Fast-model enrichment applied with {fast_model}.")
    except (APIConnectionError, APIError, ValidationError, json.JSONDecodeError) as exc:
        notes.append(f"Fast-model enrichment skipped: {exc}")

    return collected, notes
