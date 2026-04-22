from __future__ import annotations

import os
from datetime import datetime, timezone

import httpx

from clu_core.models import CollectedSourceData, SnapshotMetric, SourceAttribution

from .base import BaseConnector


class AlphaVantageConnector(BaseConnector):
    def fetch(self) -> CollectedSourceData:
        api_key = os.getenv(self.config.params["api_key_env"], "")
        if not api_key:
            return CollectedSourceData(
                source=SourceAttribution(
                    source_id=self.config.id,
                    display_name=self.config.display_name,
                    access_url="https://www.alphavantage.co/documentation/",
                    source_type=self.config.type,
                    retrieved_at=datetime.now(timezone.utc),
                    notes="Skipped because API key was not configured.",
                ),
                section=self.config.section,
                notes=["Missing Alpha Vantage API key."],
            )

        metrics: list[SnapshotMetric] = []
        for fn in self.config.params.get("functions", []):
            response = httpx.get(
                "https://www.alphavantage.co/query",
                params={"apikey": api_key, **fn},
                timeout=20.0,
            )
            response.raise_for_status()
            payload = response.json()
            for key in ("top_gainers", "top_losers", "most_actively_traded"):
                for row in payload.get(key, [])[:3]:
                    metrics.append(
                        SnapshotMetric(
                            id=f"{self.config.id}-{key}-{row['ticker']}",
                            label=f"{key} {row['ticker']}",
                            value=row.get("price", "n/a"),
                            change=row.get("change_percentage"),
                            source_id=self.config.id,
                            section=self.config.section,
                            raw=row,
                        )
                    )

        return CollectedSourceData(
            source=SourceAttribution(
                source_id=self.config.id,
                display_name=self.config.display_name,
                access_url="https://www.alphavantage.co/documentation/",
                source_type=self.config.type,
                retrieved_at=datetime.now(timezone.utc),
            ),
            section=self.config.section,
            metrics=metrics,
        )

