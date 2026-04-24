from __future__ import annotations

from datetime import datetime, timezone

import yfinance as yf

from clu_core.models import CollectedSourceData, SnapshotMetric, SourceAttribution

from .base import BaseConnector


class YFinanceMarketsConnector(BaseConnector):
    def _format_price(self, value: float | None) -> str:
        if value is None:
            return "n/a"
        if abs(value) >= 1000:
            return f"{value:,.0f}"
        if abs(value) >= 100:
            return f"{value:,.1f}".rstrip("0").rstrip(".")
        if abs(value) >= 10:
            return f"{value:,.2f}".rstrip("0").rstrip(".")
        return f"{value:,.3f}".rstrip("0").rstrip(".")

    def _symbol_specs(self) -> list[dict]:
        specs: list[dict] = []
        for raw in self.config.params.get("symbols", []):
            if isinstance(raw, str):
                specs.append({"symbol": raw})
            elif isinstance(raw, dict) and raw.get("symbol"):
                specs.append(raw)
        return specs

    def fetch(self) -> CollectedSourceData:
        specs = self._symbol_specs()
        if not specs:
            return CollectedSourceData(
                source=SourceAttribution(
                    source_id=self.config.id,
                    display_name=self.config.display_name,
                    access_url="https://finance.yahoo.com/",
                    source_type=self.config.type,
                    retrieved_at=datetime.now(timezone.utc),
                    notes="No symbols configured.",
                ),
                section=self.config.section,
                notes=["No Yahoo Finance symbols configured."],
            )

        symbols = [spec["symbol"] for spec in specs]
        history = yf.download(
            tickers=symbols,
            period=self.config.params.get("period", "7d"),
            interval=self.config.params.get("interval", "1d"),
            auto_adjust=False,
            progress=False,
            threads=False,
        )

        metrics: list[SnapshotMetric] = []
        close_frame = history.get("Close")
        if close_frame is None:
            close_frame = history
        if hasattr(close_frame, "name") and getattr(close_frame, "name", None) == "Close" and len(symbols) == 1:
            close_frame = close_frame.to_frame(name=symbols[0])

        for order, spec in enumerate(specs):
            symbol = spec["symbol"]
            if symbol not in close_frame:
                continue
            closes = close_frame[symbol].dropna()
            if closes.empty:
                continue

            latest_numeric = float(closes.iloc[-1])
            previous_numeric = float(closes.iloc[-2]) if len(closes) > 1 else None
            latest_date = closes.index[-1]
            latest_value = self._format_price(latest_numeric)
            previous_value = self._format_price(previous_numeric) if previous_numeric is not None else None

            change = None
            change_percent = None
            trend = None
            if previous_numeric is not None:
                delta = latest_numeric - previous_numeric
                change = f"{delta:+.2f}"
                if abs(previous_numeric) > 1e-9:
                    change_percent = f"{(delta / previous_numeric) * 100:+.2f}%"
                trend = "up" if delta > 0 else ("down" if delta < 0 else "flat")

            unit = spec.get("unit")
            if unit == "index":
                unit = None
            if unit == "USD":
                latest_value = f"${latest_value}"
                if previous_value is not None:
                    previous_value = f"${previous_value}"
                if change is not None:
                    change = f"${float(change):+,.2f}".rstrip("0").rstrip(".")
                unit = None

            metrics.append(
                SnapshotMetric(
                    id=f"{self.config.id}-{symbol}",
                    label=spec.get("label") or symbol,
                    value=latest_value,
                    previous_value=previous_value,
                    unit=unit,
                    change=change,
                    change_percent=change_percent,
                    trend=trend,
                    freshness="fresh",
                    source_id=self.config.id,
                    section=spec.get("section", self.config.section),
                    context=str(latest_date.date()),
                    raw={
                        "symbol": symbol,
                        "display_order": spec.get("display_order", order),
                        "market_group": spec.get("market_group"),
                        "market_region": spec.get("market_region"),
                    },
                )
            )

        return CollectedSourceData(
            source=SourceAttribution(
                source_id=self.config.id,
                display_name=self.config.display_name,
                access_url="https://finance.yahoo.com/",
                source_type=self.config.type,
                retrieved_at=datetime.now(timezone.utc),
            ),
            section=self.config.section,
            metrics=metrics,
        )
