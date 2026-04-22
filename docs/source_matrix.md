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

### Official publisher RSS feeds

- Purpose: direct ingestion from selected publishers without third-party aggregators
- Auth: usually no key required
- Example feeds:
  - NPR World: https://feeds.npr.org/1004/rss.xml
- Notes:
  - RSS lets the user keep a curated source list
  - adapter is generic, so additional feeds can be added through config

## Structured world data

### FRED API

- Purpose: US and global macroeconomic time series
- Auth: API key required
- Docs:
  - https://fred.stlouisfed.org/docs/api/fred/overview.html
  - https://fred.stlouisfed.org/docs/api/api_key.html
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

### OpenAI Responses API

- Purpose: structured synthesis of the collected signal into a stored daily briefing
- Auth: API key required
- Docs:
  - https://platform.openai.com/docs/api-reference/responses/create
  - https://platform.openai.com/docs/guides/structured-outputs?api-mode=responses&lang=python
  - https://platform.openai.com/docs/models/gpt-5-mini
- Current default:
  - model: `gpt-5-mini`
- User setup:
  1. Create an OpenAI API key.
  2. Put it in `.env` as `OPENAI_API_KEY=...`

