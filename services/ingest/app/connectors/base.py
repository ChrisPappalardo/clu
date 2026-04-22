from __future__ import annotations

from abc import ABC, abstractmethod

from clu_core.models import CollectedSourceData, SourceConfig


class BaseConnector(ABC):
    def __init__(self, config: SourceConfig):
        self.config = config

    @abstractmethod
    def fetch(self) -> CollectedSourceData:
        raise NotImplementedError

