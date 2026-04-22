from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

from .models import AppConfig


UNRESOLVED_ENV_PATTERN = re.compile(r"\$\{[^}]+\}")


def _expand_env_values(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _expand_env_values(inner) for key, inner in value.items()}
    if isinstance(value, list):
        return [_expand_env_values(item) for item in value]
    if isinstance(value, str):
        expanded = os.path.expandvars(value)
        if UNRESOLVED_ENV_PATTERN.search(expanded):
            return ""
        return expanded
    return value


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return AppConfig.model_validate(_expand_env_values(data))
