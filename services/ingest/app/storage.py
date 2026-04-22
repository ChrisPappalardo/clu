from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import ValidationError

from clu_core.models import DailySnapshot


RUN_ID_PATTERN = re.compile(r"^\d{8}T\d{6}Z$")


def load_snapshot(path: Path) -> DailySnapshot | None:
    if not path.exists():
        return None
    try:
        snapshot = DailySnapshot.model_validate_json(path.read_text(encoding="utf-8"))
    except ValidationError:
        return None
    if not RUN_ID_PATTERN.match(snapshot.snapshot_id):
        return None
    return snapshot


def list_snapshot_paths(output_dir: Path) -> list[Path]:
    return sorted(
        [
            path
            for path in output_dir.glob("*.json")
            if path.name not in {"latest_snapshot.json", "snapshot_index.json"}
        ]
    )


def load_recent_snapshots(output_dir: Path, limit: int) -> list[DailySnapshot]:
    paths = list_snapshot_paths(output_dir)
    snapshots = [load_snapshot(path) for path in paths[-limit:]]
    return [snapshot for snapshot in snapshots if snapshot is not None]


def write_snapshot_index(output_dir: Path, snapshots: list[DailySnapshot]) -> None:
    deduped: dict[str, DailySnapshot] = {}
    for snapshot in snapshots:
        deduped[snapshot.snapshot_id] = snapshot
    index = [
        {
            "snapshot_id": snapshot.snapshot_id,
            "snapshot_date": snapshot.snapshot_date,
            "generated_at": snapshot.generated_at.isoformat(),
            "lead_summary": snapshot.lead_summary,
            "themes": snapshot.themes,
            "top_story_ids": snapshot.top_story_ids,
        }
        for snapshot in sorted(deduped.values(), key=lambda row: row.generated_at)
    ]
    (output_dir / "snapshot_index.json").write_text(
        json.dumps(index, indent=2),
        encoding="utf-8",
    )
