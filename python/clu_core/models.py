from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl


class HomeLocation(BaseModel):
    label: str
    latitude: float
    longitude: float


class DeliveryConfig(BaseModel):
    store_html_report: bool = True
    store_json_report: bool = True
    generate_email_friendly_html: bool = True


class UserConfig(BaseModel):
    timezone: str
    home_location: HomeLocation
    delivery: DeliveryConfig = Field(default_factory=DeliveryConfig)


class ToneConfig(BaseModel):
    style: str = "concise"
    viewpoint: str = "neutral"
    interpretation_level: str = "high"


class BriefingPriorities(BaseModel):
    geography: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)


class BriefingConfig(BaseModel):
    max_headlines_per_section: int = 6
    max_sections: int = 6
    include_sections: list[str] = Field(default_factory=list)
    priorities: BriefingPriorities = Field(default_factory=BriefingPriorities)
    tone: ToneConfig = Field(default_factory=ToneConfig)


class AIConfig(BaseModel):
    provider: str = "openai"
    model: str = "gpt-5-mini"
    fast_model: str | None = None
    enabled: bool = True
    max_input_items_per_section: int = 12
    history_window_days: int = 7
    base_url: str | None = None
    api_key_env: str = "OPENAI_API_KEY"


class SourceConfig(BaseModel):
    id: str
    type: str
    enabled: bool = True
    section: str
    display_name: str
    params: dict[str, Any] = Field(default_factory=dict)


class AppConfig(BaseModel):
    user: UserConfig
    briefing: BriefingConfig
    ai: AIConfig = Field(default_factory=AIConfig)
    sources: list[SourceConfig] = Field(default_factory=list)


class SourceAttribution(BaseModel):
    source_id: str
    display_name: str
    access_url: str | None = None
    source_type: str
    retrieved_at: datetime
    notes: str | None = None


class SnapshotItem(BaseModel):
    id: str
    title: str
    summary: str
    url: HttpUrl | None = None
    section: str
    published_at: datetime | None = None
    source_id: str
    source_name: str
    geography: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    importance_score: float = 0.0
    novelty_score: float = 0.0
    cluster_key: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class SnapshotMetric(BaseModel):
    id: str
    label: str
    value: str
    unit: str | None = None
    change: str | None = None
    trend: Literal["up", "down", "flat", "mixed"] | None = None
    source_id: str
    section: str
    context: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class StoryCluster(BaseModel):
    id: str
    section: str
    title: str
    summary: str
    what_changed: str | None = None
    why_now: str | None = None
    why_it_matters: str
    risk_level: Literal["high", "medium", "low"] | None = None
    risk_summary: str | None = None
    importance_score: float
    novelty_score: float
    significance: Literal["high", "medium", "low"]
    item_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    source_names: list[str] = Field(default_factory=list)
    geography: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    watch_points: list[str] = Field(default_factory=list)
    developments: list[str] = Field(default_factory=list)
    related_previous_cluster_ids: list[str] = Field(default_factory=list)


class CollectedSourceData(BaseModel):
    source: SourceAttribution
    section: str
    items: list[SnapshotItem] = Field(default_factory=list)
    metrics: list[SnapshotMetric] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class SnapshotSection(BaseModel):
    id: str
    title: str
    kind: Literal["news", "data", "mixed"]
    summary: str
    narrative: str | None = None
    what_changed: str | None = None
    why_now: str | None = None
    risk_summary: str | None = None
    items: list[SnapshotItem] = Field(default_factory=list)
    metrics: list[SnapshotMetric] = Field(default_factory=list)
    clusters: list[StoryCluster] = Field(default_factory=list)


class WatchItem(BaseModel):
    label: str
    note: str
    section_id: str | None = None


class BriefingMemory(BaseModel):
    prior_snapshot_id: str | None = None
    prior_snapshot_date: str | None = None
    continuing_cluster_ids: list[str] = Field(default_factory=list)
    newly_emerged_cluster_ids: list[str] = Field(default_factory=list)
    dropped_cluster_ids: list[str] = Field(default_factory=list)
    continuity_note: str | None = None


class DailySnapshot(BaseModel):
    snapshot_id: str
    snapshot_date: str
    generated_at: datetime
    timezone: str
    lead_summary: str
    what_changed_summary: str | None = None
    outlook: str | None = None
    risk_summary: str | None = None
    themes: list[str] = Field(default_factory=list)
    top_story_ids: list[str] = Field(default_factory=list)
    watch_items: list[WatchItem] = Field(default_factory=list)
    sections: list[SnapshotSection] = Field(default_factory=list)
    clusters: list[StoryCluster] = Field(default_factory=list)
    memory: BriefingMemory = Field(default_factory=BriefingMemory)
    source_attributions: list[SourceAttribution] = Field(default_factory=list)
    generation_notes: list[str] = Field(default_factory=list)
