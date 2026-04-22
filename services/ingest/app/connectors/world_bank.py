from __future__ import annotations

from datetime import datetime, timezone

from clu_core.models import CollectedSourceData, SnapshotMetric, SourceAttribution

from .base import BaseConnector
from ..http_utils import get_json


class WorldBankConnector(BaseConnector):
    def fetch(self) -> CollectedSourceData:
        metrics: list[SnapshotMetric] = []
        for spec in self.config.params.get("indicators", []):
            code = spec["code"]
            countries = spec["countries"]
            payload = get_json(
                f"https://api.worldbank.org/v2/country/{countries}/indicator/{code}",
                params={"format": "json", "mrv": 1},
                retries=3,
            )
            for row in payload[1] if len(payload) > 1 else []:
                if row.get("value") is None:
                    continue
                metrics.append(
                    SnapshotMetric(
                        id=f"{self.config.id}-{code}-{row['country']['id']}",
                        label=f"{row['country']['value']} {row['indicator']['value']}",
                        value=str(row["value"]),
                        source_id=self.config.id,
                        section=self.config.section,
                        context=row.get("date"),
                        raw=row,
                    )
                )

        return CollectedSourceData(
            source=SourceAttribution(
                source_id=self.config.id,
                display_name=self.config.display_name,
                access_url="https://datahelpdesk.worldbank.org/knowledgebase/articles/898581-api-basic-call-structures",
                source_type=self.config.type,
                retrieved_at=datetime.now(timezone.utc),
            ),
            section=self.config.section,
            metrics=metrics,
        )
