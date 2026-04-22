from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import feedparser

from clu_core.models import CollectedSourceData, SnapshotItem, SourceAttribution

from .base import BaseConnector


class RSSConnector(BaseConnector):
    def fetch(self) -> CollectedSourceData:
        feed_url = self.config.params["feed_url"]
        max_items = int(self.config.params.get("max_items", 10))
        parsed = feedparser.parse(feed_url)

        items: list[SnapshotItem] = []
        for entry in parsed.entries[:max_items]:
            published = None
            if getattr(entry, "published_parsed", None):
                published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            items.append(
                SnapshotItem(
                    id=f"{self.config.id}-{uuid4()}",
                    title=entry.get("title", "Untitled"),
                    summary=entry.get("summary", "")[:600],
                    url=entry.get("link"),
                    section=self.config.section,
                    published_at=published,
                    source_id=self.config.id,
                    source_name=self.config.display_name,
                    raw={"feed_url": feed_url},
                )
            )

        return CollectedSourceData(
            source=SourceAttribution(
                source_id=self.config.id,
                display_name=self.config.display_name,
                access_url=feed_url,
                source_type=self.config.type,
                retrieved_at=datetime.now(timezone.utc),
            ),
            section=self.config.section,
            items=items,
        )

