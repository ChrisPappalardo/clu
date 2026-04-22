from __future__ import annotations

from datetime import datetime, timezone

from clu_core.models import CollectedSourceData, SnapshotItem, SourceAttribution

from .base import BaseConnector
from ..http_utils import get_json


USGS_FEEDS = {
    "significant_day": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_day.geojson",
    "significant_week": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_week.geojson",
}


class USGSConnector(BaseConnector):
    def fetch(self) -> CollectedSourceData:
        feed_name = self.config.params.get("feed", "significant_day")
        feed_url = USGS_FEEDS[feed_name]
        payload = get_json(feed_url)

        items = [
            SnapshotItem(
                id=feature["id"],
                title=feature["properties"]["title"],
                summary=feature["properties"].get("place", ""),
                url=feature["properties"].get("url"),
                section=self.config.section,
                published_at=datetime.fromtimestamp(
                    feature["properties"]["time"] / 1000,
                    tz=timezone.utc,
                ),
                source_id=self.config.id,
                source_name=self.config.display_name,
                raw=feature,
            )
            for feature in payload.get("features", [])
        ]

        return CollectedSourceData(
            source=SourceAttribution(
                source_id=self.config.id,
                display_name=self.config.display_name,
                access_url="https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php",
                source_type=self.config.type,
                retrieved_at=datetime.now(timezone.utc),
            ),
            section=self.config.section,
            items=items,
        )
