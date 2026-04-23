from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import feedparser

from clu_core.models import CollectedSourceData, SnapshotItem, SourceAttribution

from .base import BaseConnector
from .filtering import matches_regex_patterns, matches_substring_patterns


class RSSConnector(BaseConnector):
    def _is_allowed_entry(self, entry) -> bool:
        title = entry.get("title", "")
        link = entry.get("link", "")
        include_title_patterns = self.config.params.get("include_title_patterns", [])
        include_url_patterns = self.config.params.get("include_url_patterns", [])
        exclude_title_patterns = self.config.params.get("exclude_title_patterns", [])
        exclude_url_patterns = self.config.params.get("exclude_url_patterns", [])
        if include_title_patterns and not matches_regex_patterns(title, include_title_patterns):
            return False
        if include_url_patterns and not matches_substring_patterns(link, include_url_patterns):
            return False
        if matches_regex_patterns(title, exclude_title_patterns):
            return False
        if matches_substring_patterns(link, exclude_url_patterns):
            return False
        return True

    def fetch(self) -> CollectedSourceData:
        feed_url = self.config.params["feed_url"]
        max_items = int(self.config.params.get("max_items", 10))
        parsed = feedparser.parse(feed_url)

        items: list[SnapshotItem] = []
        for entry in parsed.entries:
            if not self._is_allowed_entry(entry):
                continue
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
            if len(items) >= max_items:
                break

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
