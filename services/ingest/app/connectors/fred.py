from __future__ import annotations

import os
from datetime import datetime, timezone

from clu_core.models import CollectedSourceData, SnapshotMetric, SourceAttribution

from .base import BaseConnector
from ..http_utils import get_json


class FREDConnector(BaseConnector):
    def fetch(self) -> CollectedSourceData:
        api_key = os.getenv(self.config.params["api_key_env"], "")
        if not api_key:
            return CollectedSourceData(
                source=SourceAttribution(
                    source_id=self.config.id,
                    display_name=self.config.display_name,
                    access_url="https://fred.stlouisfed.org/docs/api/fred/overview.html",
                    source_type=self.config.type,
                    retrieved_at=datetime.now(timezone.utc),
                    notes="Skipped because API key was not configured.",
                ),
                section=self.config.section,
                notes=["Missing FRED API key."],
            )

        metrics: list[SnapshotMetric] = []
        for series_id in self.config.params.get("series", []):
            observations = get_json(
                "https://api.stlouisfed.org/fred/series/observations",
                params={
                    "series_id": series_id,
                    "api_key": api_key,
                    "file_type": "json",
                    "sort_order": "desc",
                    "limit": 2,
                },
            ).get("observations", [])
            if not observations:
                continue
            latest = observations[0]
            previous = observations[1] if len(observations) > 1 else None
            change = None
            if previous and latest["value"] != "." and previous["value"] != ".":
                try:
                    change = f"{float(latest['value']) - float(previous['value']):.2f}"
                except ValueError:
                    change = None
            metrics.append(
                SnapshotMetric(
                    id=f"{self.config.id}-{series_id}",
                    label=series_id,
                    value=latest["value"],
                    change=change,
                    source_id=self.config.id,
                    section=self.config.section,
                    raw=latest,
                )
            )

        return CollectedSourceData(
            source=SourceAttribution(
                source_id=self.config.id,
                display_name=self.config.display_name,
                access_url="https://fred.stlouisfed.org/docs/api/fred/overview.html",
                source_type=self.config.type,
                retrieved_at=datetime.now(timezone.utc),
            ),
            section=self.config.section,
            metrics=metrics,
        )
