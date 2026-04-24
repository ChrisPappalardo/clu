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
- Source filtering was tightened so Guardian and RSS connectors now share consistent pattern handling, Guardian `trailText` is cleaned before rendering, and Guardian config can exclude content types such as `liveblog`.
- Added a section-text cleanup/fallback layer so section `what_changed`, `why_now`, `risk_summary`, and `narrative` no longer surface markdown-ish formatting or raw cluster IDs in the dashboard/email output.
- Fixed section routing so metrics/items are grouped by their own declared section instead of the parent connector section; this restored FRED market metrics to the `markets` section.
- Improved FRED display formatting for the dashboard/report: CPI and core CPI now emphasize MoM and YoY moves, nonfarm payrolls now present as payroll change, retail sales render as dollar amounts, and index base-year units are hidden for CPI/core CPI/industrial production.
- Added a Yahoo Finance markets connector using `yfinance` for broad market levels and daily moves; current live config includes S&P 500, Nasdaq Composite, Dow Jones Industrial Average, gold, bitcoin, Euro Stoxx 50, and Nikkei 225.
- Section metric selection now rotates across sources only for the `markets` section so it can surface both FRED and Yahoo metrics without disturbing higher-signal metric ordering in `macro` and other sections.
- Verified with a fresh Ollama-backed ingest on `2026-04-23` / snapshot `20260424T010746Z`; the `markets` section now shows a mixed set of FRED and Yahoo metrics, including S&P 500, Nasdaq, and Dow alongside Treasury yields and Brent.
- Expanded the `markets` section metric budget to show the full current market pack and added explicit market grouping metadata for UI/report rendering.
- Verified with snapshot `20260424T011852Z`; the `markets` section now carries 14 metrics grouped into `US Rates & Energy`, `Risk & Credit`, `US Equity Indexes`, `International Equity Indexes`, and `Alternatives`.
- Corrected the `macro` section after the first metric-rotation pass displaced core FRED metrics with World Bank GDP rows; `macro` is back to the FRED-first set including CPI, core CPI, unemployment, payroll change, retail sales, and industrial production.
- Adjusted `US Rates & Energy` ordering so the `US 2Y Treasury` appears before the `US 10Y Treasury`.
- Reworked the weather connector so output is location-aware and human-readable: US-style locations now request imperial units from Open-Meteo, weather labels render as `High`, `Low`, `Precipitation`, and `Conditions`, and weather codes map to readable condition text such as `Overcast`.
- Verified with snapshot `20260424T012853Z`; the `markets` section order now starts `US 2Y Treasury`, `US 10Y Treasury`, `Brent Crude Spot`, and the weather section now shows `60.4 °F`, `30.2 °F`, `0 inch`, and `Overcast` for the current Clio, CA forecast.
- Began a full React dashboard overhaul on the current branch to decouple the desktop web experience from the future email/report layout.
- Replaced the old narrow stacked dashboard with a desktop-first briefing board: interactive top-story navigator + detail pane, dedicated macro and markets analysis panels, grouped cross-asset market board, visible source attribution rail, and smaller secondary radar cards for weather/disruptions/science.
- Weather is now labeled with the configured home location in the dashboard via the API config template, and the weather section is presented as a local forecast card instead of a generic data block.
- `docker compose exec -T web npm run build` passed after the dashboard rewrite.

## Next Review Focus

- Verify the Guardian/source-filter improvements against a clean full ingest artifact and continue tightening source selection where noisy items still leak through.
- Coverage selection should become budgeted across sections/topics instead of relying mainly on rank order of the first enriched items.
- AI section narratives still need stronger quality control; they no longer leak raw IDs/markdown, but they can still drift into weak or misleading prose.
- The markets section now shows the larger grouped metric set; next UI/content pass should refine label wording, compactness, and which groups deserve the most prominence on smaller screens.
- Weather is now legible for US locations, but the next pass should improve semantics further by surfacing more meaningful forecast concepts such as precipitation chance, snow/rain framing, and a concise daily weather summary instead of relying mainly on raw daily fields.
- The dashboard overhaul needs an in-browser visual pass against real desktop and mobile viewports; code/build are in place, but the next step should tune spacing, hierarchy, and the treatment of low-signal sections after seeing the live result.

## Product Notes

- CLU is a single-user daily world snapshot system with one canonical stored briefing schema.
- The stored snapshot artifacts are the source of truth. The API, dashboard, and future email delivery should all read from the same generated outputs.
- UI changes should be evaluated against both interactive dashboard quality and email-safe report rendering.
