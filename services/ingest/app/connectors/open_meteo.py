from __future__ import annotations

from datetime import datetime, timezone

import httpx

from clu_core.models import CollectedSourceData, SnapshotMetric, SourceAttribution

from .base import BaseConnector


class OpenMeteoConnector(BaseConnector):
    def __init__(self, config, user_location):
        super().__init__(config)
        self.user_location = user_location

    def fetch(self) -> CollectedSourceData:
        response = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": self.user_location.latitude,
                "longitude": self.user_location.longitude,
                "daily": ",".join(self.config.params.get("daily", [])),
                "timezone": "auto",
                "forecast_days": 1,
            },
            timeout=20.0,
        )
        response.raise_for_status()
        payload = response.json()
        daily = payload.get("daily", {})

        metrics = [
            SnapshotMetric(
                id=f"{self.config.id}-{key}",
                label=key,
                value=str(values[0]),
                source_id=self.config.id,
                section=self.config.section,
                raw={"timezone": payload.get("timezone")},
            )
            for key, values in daily.items()
            if key != "time" and values
        ]

        return CollectedSourceData(
            source=SourceAttribution(
                source_id=self.config.id,
                display_name=self.config.display_name,
                access_url="https://open-meteo.com/en/docs",
                source_type=self.config.type,
                retrieved_at=datetime.now(timezone.utc),
            ),
            section=self.config.section,
            metrics=metrics,
        )

