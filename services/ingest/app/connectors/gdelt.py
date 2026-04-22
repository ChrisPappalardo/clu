from __future__ import annotations

from datetime import datetime, timezone

from clu_core.models import CollectedSourceData, SnapshotItem, SourceAttribution

from .base import BaseConnector
from ..http_utils import get_json


class GDELTConnector(BaseConnector):
    def fetch(self) -> CollectedSourceData:
        params = {
            "query": self.config.params.get("query", ""),
            "mode": "ArtList",
            "format": "json",
            "maxrecords": self.config.params.get("max_records", 10),
            "timespan": self.config.params.get("timespan", "1d"),
        }
        data = get_json(
            "https://api.gdeltproject.org/api/v2/doc/doc",
            params=params,
        ).get("articles", [])

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
