from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from clu_core.config import load_config

app = FastAPI(title="CLU API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _output_dir() -> Path:
    return Path(os.getenv("CLU_OUTPUT_DIR", "/app/data/output"))


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/snapshot/latest")
def latest_snapshot():
    path = _output_dir() / "latest_snapshot.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Snapshot not generated yet.")
    return _read_json(path)


@app.get("/api/v1/report/latest.html", response_class=HTMLResponse)
def latest_report_html():
    path = _output_dir() / "latest_snapshot.html"
    if not path.exists():
        raise HTTPException(status_code=404, detail="HTML report not generated yet.")
    return path.read_text(encoding="utf-8")


@app.get("/api/v1/snapshots")
def list_snapshots():
    path = _output_dir() / "snapshot_index.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Snapshot index not generated yet.")
    return _read_json(path)


@app.get("/api/v1/snapshots/{snapshot_id}")
def get_snapshot(snapshot_id: str):
    path = _output_dir() / f"{snapshot_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Snapshot not found.")
    return _read_json(path)


@app.get("/api/v1/config/template")
def config_template():
    config_path = os.getenv("CLU_CONFIG_PATH", "/app/config/user_config.yaml")
    if not Path(config_path).exists():
        config_path = "/app/config/user_config.example.yaml"
    return load_config(config_path).model_dump(mode="json")
