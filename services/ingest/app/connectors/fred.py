from __future__ import annotations

import os
from datetime import datetime, timezone
from math import isclose

from clu_core.models import CollectedSourceData, SnapshotMetric, SourceAttribution

from .base import BaseConnector
from ..http_utils import get_json


class FREDConnector(BaseConnector):
    INDEX_UNIT_HIDDEN_SERIES = {"CPIAUCSL", "CPILFESL", "INDPRO"}
    MARKET_METADATA = {
        "DGS2": {"market_group": "US Rates & Energy", "market_region": "US", "display_order": 10},
        "DGS10": {"market_group": "US Rates & Energy", "market_region": "US", "display_order": 11},
        "DCOILBRENTEU": {"market_group": "US Rates & Energy", "market_region": "US", "display_order": 12},
        "DTWEXBGS": {"market_group": "Risk & Credit", "market_region": "US", "display_order": 20},
        "VIXCLS": {"market_group": "Risk & Credit", "market_region": "US", "display_order": 21},
        "BAMLH0A0HYM2": {"market_group": "Risk & Credit", "market_region": "US", "display_order": 22},
        "UST10Y2Y": {"market_group": "US Rates & Energy", "market_region": "US", "display_order": 13},
    }

    def _to_float(self, value: str | None) -> float | None:
        if value in {None, ".", ""}:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _format_number(self, value: float | None, *, unit: str | None = None) -> str | None:
        if value is None:
            return None
        if unit == "%":
            return f"{value:.2f}".rstrip("0").rstrip(".")
        if abs(value) >= 1000:
            return f"{value:,.0f}"
        if abs(value) >= 100:
            return f"{value:,.1f}".rstrip("0").rstrip(".")
        if abs(value) >= 10:
            return f"{value:.2f}".rstrip("0").rstrip(".")
        return f"{value:.3f}".rstrip("0").rstrip(".")

    def _freshness(self, metadata: dict, observation_date: str | None) -> str | None:
        if not observation_date:
            return None
        try:
            observed_at = datetime.fromisoformat(observation_date)
        except ValueError:
            return None
        age_days = (datetime.now(timezone.utc).date() - observed_at.date()).days
        frequency = str(metadata.get("frequency_short", "")).upper()
        if frequency == "D":
            return "fresh" if age_days <= 3 else ("recent" if age_days <= 7 else "stale")
        if frequency == "W":
            return "fresh" if age_days <= 8 else ("recent" if age_days <= 16 else "stale")
        if frequency == "M":
            return "fresh" if age_days <= 35 else ("recent" if age_days <= 60 else "stale")
        if frequency == "Q":
            return "fresh" if age_days <= 100 else ("recent" if age_days <= 140 else "stale")
        return "recent" if age_days <= 30 else "stale"

    def _series_specs(self) -> list[dict]:
        specs: list[dict] = []
        for raw in self.config.params.get("series", []):
            if isinstance(raw, str):
                specs.append({"id": raw})
            elif isinstance(raw, dict) and raw.get("id"):
                specs.append(raw)
        return specs

    def _series_metadata(self, api_key: str, series_id: str) -> dict:
        payload = get_json(
            "https://api.stlouisfed.org/fred/series",
            params={
                "series_id": series_id,
                "api_key": api_key,
                "file_type": "json",
            },
        )
        series_rows = payload.get("seriess", [])
        return series_rows[0] if series_rows else {}

    def _series_observations(self, api_key: str, series_id: str) -> list[dict]:
        observations = get_json(
            "https://api.stlouisfed.org/fred/series/observations",
            params={
                "series_id": series_id,
                "api_key": api_key,
                "file_type": "json",
                "sort_order": "desc",
                "limit": 16,
            },
        ).get("observations", [])
        return [row for row in observations if self._to_float(row.get("value")) is not None]

    def _display_unit(self, series_id: str, unit: str | None) -> str | None:
        if series_id in self.INDEX_UNIT_HIDDEN_SERIES:
            return None
        return unit

    def _derived_metrics(self, metrics_by_series_id: dict[str, SnapshotMetric]) -> list[SnapshotMetric]:
        derived: list[SnapshotMetric] = []
        ten_year = metrics_by_series_id.get("DGS10")
        two_year = metrics_by_series_id.get("DGS2")
        if ten_year and two_year:
            latest_10 = self._to_float(ten_year.raw.get("latest", {}).get("value"))
            latest_2 = self._to_float(two_year.raw.get("latest", {}).get("value"))
            previous_10 = self._to_float(ten_year.raw.get("previous", {}).get("value"))
            previous_2 = self._to_float(two_year.raw.get("previous", {}).get("value"))
            if latest_10 is not None and latest_2 is not None:
                spread = latest_10 - latest_2
                previous_spread = (
                    previous_10 - previous_2
                    if previous_10 is not None and previous_2 is not None
                    else None
                )
                spread_change = None
                spread_trend = "flat"
                if previous_spread is not None:
                    delta = spread - previous_spread
                    spread_change = f"{delta:+.2f}"
                    if isclose(delta, 0.0, abs_tol=0.005):
                        spread_trend = "flat"
                    else:
                        spread_trend = "up" if delta > 0 else "down"
                derived.append(
                    SnapshotMetric(
                        id=f"{self.config.id}-UST10Y2Y",
                        label="2s10s Treasury Spread",
                        value=self._format_number(spread, unit="%") or f"{spread:.2f}",
                        previous_value=self._format_number(previous_spread, unit="%"),
                        unit="pp",
                        change=spread_change,
                        trend=spread_trend,
                        freshness=ten_year.freshness or two_year.freshness,
                        source_id=self.config.id,
                        section="markets",
                        context=ten_year.context or two_year.context,
                        raw={
                            "derived_from": ["DGS10", "DGS2"],
                            "latest_spread": spread,
                            "previous_spread": previous_spread,
                            **self.MARKET_METADATA["UST10Y2Y"],
                        },
                    )
                )
        return derived

    def fetch(self) -> CollectedSourceData:
        api_key = os.getenv(self.config.params["api_key_env"], "")
        if not api_key:
            return CollectedSourceData(
                source=SourceAttribution(
                    source_id=self.config.id,
                    display_name=self.config.display_name,
                    access_url="https://fred.stlouisfed.org/docs/api/fred/overview.html",
                    source_type=self.config.type,
                    retrieved_at=datetime.now(timezone.utc),
                    notes="Skipped because API key was not configured.",
                ),
                section=self.config.section,
                notes=["Missing FRED API key."],
            )

        metrics: list[SnapshotMetric] = []
        metrics_by_series_id: dict[str, SnapshotMetric] = {}
        for spec in self._series_specs():
            series_id = spec["id"]
            metadata = self._series_metadata(api_key, series_id)
            observations = self._series_observations(api_key, series_id)
            if not observations:
                continue

            latest = observations[0]
            previous = observations[1] if len(observations) > 1 else None
            latest_numeric = self._to_float(latest.get("value"))
            previous_numeric = self._to_float(previous.get("value")) if previous else None
            if latest_numeric is None:
                continue

            unit = spec.get("unit") or metadata.get("units_short") or metadata.get("units")
            display_unit = self._display_unit(series_id, unit)
            latest_value = self._format_number(latest_numeric, unit=unit) or latest.get("value", ".")
            previous_value = self._format_number(previous_numeric, unit=unit) if previous else None
            change = None
            change_percent = None
            trend = None
            if previous_numeric is not None:
                delta = latest_numeric - previous_numeric
                if unit == "%":
                    change = f"{delta:+.2f}"
                else:
                    change = self._format_number(delta, unit=unit)
                    if change and not change.startswith("-"):
                        change = f"+{change}"
                if previous_numeric and not isclose(previous_numeric, 0.0, abs_tol=1e-9):
                    change_percent = f"{(delta / previous_numeric) * 100:+.2f}%"
                trend = "up" if delta > 0 else ("down" if delta < 0 else "flat")

            label = spec.get("label") or metadata.get("title") or series_id
            if series_id in {"CPIAUCSL", "CPILFESL"} and previous_numeric not in {None, 0.0}:
                month_over_month = ((latest_numeric / previous_numeric) - 1.0) * 100
                change = f"MoM {month_over_month:+.2f}%"
                year_ago = self._to_float(observations[12].get("value")) if len(observations) > 12 else None
                if year_ago not in {None, 0.0}:
                    year_over_year = ((latest_numeric / year_ago) - 1.0) * 100
                    change_percent = f"YoY {year_over_year:+.2f}%"
                else:
                    change_percent = None
            elif series_id == "PAYEMS" and previous_numeric is not None:
                jobs_delta = int(round((latest_numeric - previous_numeric) * 1000))
                label = "Nonfarm Payroll Change"
                latest_value = f"{jobs_delta:+,}"
                previous_value = None
                display_unit = "jobs"
                change = None
                change_percent = None
                trend = "up" if jobs_delta > 0 else ("down" if jobs_delta < 0 else "flat")
            elif series_id == "RSAFS":
                latest_value = f"${latest_numeric:,.0f}"
                previous_value = f"${previous_numeric:,.0f}" if previous_numeric is not None else None
                display_unit = None
                if previous_numeric is not None:
                    delta = latest_numeric - previous_numeric
                    change = f"${delta:+,.0f}"
                    if previous_numeric and not isclose(previous_numeric, 0.0, abs_tol=1e-9):
                        change_percent = f"{(delta / previous_numeric) * 100:+.2f}%"

            metric = SnapshotMetric(
                id=f"{self.config.id}-{series_id}",
                label=label,
                value=latest_value,
                previous_value=previous_value,
                unit=display_unit,
                change=change,
                change_percent=change_percent,
                trend=trend,
                freshness=self._freshness(metadata, latest.get("date")),
                source_id=self.config.id,
                section=spec.get("section", self.config.section),
                context=latest.get("date"),
                raw={
                    "series_id": series_id,
                    "latest": latest,
                    "previous": previous,
                    "metadata": metadata,
                    **self.MARKET_METADATA.get(series_id, {}),
                },
            )
            metrics.append(metric)
            metrics_by_series_id[series_id] = metric

        metrics.extend(self._derived_metrics(metrics_by_series_id))

        return CollectedSourceData(
            source=SourceAttribution(
                source_id=self.config.id,
                display_name=self.config.display_name,
                access_url="https://fred.stlouisfed.org/docs/api/fred/overview.html",
                source_type=self.config.type,
                retrieved_at=datetime.now(timezone.utc),
            ),
            section=self.config.section,
            metrics=metrics,
        )
