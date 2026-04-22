from __future__ import annotations

from datetime import datetime, timezone

import httpx

from clu_core.models import CollectedSourceData, SnapshotItem, SourceAttribution

from .base import BaseConnector


class GDELTConnector(BaseConnector):
    def fetch(self) -> CollectedSourceData:
        params = {
            "query": self.config.params.get("query", ""),
            "mode": "ArtList",
            "format": "json",
            "maxrecords": self.config.params.get("max_records", 10),
            "timespan": self.config.params.get("timespan", "1d"),
        }
        response = httpx.get(
            "https://api.gdeltproject.org/api/v2/doc/doc",
            params=params,
            timeout=20.0,
        )
        response.raise_for_status()
        data = response.json().get("articles", [])

        items = [
            SnapshotItem(
                id=entry["url"],
                title=entry.get("title", "Untitled"),
                summary=entry.get("seendate", ""),
                url=entry.get("url"),
                section=self.config.section,
                published_at=None,
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
                access_url="https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/",
                source_type=self.config.type,
                retrieved_at=datetime.now(timezone.utc),
            ),
            section=self.config.section,
            items=items,
        )

