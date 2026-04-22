from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from clu_core.config import load_config
from clu_core.models import CollectedSourceData, SourceAttribution
from clu_core.rendering import render_snapshot_html

from .source_registry import build_connector
from .summarizer import synthesize_snapshot


def main() -> None:
    config_path = os.getenv("CLU_CONFIG_PATH", "/app/config/user_config.yaml")
    output_dir = Path(os.getenv("CLU_OUTPUT_DIR", "/app/data/output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    config_file = Path(config_path)
    if not config_file.exists():
        config_file = config_file.with_name("user_config.example.yaml")

    config = load_config(config_file)
    generated_at = datetime.now().astimezone()
    collected = []
    for source in config.sources:
        if not source.enabled:
            continue
        connector = build_connector(source, config.user.home_location)
        try:
            collected.append(connector.fetch())
        except Exception as exc:  # pragma: no cover
            collected.append(
                CollectedSourceData(
                    source=SourceAttribution(
                        source_id=source.id,
                        display_name=source.display_name,
                        source_type=source.type,
                        retrieved_at=generated_at,
                        notes=f"Connector failed: {exc}",
                    ),
                    section=source.section,
                    notes=[f"Source {source.id} failed: {exc}"],
                )
            )
            print(f"Source {source.id} failed: {exc}")

    snapshot = synthesize_snapshot(config, collected, generated_at)
    snapshot_json = json.dumps(snapshot.model_dump(mode="json"), indent=2)
    snapshot_html = render_snapshot_html(snapshot)

    latest_json = output_dir / "latest_snapshot.json"
    latest_html = output_dir / "latest_snapshot.html"
    dated_json = output_dir / f"{snapshot.snapshot_id}.json"
    dated_html = output_dir / f"{snapshot.snapshot_id}.html"

    latest_json.write_text(snapshot_json, encoding="utf-8")
    latest_html.write_text(snapshot_html, encoding="utf-8")
    dated_json.write_text(snapshot_json, encoding="utf-8")
    dated_html.write_text(snapshot_html, encoding="utf-8")

    print(f"Wrote {latest_json}")
    print(f"Wrote {latest_html}")


if __name__ == "__main__":
    main()
