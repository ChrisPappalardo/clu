# Architecture

## Product shape

CLU is designed as a single-user system that runs under one Linux user account. It has no user authentication layer. Personalization lives in a local config file and, later, can also be edited through the application UI.

The system has one canonical briefing schema. Every output path uses the same stored report:

- React dashboard reads the JSON snapshot
- API serves the JSON snapshot and rendered HTML
- cron-triggered ingest writes JSON and HTML artifacts to disk
- future email delivery can send the same stored HTML briefing directly

## Services

- `ingest`: Python collector, normalizer, AI synthesizer, report writer
- `api`: FastAPI service that exposes the latest snapshot and report assets
- `web`: React dashboard for interactive browsing of the snapshot

## Data flow

1. Source adapters fetch raw data from APIs or RSS feeds.
2. Adapters normalize raw responses into a common `CollectedSourceData` shape.
3. The ingest pipeline merges these payloads into a `DailySnapshot`.
4. AI produces the lead summary, section summaries, themes, interpretation, and watchlist.
5. The pipeline writes:
   - `latest_snapshot.json`
   - `latest_snapshot.html`
   - `snapshot_index.json`
   - immutable timestamped artifact copies for each ingest run
6. The API serves the latest stored artifacts.
7. The React app fetches the snapshot from the API.

## Canonical report schema

The top-level report object is `DailySnapshot`. It contains:

- briefing metadata: `snapshot_id`, `snapshot_date`, `generated_at`, `timezone`
- one `lead_summary`
- one `what_changed_summary`
- one `outlook`
- one `risk_summary`
- high-level `themes`
- ranked `top_story_ids`
- `watch_items[]`
- `sections[]`, each with:
  - `id`, `title`, `kind`
  - section summary
  - section narrative
  - section `what_changed`, `why_now`, and `risk_summary`
  - `items[]` for news or event content
  - `metrics[]` for structured data signals
- `clusters[]` for ranked story-level briefings
  - cluster `what_changed`, `why_now`, `why_it_matters`, and risk framing
- `memory` describing continuity from prior snapshots
- `source_attributions[]`
- `generation_notes[]`

This separation matters:

- `items` model narrative/editorial material
- `metrics` model numeric structured signals
- `clusters` model merged story developments across sources and days
- section summaries can synthesize both

That makes the schema safe for:

- card-based UI rendering
- HTML email formatting
- later storage in a relational model
- future export to markdown or PDF

## Personalization

Initial personalization is file-based:

- enabled sections
- preferred regions
- preferred topics
- tone and interpretation level
- enabled sources and their parameters

The application should eventually expose a config editor UI, but the underlying source of truth remains a single-user config document.
