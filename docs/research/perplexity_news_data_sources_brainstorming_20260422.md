<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# What free sources of API news and data are available on the internet?  I am interested in world news headlines from reputable neutral sources (like the AP or NPR / PBS), data from key financial markets and other official and high velocity sources that give a "pulse" on the world, and other similar sources.

Several free APIs provide access to world news headlines from reputable neutral sources like AP and NPR/PBS, as well as financial market data and high-velocity global pulse indicators.[^1_1][^1_4][^1_9]

## News APIs

NewsAPI.org aggregates headlines from over 150,000 sources across 50+ countries, including neutral outlets like AP, NPR, and PBS; its free tier allows 100 requests daily with real-time and historical data.[^1_9][^1_1]
Other strong free options include NewsData.io (79,000+ sources in 200+ countries, 89 languages) and TheNewsAPI.com (40,000+ sources), both emphasizing global coverage from trusted publishers.[^1_4][^1_1]
WorldNewsAPI.com and APITube.io also offer free tiers for multilingual headlines from thousands of outlets.[^1_8][^1_1]

## Financial Data APIs

Alpha Vantage delivers free real-time and historical stock, ETF, forex, crypto, and economic indicator data via JSON/CSV, covering global markets with technical indicators.[^1_2][^1_6]
Marketstack provides end-of-day and intraday stock data from 60+ exchanges worldwide on its free plan (100 requests/month).[^1_6][^1_10]
Finnhub offers high-velocity real-time stock updates, sentiment analysis, and filings with a generous free tier.[^1_6]

## High-Velocity Sources

For a "world pulse," USGS provides free APIs for real-time earthquake data and Vs30 models, offering seismic activity feeds.[^1_3]
Combine news APIs with financial ones for comprehensive monitoring; most require a free API key signup and have rate limits (e.g., 500-1,000 calls/day).[^1_1][^1_2]
<span style="display:none">[^1_5][^1_7]</span>

<div align="center">⁂</div>

[^1_1]: https://github.com/free-news-api/news-api

[^1_2]: https://www.alphavantage.co

[^1_3]: https://www.usgs.gov/programs/earthquake-hazards/science/vs30-models-and-data

[^1_4]: https://newsdata.io/blog/best-free-news-api/

[^1_5]: https://apileague.com/articles/best-news-api/

[^1_6]: https://dev.to/williamsmithh/top-5-free-financial-data-apis-for-building-a-powerful-stock-portfolio-tracker-4dhj

[^1_7]: https://pmc.ncbi.nlm.nih.gov/articles/PMC6084800/

[^1_8]: https://apitube.io/free-news-api

[^1_9]: https://newsapi.org

[^1_10]: https://noteapiconnector.com/best-free-finance-apis


---

# Expand on non-financial and non-news data sources and what they provide.  Weather and climate data, economic and social data, etc.  Are those all APIs or are there other protocols that should be considered?  Keep it to free services, nothing premium, and nothing partisan.

Free APIs and open data protocols offer diverse non-financial, non-news sources for weather, climate, economic, and social data from neutral public entities. These primarily use RESTful APIs (JSON/XML over HTTP), though some leverage bulk downloads or other formats like CSV/GeoJSON for high-volume access. All listed options are free, with no premium tiers required.

## Weather APIs

Open-Meteo provides global current weather, hourly/daily forecasts, historical data (80+ years), and climate info at 1-11km resolution, sourced from national services; no key needed.[^2_2]
OpenWeatherMap delivers real-time conditions, 4-day forecasts, air quality, and national alerts worldwide via simple JSON endpoints; free tier suits most uses.[^2_5]
Visual Crossing offers current, hourly/sub-hourly forecasts, historical data, and alerts globally with a single endpoint; fully free for basic integration.[^2_8]

## Climate Data

Open-Meteo includes historical climate datasets (temperature, precipitation) spanning decades for trend analysis.[^2_2]
NOAA's Climate Data Online (via API) supplies U.S./global historical weather and climate records, including normals and extremes, as REST endpoints or bulk CSV.

## Economic Data

World Bank Open Data API provides indicators like GDP, inflation, trade, and poverty rates for 200+ countries, updated regularly in JSON format.[^2_6]
FRED API (Federal Reserve Economic Data) offers 800,000+ U.S./global time series on unemployment, CPI, industrial production, and more; free with key.[^2_1]

## Social and Health Data

WHO Global Health Observatory API delivers stats on mortality, disease prevalence, immunization, and SDGs across 194 countries.[^2_6]
UN Data API covers population, migration, human development, and humanitarian indicators from neutral UN sources.

## Other Protocols

Beyond REST APIs, consider OGC standards like WMS/WFS for geospatial data (e.g., USGS Earthquake API for real-time seismic feeds via GeoJSON).[^2_11]
Bulk downloads via SFTP/HTTP from data.gov or EU Open Data Portal provide high-velocity social/economic datasets when APIs hit limits; parse with scripts for pulse monitoring.[^2_6]
<span style="display:none">[^2_10][^2_3][^2_4][^2_7][^2_9]</span>

<div align="center">⁂</div>

[^2_1]: https://apipheny.io/free-api/

[^2_2]: https://open-meteo.com

[^2_3]: https://pmc.ncbi.nlm.nih.gov/articles/PMC11383449/

[^2_4]: https://www.reddit.com/r/Frontend/comments/1dbyqda/what_are_some_cool_apis_you_can_use_for_free_eg/

[^2_5]: https://openweathermap.org/api

[^2_6]: https://browse.welch.jhmi.edu/global-health/global-health-data-statistics

[^2_7]: https://mixedanalytics.com/blog/list-actually-free-open-no-auth-needed-apis/

[^2_8]: https://www.visualcrossing.com/weather-api/

[^2_9]: https://www.cip.org/blog/introducing-the-global-pulse-indicators

[^2_10]: https://dev.to/devshefali/20-free-apis-you-should-know-as-a-developer-5a3o

[^2_11]: https://www.usgs.gov/programs/earthquake-hazards/science/vs30-models-and-data

