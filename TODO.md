# CLU TODO

## Workflow Notes

- Always update this `TODO.md` before stopping work or switching tasks so future sessions can resume cleanly.
- `docker compose run --rm ingest` calls local LLMs through Ollama. On current hardware it can take a few minutes to finish. Let it complete before judging results, because better model output improves development and review quality.
- The dashboard has two output targets:
  - interactive React dashboard for local use
  - static HTML report for email delivery
- The visual system should stay largely consistent between the React dashboard and the emailed HTML report.
- The email/report constraint matters: the layout should work as a tall, narrow smartphone-friendly reading experience even when the React version adds interaction.

## Current Priorities

- [x] Fix historical retention/indexing so `snapshot_index.json` does not lose older immutable runs.
- [x] Tighten enrichment validation so AI classifications use a constrained vocabulary and do not silently drift from ranking expectations.
- [ ] Rework coverage and selection logic so section/topic coverage is intentional rather than dominated by whichever items are enriched first.
- [ ] Improve source quality for existing connectors before adding many new sources.
- [ ] Expose history and comparison workflows in the dashboard using the stored snapshot artifacts already served by the API.
- [ ] Plan the email delivery path on top of immutable stored HTML/JSON artifacts.
- [ ] Plan a more durable historical storage/index layer for runs, delivery status, and retention policy.

## Near-Term Execution Order

1. Review and improve source normalization/filtering for Guardian, RSS, and other current connectors.
2. Design a stronger coverage-selection pipeline.
3. Improve dashboard history/provenance views.
4. Design email delivery and historical storage.

## Latest Progress

- Historical indexing was fixed so ingest now preserves the full set of immutable snapshot runs when rewriting `snapshot_index.json`.
- AI enrichment now normalizes and validates model output against the vocabulary expected by ranking logic.
- Verified with a full Ollama-backed ingest on `2026-04-23`; new artifacts were written successfully.
- Fresh snapshot review suggests the next quality gaps are source filtering/normalization and AI writing quality in section-level narrative fields.

## Next Review Focus

- Guardian filtering still needs tightening for regex-style exclusions and content-type handling such as liveblogs.
- Coverage selection should become budgeted across sections/topics instead of relying mainly on rank order of the first enriched items.
- AI section narratives should be constrained further; current output can still drift into list-like or markdown-ish text that is not suitable for polished dashboard/email rendering.

## Product Notes

- CLU is a single-user daily world snapshot system with one canonical stored briefing schema.
- The stored snapshot artifacts are the source of truth. The API, dashboard, and future email delivery should all read from the same generated outputs.
- UI changes should be evaluated against both interactive dashboard quality and email-safe report rendering.
