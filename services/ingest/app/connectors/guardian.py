from __future__ import annotations

import os
from datetime import datetime, timezone

import httpx

from clu_core.models import CollectedSourceData, SnapshotItem, SourceAttribution

from .base import BaseConnector


class GuardianConnector(BaseConnector):
    def fetch(self) -> CollectedSourceData:
        api_key = os.getenv(self.config.params["api_key_env"], "")
        if not api_key:
            return CollectedSourceData(
                source=SourceAttribution(
                    source_id=self.config.id,
                    display_name=self.config.display_name,
                    access_url="https://open-platform.theguardian.com/documentation/",
                    source_type=self.config.type,
                    retrieved_at=datetime.now(timezone.utc),
                    notes="Skipped because API key was not configured.",
                ),
                section=self.config.section,
                notes=["Missing Guardian API key."],
            )

        params = {
            "api-key": api_key,
            "q": self.config.params.get("query", ""),
            "page-size": self.config.params.get("page_size", 10),
            "show-fields": "trailText,headline",
            "order-by": "newest",
        }
        response = httpx.get(
            "https://content.guardianapis.com/search",
            params=params,
            timeout=20.0,
        )
        response.raise_for_status()
        data = response.json()["response"]["results"]

        items = [
            SnapshotItem(
                id=entry["id"],
                title=entry["webTitle"],
                summary=entry.get("fields", {}).get("trailText", ""),
                url=entry["webUrl"],
                section=self.config.section,
                published_at=datetime.fromisoformat(
                    entry["webPublicationDate"].replace("Z", "+00:00")
                ),
                source_id=self.config.id,
                source_name=self.config.display_name,
                raw=entry,
            )
            for entry in data
        ]

        return CollectedSourceData(
            source=SourceAttribution(
                source_id=self.config.id,
                display_name=self.config.display_name,
                access_url="https://open-platform.theguardian.com/documentation/",
                source_type=self.config.type,
                retrieved_at=datetime.now(timezone.utc),
            ),
            section=self.config.section,
            items=items,
        )

