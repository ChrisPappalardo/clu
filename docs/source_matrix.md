# Source Matrix

This is the current recommended source mix for the first implementation phase. It favors official APIs and official publisher feeds where possible, and keeps free access as the default.

## Editorial and news sources

### The Guardian Open Platform

- Purpose: article search for world coverage
- Auth: API key required
- Free tier: developer access for non-commercial usage, up to 1 call per second and 500 calls per day
- Docs:
  - https://open-platform.theguardian.com/access
  - https://open-platform.theguardian.com/documentation/
- User setup:
  1. Create a Guardian Open Platform account.
  2. Request a developer key.
  3. Put it in `.env` as `GUARDIAN_API_KEY=...`

### GDELT DOC 2.0 API

- Purpose: broad multilingual world-news discovery and topic monitoring
- Auth: no key required
- Docs:
  - https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
- Notes:
  - good for global breadth and topic search
  - use as a discovery layer, not as the sole editorial authority
  - keep it opt-in by default because the endpoint can be operationally flaky in scheduled runs

### Official publisher RSS feeds

- Purpose: direct ingestion from selected publishers without third-party aggregators
- Auth: usually no key required
- Example feeds:
  - NPR World: https://feeds.npr.org/1004/rss.xml
  - BBC World: http://feeds.bbci.co.uk/news/world/rss.xml
  - BBC Business: http://feeds.bbci.co.uk/news/business/rss.xml
  - DW World: https://rss.dw.com/rdf/rss-en-world
  - PBS NewsHour headlines, filtered to world coverage: https://www.pbs.org/newshour/feeds/rss/headlines
- Notes:
  - RSS lets the user keep a curated source list
  - adapter is generic, so additional feeds can be added through config
  - for dependable daily operation, prefer direct publisher feeds first and add GDELT only as a secondary discovery source
  - use feed-level exclusion filters to keep obvious feature, opinion, and mixed-format items out of the hard-news briefing

## Structured world data

### FRED API

- Purpose: US and global macroeconomic time series
- Auth: API key required
- Docs:
  - https://fred.stlouisfed.org/docs/api/fred/overview.html
  - https://fred.stlouisfed.org/docs/api/api_key.html
- Suggested default series for world-pulse briefing:
  - Macro: CPI, core CPI, unemployment, payrolls, retail sales, industrial production, housing starts, Fed funds
  - Markets: 2Y/10Y Treasury, 2s10s spread, Brent crude, broad dollar index, VIX, high-yield spread, S&P 500, Nasdaq Composite
- User setup:
  1. Create a FRED account.
  2. Generate an API key.
  3. Put it in `.env` as `FRED_API_KEY=...`

### World Bank Indicators API

- Purpose: global development and economic indicators
- Auth: no key required
- Docs:
  - https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation
  - https://datahelpdesk.worldbank.org/knowledgebase/articles/898581-api-basic-call-structures

### Open-Meteo

- Purpose: local weather and climate signals for the user’s configured location
- Auth: no key required for non-commercial usage
- Docs:
  - https://open-meteo.com/en/docs

### USGS Earthquake GeoJSON Feeds

- Purpose: major earthquake and seismic disruption monitoring
- Auth: no key required
- Docs:
  - https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php

### Alpha Vantage

- Purpose: optional market pulse and commodity/treasury signals
- Auth: API key required
- Docs:
  - https://www.alphavantage.co/documentation/
- User setup:
  1. Claim a free API key.
  2. Put it in `.env` as `ALPHAVANTAGE_API_KEY=...`

## AI synthesis

### Ollama OpenAI-Compatible API

- Purpose: local structured synthesis of the collected signal into a stored daily briefing
- Auth: an API key is required by the OpenAI client, but Ollama ignores it; `ollama` is a sufficient placeholder
- Docs:
  - https://docs.ollama.com/openai
  - https://docs.ollama.com/api/openai-compatibility
- Current default:
  - provider: `ollama`
  - endpoint: `http://host.docker.internal:11434/v1/`
  - fast model: `qwen2.5:1.5b`
  - model: `qwen2.5:3b`
- User setup:
  1. Install and run Ollama on the host machine.
  2. Pull the configured models, for example `ollama pull qwen2.5:1.5b` and `ollama pull qwen2.5:3b`.
  3. Put `OLLAMA_API_KEY=ollama` in `.env` unless you want a different placeholder value.
  4. Set `OLLAMA_FAST_MODEL` and `OLLAMA_MODEL` in `.env` to the exact model tags you want to use.
  5. Keep the configured base URL pointed at the host from inside Docker with `OLLAMA_BASE_URL=http://host.docker.internal:11434/v1/`.
