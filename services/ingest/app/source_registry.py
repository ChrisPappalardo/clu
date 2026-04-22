from __future__ import annotations

from clu_core.models import HomeLocation, SourceConfig

from .connectors.alpha_vantage import AlphaVantageConnector
from .connectors.fred import FREDConnector
from .connectors.gdelt import GDELTConnector
from .connectors.guardian import GuardianConnector
from .connectors.open_meteo import OpenMeteoConnector
from .connectors.rss import RSSConnector
from .connectors.usgs import USGSConnector
from .connectors.world_bank import WorldBankConnector


def build_connector(config: SourceConfig, home_location: HomeLocation):
    if config.type == "rss":
        return RSSConnector(config)
    if config.type == "guardian":
        return GuardianConnector(config)
    if config.type == "gdelt":
        return GDELTConnector(config)
    if config.type == "fred":
        return FREDConnector(config)
    if config.type == "world_bank":
        return WorldBankConnector(config)
    if config.type == "open_meteo":
        return OpenMeteoConnector(config, home_location)
    if config.type == "usgs":
        return USGSConnector(config)
    if config.type == "alpha_vantage":
        return AlphaVantageConnector(config)
    raise ValueError(f"Unsupported source type: {config.type}")

