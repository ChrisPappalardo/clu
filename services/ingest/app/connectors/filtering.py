from __future__ import annotations

import re


def matches_regex_patterns(value: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, value, flags=re.IGNORECASE) for pattern in patterns)


def matches_substring_patterns(value: str, patterns: list[str]) -> bool:
    lowered = value.lower()
    return any(pattern.lower() in lowered for pattern in patterns)
