from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from html import unescape

from clu_core.models import CollectedSourceData, SnapshotItem, SourceAttribution

from .base import BaseConnector
from .filtering import matches_regex_patterns, matches_substring_patterns
from ..http_utils import get_json


class GuardianConnector(BaseConnector):
    def _clean_text(self, value: str) -> str:
        cleaned = unescape(value)
        cleaned = re.sub(r"<[^>]+>", " ", cleaned)
        return re.sub(r"\s+", " ", cleaned).strip()

    def _is_allowed_entry(self, entry: dict) -> bool:
        title = entry.get("webTitle", "")
        url = entry.get("webUrl", "")
        content_type = str(entry.get("type", "")).lower()
        exclude_content_types = {
            value.lower() for value in self.config.params.get("exclude_content_types", [])
        }
        if content_type in exclude_content_types:
            return False
        if matches_regex_patterns(title, self.config.params.get("exclude_title_patterns", [])):
            return False
        if matches_substring_patterns(url, self.config.params.get("exclude_url_patterns", [])):
            return False
        return True

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
            "section": self.config.params.get("section", ""),
            "page-size": self.config.params.get("page_size", 10),
            "show-fields": "trailText,headline",
            "order-by": "newest",
        }
        data = [
            entry
            for entry in get_json(
                "https://content.guardianapis.com/search",
                params=params,
            )["response"]["results"]
            if self._is_allowed_entry(entry)
        ]

        items = [
            SnapshotItem(
                id=entry["id"],
                title=self._clean_text(entry["webTitle"]),
                summary=self._clean_text(entry.get("fields", {}).get("trailText", "")),
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
