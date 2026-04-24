from __future__ import annotations

from datetime import datetime, timezone

from clu_core.models import CollectedSourceData, HomeLocation, SnapshotMetric, SourceAttribution

from .base import BaseConnector
from ..http_utils import get_json


US_STATE_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
}

WEATHER_CODE_LABELS = {
    0: "Clear",
    1: "Mostly Clear",
    2: "Partly Cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime Fog",
    51: "Light Drizzle",
    53: "Drizzle",
    55: "Heavy Drizzle",
    61: "Light Rain",
    63: "Rain",
    65: "Heavy Rain",
    71: "Light Snow",
    73: "Snow",
    75: "Heavy Snow",
    80: "Rain Showers",
    81: "Heavy Showers",
    82: "Violent Showers",
    95: "Thunderstorm",
    96: "Thunderstorm with Hail",
    99: "Severe Thunderstorm with Hail",
}


class OpenMeteoConnector(BaseConnector):
    def __init__(self, config, user_location: HomeLocation, user_timezone: str):
        super().__init__(config)
        self.user_location = user_location
        self.user_timezone = user_timezone

    def _uses_imperial_units(self) -> bool:
        parts = [part.strip() for part in self.user_location.label.split(",") if part.strip()]
        if len(parts) >= 2 and parts[-1].upper() in US_STATE_CODES:
            return True
        return self.user_timezone.startswith("America/")

    def _daily_params(self) -> dict[str, str | int | float]:
        params: dict[str, str | int | float] = {
            "latitude": self.user_location.latitude,
            "longitude": self.user_location.longitude,
            "daily": ",".join(self.config.params.get("daily", [])),
            "timezone": "auto",
            "forecast_days": 1,
        }
        if self._uses_imperial_units():
            params["temperature_unit"] = "fahrenheit"
            params["precipitation_unit"] = "inch"
            params["windspeed_unit"] = "mph"
        return params

    def _metric_payload(self, key: str, value, units: dict[str, str], timezone_name: str) -> SnapshotMetric:
        label_map = {
            "temperature_2m_max": "High",
            "temperature_2m_min": "Low",
            "precipitation_sum": "Precipitation",
            "weather_code": "Conditions",
        }
        unit = units.get(key)
        metric_value = str(value)
        if key == "weather_code":
            code = int(value)
            metric_value = WEATHER_CODE_LABELS.get(code, f"Code {code}")
            unit = None
        elif isinstance(value, float):
            metric_value = f"{value:.1f}".rstrip("0").rstrip(".")

        return SnapshotMetric(
            id=f"{self.config.id}-{key}",
            label=label_map.get(key, key),
            value=metric_value,
            unit=unit,
            source_id=self.config.id,
            section=self.config.section,
            raw={"timezone": timezone_name},
        )

    def fetch(self) -> CollectedSourceData:
        payload = get_json(
            "https://api.open-meteo.com/v1/forecast",
            params=self._daily_params(),
        )
        daily = payload.get("daily", {})
        daily_units = payload.get("daily_units", {})

        metrics = [
            self._metric_payload(key, values[0], daily_units, payload.get("timezone"))
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
