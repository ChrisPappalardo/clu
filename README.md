# CLU

CLU is a single-user daily world snapshot application. It pulls a configurable mix of news and structured world data, normalizes it into one canonical briefing schema, uses AI to synthesize the signal, stores JSON and HTML report artifacts, serves them through a Python API, and renders an interactive React dashboard.

## Current scope

This repository now contains the initial project scaffold:

- shared Python models for user config, source payloads, and the daily snapshot
- a Python ingest service with configurable source adapters
- a Python FastAPI service serving the latest snapshot and HTML report
- a React dashboard wired to the canonical snapshot schema
- clustered story ranking, briefing memory, and AI-generated narratives
- Docker Compose for local orchestration
- setup docs for source selection and API keys

The current implementation phase is expanding source coverage, enriching macro and market signals, and tightening the dashboard/report layout around the stored briefing.

## Repository layout

- `config/user_config.example.yaml`: single-user configuration template
- `docs/architecture.md`: system design and canonical schema notes
- `docs/source_matrix.md`: source choices, auth requirements, and user setup steps
- `python/clu_core`: shared Python models and HTML rendering
- `services/ingest`: scheduled collection and report generation
- `services/api`: backend API service
- `web`: React dashboard

## Quick start

1. Copy `.env.example` to `.env`.
2. Copy `config/user_config.example.yaml` to `config/user_config.yaml`.
3. If you want local AI synthesis, make sure Ollama is running on the host and that the configured model is pulled, for example `ollama pull qwen2.5:3b`.
4. Add API keys for any enabled keyed sources.
5. Run `docker compose up --build`.
6. Trigger the ingest once:

```bash
docker compose run --rm ingest
```

7. Open:
   - API: `http://localhost:8000/api/v1/snapshot/latest`
   - Snapshot index: `http://localhost:8000/api/v1/snapshots`
   - Dashboard: `http://localhost:5173`

## Cron

Example host crontab entry for a 6:30 AM local snapshot:

```cron
30 6 * * * cd /path/to/clu && /usr/bin/docker compose run --rm ingest >> /path/to/clu/logs/ingest.log 2>&1
```

Replace `/path/to/clu` with the absolute path to your CLU repository.
Create the `logs/` directory before enabling the job.

## Notes

- The ingest path writes briefing artifacts under `data/output/`.
- Each ingest run now writes an immutable timestamped snapshot artifact in addition to `latest_snapshot.*`.
- The ingest path also writes `snapshot_index.json` so the API and UI can inspect prior briefings.
- Legacy pre-run-id snapshots are ignored for briefing history so same-day continuity is based on immutable runs only.
- The default AI config targets a host-run Ollama server through its OpenAI-compatible API at `http://host.docker.internal:11434/v1/`.
- `OLLAMA_FAST_MODEL`, `OLLAMA_MODEL`, and `OLLAMA_BASE_URL` can be changed in `.env` without editing the YAML config.
- The fast model is used for item enrichment and routing before clustering; the main model is used for final briefing synthesis.
- The default source pack now includes separate world and markets editorial inputs, including Guardian business coverage and BBC business RSS in addition to the world-news feeds.
- The default FRED config now splits slower macro indicators from daily market-state indicators and derives a 2s10s Treasury spread for the markets section.
- If the configured AI endpoint is unavailable, the ingest service falls back to heuristic summaries so the pipeline can still run.
- The current scaffold uses file-based report persistence with briefing history. The shared schema is designed so a database-backed implementation can be added without changing the API or dashboard contract.
