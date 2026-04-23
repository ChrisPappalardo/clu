from __future__ import annotations

import json
import os
from typing import Literal, TypeVar

from openai import OpenAI
from openai import APIConnectionError, APIError
from pydantic import BaseModel, Field
from pydantic import ValidationError
from pydantic import field_validator

from clu_core.models import AIConfig, AppConfig, CollectedSourceData, SnapshotItem


CONTENT_TYPE_SYNONYMS = {
    "news": "hard_news",
    "hard news": "hard_news",
    "hard_news": "hard_news",
    "analysis": "analysis",
    "analytical": "analysis",
    "explainer": "explainer",
    "explanation": "explainer",
    "feature": "feature",
    "opinion": "opinion",
    "editorial": "opinion",
    "mixed": "mixed",
}

SIGNIFICANCE_SYNONYMS = {
    "high": "high",
    "medium": "medium",
    "med": "medium",
    "moderate": "medium",
    "low": "low",
}


class ItemEnrichment(BaseModel):
    item_id: str
    content_type: Literal["hard_news", "analysis", "explainer", "feature", "opinion", "mixed"]
    significance: Literal["high", "medium", "low"]
    topics: list[str] = Field(default_factory=list)
    geography: list[str] = Field(default_factory=list)
    confidence: float = 0.0

    @field_validator("content_type", mode="before")
    @classmethod
    def _normalize_content_type(cls, value: str) -> str:
        normalized = CONTENT_TYPE_SYNONYMS.get(str(value).strip().lower())
        if normalized is None:
            raise ValueError(f"Unsupported content_type: {value}")
        return normalized

    @field_validator("significance", mode="before")
    @classmethod
    def _normalize_significance(cls, value: str) -> str:
        normalized = SIGNIFICANCE_SYNONYMS.get(str(value).strip().lower())
        if normalized is None:
            raise ValueError(f"Unsupported significance: {value}")
        return normalized

    @field_validator("topics", "geography", mode="before")
    @classmethod
    def _normalize_tags(cls, value):
        if not value:
            return []
        cleaned: list[str] = []
        for entry in value:
            normalized = str(entry).strip()
            if not normalized:
                continue
            cleaned.append(normalized[:48])
            if len(cleaned) >= 3:
                break
        return cleaned

    @field_validator("confidence", mode="before")
    @classmethod
    def _normalize_confidence(cls, value) -> float:
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(confidence, 1.0))


class EnrichmentChunk(BaseModel):
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


def _chunked(items: list[SnapshotItem], size: int) -> list[list[SnapshotItem]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


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
    ][:48]
    if not batch_items:
        return collected, notes

    enrichment_by_id: dict[str, ItemEnrichment] = {}
    try:
        for chunk in _chunked(batch_items, 8):
            prompt_items = [
                {
                    "item_id": item.id,
                    "title": item.title,
                    "summary": item.summary,
                    "source_name": item.source_name,
                    "section": item.section,
                }
                for item in chunk
            ]
            enrichment = _structured_completion(
                client,
                model=fast_model,
                system_prompt=(
                    "You are a lightweight news classifier for a morning briefing system. "
                    "For each item, classify content_type as one of: hard_news, analysis, explainer, feature, opinion, mixed. "
                    "Estimate significance as high, medium, or low. "
                    "Add up to 3 concise topic tags and up to 2 concise geography tags. "
                    "Be conservative: feature or opinion is better than falsely calling something hard_news."
                ),
                user_prompt=(
                    "Classify these briefing candidates for ranking and filtering. "
                    "Return one result per item_id. "
                    f"Items: {json.dumps(prompt_items, default=str)}"
                ),
                model_class=EnrichmentChunk,
            )
            for item in enrichment.items:
                enrichment_by_id[item.item_id] = item
        for payload in collected:
            for item in payload.items:
                enriched = enrichment_by_id.get(item.id)
                if enriched is None:
                    continue
                item.topics = sorted(set(item.topics + enriched.topics))
                item.geography = sorted(set(item.geography + enriched.geography))
                item.raw["content_type"] = enriched.content_type
                item.raw["significance_hint"] = enriched.significance
                item.raw["classifier_confidence"] = enriched.confidence
        notes.append(f"Fast-model enrichment applied with {fast_model} to {len(enrichment_by_id)} items.")
    except (APIConnectionError, APIError, ValidationError, json.JSONDecodeError) as exc:
        notes.append(f"Fast-model enrichment skipped: {exc}")

    return collected, notes
