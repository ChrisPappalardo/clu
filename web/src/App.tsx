import { useEffect, useState } from "react";

type StoryCluster = {
  id: string;
  section: string;
  title: string;
  summary: string;
  what_changed?: string | null;
  why_now?: string | null;
  why_it_matters: string;
  risk_level?: string | null;
  risk_summary?: string | null;
  significance: string;
  source_ids: string[];
  source_names: string[];
  topics: string[];
  geography: string[];
  related_previous_cluster_ids?: string[];
};

type SnapshotMetric = {
  id: string;
  label: string;
  value: string;
  unit?: string | null;
  previous_value?: string | null;
  change?: string | null;
  change_percent?: string | null;
  trend?: string | null;
  freshness?: string | null;
  context?: string | null;
  raw?: Record<string, unknown>;
};

type SnapshotSection = {
  id: string;
  title: string;
  summary: string;
  narrative?: string | null;
  what_changed?: string | null;
  why_now?: string | null;
  risk_summary?: string | null;
  metrics: SnapshotMetric[];
  clusters: StoryCluster[];
};

type WatchItem = {
  label: string;
  note: string;
  section_id?: string | null;
};

type SourceAttribution = {
  source_id: string;
  display_name: string;
  notes?: string | null;
};

type SnapshotIndexEntry = {
  snapshot_id: string;
  snapshot_date: string;
  lead_summary: string;
  themes: string[];
};

type Snapshot = {
  snapshot_date: string;
  generated_at?: string;
  lead_summary: string;
  what_changed_summary?: string | null;
  outlook?: string | null;
  risk_summary?: string | null;
  themes: string[];
  top_story_ids: string[];
  watch_items: WatchItem[];
  sections: SnapshotSection[];
  clusters: StoryCluster[];
  source_attributions: SourceAttribution[];
  generation_notes: string[];
  memory: {
    prior_snapshot_date?: string | null;
    continuity_note?: string | null;
    continuing_cluster_ids: string[];
    newly_emerged_cluster_ids: string[];
  };
};

type ConfigTemplate = {
  user?: {
    home_location?: {
      label?: string;
    };
  };
};

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

function compactSectionTitle(id: string) {
  if (id === "world-news") return "World";
  if (id === "markets") return "Markets";
  if (id === "macro") return "Macro";
  if (id === "disruptions") return "Disruptions";
  return id.replace(/-/g, " ");
}

function formatMetric(metric: SnapshotMetric) {
  const unit = metric.unit && metric.unit !== "%" ? ` ${metric.unit}` : metric.unit === "%" ? "%" : "";
  return `${metric.value}${unit}`;
}

function storyState(cluster: StoryCluster) {
  return (cluster.related_previous_cluster_ids?.length ?? 0) > 0 ? "Continuing" : "New";
}

function marketMetricMeta(metric: SnapshotMetric) {
  const raw = metric.raw ?? {};
  const region = typeof raw.market_region === "string" ? raw.market_region : "Other";
  const group = typeof raw.market_group === "string" ? raw.market_group : "Other";
  const order = typeof raw.display_order === "number" ? raw.display_order : 999;
  return { region, group, order };
}

function groupMarketMetrics(metrics: SnapshotMetric[]) {
  const regionOrder = ["US", "International", "Global", "Other"];
  const buckets = new Map<string, SnapshotMetric[]>();

  for (const metric of metrics) {
    const { region, group } = marketMetricMeta(metric);
    const key = `${region}:::${group}`;
    buckets.set(key, [...(buckets.get(key) ?? []), metric]);
  }

  return [...buckets.entries()]
    .map(([key, groupMetrics]) => {
      const [region, group] = key.split(":::");
      return {
        region,
        group,
        metrics: groupMetrics.sort((left, right) => marketMetricMeta(left).order - marketMetricMeta(right).order),
      };
    })
    .sort((left, right) => {
      const regionDelta = regionOrder.indexOf(left.region) - regionOrder.indexOf(right.region);
      if (regionDelta !== 0) return regionDelta;
      return marketMetricMeta(left.metrics[0]).order - marketMetricMeta(right.metrics[0]).order;
    });
}

function sectionCopy(section?: SnapshotSection) {
  if (!section) return null;
  return section.narrative ?? section.summary;
}

function weatherLine(section: SnapshotSection | undefined, location: string | null) {
  if (!section || section.metrics.length === 0) {
    return location ? `No useful forecast is available for ${location}.` : "No useful forecast is available.";
  }
  const byLabel = new Map(section.metrics.map((metric) => [metric.label, metric]));
  const high = byLabel.get("High");
  const low = byLabel.get("Low");
  const conditions = byLabel.get("Conditions");
  const precipitation = byLabel.get("Precipitation");
  const pieces = [
    conditions?.value ? `${conditions.value.toLowerCase()}` : null,
    high ? `high ${formatMetric(high)}` : null,
    low ? `low ${formatMetric(low)}` : null,
    precipitation ? `precip ${formatMetric(precipitation)}` : null,
  ].filter(Boolean);
  return `${location ?? "Local forecast"}: ${pieces.join(" · ")}.`;
}

function hasSignal(section?: SnapshotSection) {
  return Boolean(section && (section.metrics.length > 0 || section.clusters.length > 0));
}

export default function App() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [history, setHistory] = useState<SnapshotIndexEntry[]>([]);
  const [locationLabel, setLocationLabel] = useState<string | null>(null);
  const [selectedStoryId, setSelectedStoryId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const snapshotResponse = await fetch(`${API_BASE}/api/v1/snapshot/latest`);
        if (!snapshotResponse.ok) {
          throw new Error(await snapshotResponse.text());
        }
        const snapshotData: Snapshot = await snapshotResponse.json();
        if (cancelled) return;
        setSnapshot(snapshotData);

        const [historyResult, configResult] = await Promise.allSettled([
          fetch(`${API_BASE}/api/v1/snapshots`).then((response) => (response.ok ? response.json() : [])),
          fetch(`${API_BASE}/api/v1/config/template`).then((response) => (response.ok ? response.json() : null)),
        ]);

        if (cancelled) return;
        setHistory(historyResult.status === "fulfilled" ? historyResult.value : []);
        if (configResult.status === "fulfilled") {
          const config = configResult.value as ConfigTemplate | null;
          setLocationLabel(config?.user?.home_location?.label ?? null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load snapshot.");
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!snapshot) return;
    const clusterLookup = new Map(snapshot.clusters.map((cluster) => [cluster.id, cluster]));
    const topStories = snapshot.top_story_ids
      .map((storyId) => clusterLookup.get(storyId))
      .filter((cluster): cluster is StoryCluster => Boolean(cluster));
    if (!topStories.length) return;
    if (!selectedStoryId || !topStories.some((story) => story.id === selectedStoryId)) {
      setSelectedStoryId(topStories[0].id);
    }
  }, [snapshot, selectedStoryId]);

  if (error) {
    return <main className="dash"><p className="stateMessage error">{error}</p></main>;
  }

  if (!snapshot) {
    return <main className="dash"><p className="stateMessage">Waiting for the first briefing...</p></main>;
  }

  const clusterLookup = new Map(snapshot.clusters.map((cluster) => [cluster.id, cluster]));
  const topStories = snapshot.top_story_ids
    .map((storyId) => clusterLookup.get(storyId))
    .filter((cluster): cluster is StoryCluster => Boolean(cluster));

  const selectedStory = topStories.find((story) => story.id === selectedStoryId) ?? topStories[0] ?? null;

  const macroSection = snapshot.sections.find((section) => section.id === "macro");
  const marketsSection = snapshot.sections.find((section) => section.id === "markets");
  const weatherSection = snapshot.sections.find((section) => section.id === "weather");
  const disruptionsSection = snapshot.sections.find((section) => section.id === "disruptions");
  const scienceSection = snapshot.sections.find((section) => section.id === "science");
  const activeSources = snapshot.source_attributions.filter((source) => !source.notes);
  const flaggedSources = snapshot.source_attributions.filter((source) => source.notes);

  return (
    <main className="dash">
      <section className="heroBand">
        <div className="heroMain">
          <div className="heroKicker">CLU Daily Brief</div>
          <h1>{snapshot.snapshot_date}</h1>
          <p className="heroSummary">{snapshot.lead_summary}</p>
          <div className="heroNotes">
            {snapshot.what_changed_summary && <p><span>What changed</span>{snapshot.what_changed_summary}</p>}
            {snapshot.outlook && <p><span>Outlook</span>{snapshot.outlook}</p>}
            {snapshot.risk_summary && <p className="heroRisk"><span>Risk</span>{snapshot.risk_summary}</p>}
          </div>
          <div className="themeBar">
            {snapshot.themes.map((theme) => (
              <span className="themePill" key={theme}>{theme}</span>
            ))}
          </div>
        </div>

        <div className="heroStats">
          <div className="statBox">
            <div className="statLabel">Coverage</div>
            <div className="statMatrix">
              <div><strong>{topStories.length}</strong><span>threads</span></div>
              <div><strong>{activeSources.length}</strong><span>sources</span></div>
              <div><strong>{snapshot.memory.newly_emerged_cluster_ids.length}</strong><span>new</span></div>
              <div><strong>{snapshot.memory.continuing_cluster_ids.length}</strong><span>continuing</span></div>
            </div>
          </div>
          <div className="statBox">
            <div className="statLabel">Continuity</div>
            <p>{snapshot.memory.continuity_note ?? "No prior comparison yet."}</p>
            {snapshot.memory.prior_snapshot_date && (
              <p className="metaLine">Compared with {snapshot.memory.prior_snapshot_date}</p>
            )}
            <p className="metaLine">{history.length} stored snapshots</p>
          </div>
        </div>
      </section>

      <section className="storyGrid">
        <article className="panel storyRail">
          <div className="panelHead">
            <div>
              <div className="panelKicker">Top Threads</div>
              <h2>Signal board</h2>
            </div>
          </div>
          <div className="storyList">
            {topStories.map((story, index) => (
              <button
                className={selectedStory?.id === story.id ? "storyCard storyCardActive" : "storyCard"}
                key={story.id}
                onClick={() => setSelectedStoryId(story.id)}
                type="button"
              >
                <div className="storyTopline">
                  <span className="storyIndex">{String(index + 1).padStart(2, "0")}</span>
                  <span className="storySection">{compactSectionTitle(story.section)}</span>
                  <span className={`badge badge-${storyState(story).toLowerCase()}`}>{storyState(story)}</span>
                </div>
                <h3>{story.title}</h3>
                <p>{story.summary}</p>
                <div className="storyMeta">
                  <span>{story.source_ids.length} source{story.source_ids.length === 1 ? "" : "s"}</span>
                  <span className={`tone tone-${story.significance}`}>{story.significance}</span>
                </div>
              </button>
            ))}
          </div>
        </article>

        <article className="panel featurePanel">
          {selectedStory ? (
            <>
              <div className="panelHead">
                <div>
                  <div className="panelKicker">Thread Focus</div>
                  <h2>{selectedStory.title}</h2>
                </div>
                <div className="featureBadges">
                  <span className="badge badge-neutral">{compactSectionTitle(selectedStory.section)}</span>
                  <span className={`badge badge-${storyState(selectedStory).toLowerCase()}`}>{storyState(selectedStory)}</span>
                </div>
              </div>

              <p className="featureSummary">{selectedStory.summary}</p>

              <div className="featureGrid">
                <section className="featureBlock">
                  <div className="blockLabel">Why it matters</div>
                  <p>{selectedStory.why_it_matters}</p>
                </section>
                <section className="featureBlock">
                  <div className="blockLabel">What changed</div>
                  <p>{selectedStory.what_changed ?? "This thread remains active in the current snapshot."}</p>
                </section>
                <section className="featureBlock">
                  <div className="blockLabel">Why now</div>
                  <p>{selectedStory.why_now ?? "This thread is gaining attention in the current ranking."}</p>
                </section>
                <section className="featureBlock">
                  <div className="blockLabel">Risk</div>
                  <p>{selectedStory.risk_summary ?? "No additional risk framing is attached to this thread."}</p>
                </section>
              </div>

              <div className="featureFooter">
                <div>
                  <div className="blockLabel">Sources</div>
                  <div className="chipWrap">
                    {selectedStory.source_names.map((source) => (
                      <span className="chip sourceChip" key={`${selectedStory.id}-${source}`}>{source}</span>
                    ))}
                  </div>
                </div>
                <div>
                  <div className="blockLabel">Tags</div>
                  <div className="chipWrap">
                    {selectedStory.geography.map((item) => (
                      <span className="chip scopeChip" key={`${selectedStory.id}-${item}`}>{item}</span>
                    ))}
                    {selectedStory.topics.map((item) => (
                      <span className="chip scopeChip scopeChipMuted" key={`${selectedStory.id}-${item}`}>{item}</span>
                    ))}
                  </div>
                </div>
              </div>
            </>
          ) : (
            <p className="stateMessage">No top story is available.</p>
          )}
        </article>

        <aside className="railStack">
          <article className="panel">
            <div className="panelHead">
              <div>
                <div className="panelKicker">Watchlist</div>
                <h2>Watch next</h2>
              </div>
            </div>
            <div className="watchList">
              {snapshot.watch_items.map((item) => (
                <div className="watchRow" key={`${item.section_id ?? "global"}-${item.label}`}>
                  <strong>{item.label}</strong>
                  <p>{item.note}</p>
                </div>
              ))}
            </div>
          </article>

          <article className="panel">
            <div className="panelHead">
              <div>
                <div className="panelKicker">Sources</div>
                <h2>Attribution</h2>
              </div>
            </div>
            <div className="chipWrap">
              {activeSources.map((source) => (
                <span className="chip sourceChip" key={source.source_id}>{source.display_name}</span>
              ))}
              {flaggedSources.map((source) => (
                <span className="chip sourceChip sourceChipMuted" key={source.source_id}>{source.display_name}</span>
              ))}
            </div>
            {snapshot.generation_notes.length > 0 && (
              <div className="generationNotes">
                {snapshot.generation_notes.map((note) => (
                  <p key={note}>{note}</p>
                ))}
              </div>
            )}
          </article>
        </aside>
      </section>

      <section className="analysisGrid">
        <article className="panel analysisPanel">
          <div className="panelHead">
            <div>
              <div className="panelKicker">Macro</div>
              <h2>Economic pulse</h2>
            </div>
            <span className="panelCount">{macroSection?.metrics.length ?? 0} metrics</span>
          </div>
          <div className="analysisTop">
            <p className="analysisText">{sectionCopy(macroSection)}</p>
            <div className="analysisLines">
              {macroSection?.what_changed && <p><span>Change</span>{macroSection.what_changed}</p>}
              {macroSection?.why_now && <p><span>Why now</span>{macroSection.why_now}</p>}
              {macroSection?.risk_summary && <p className="heroRisk"><span>Risk</span>{macroSection.risk_summary}</p>}
            </div>
          </div>
          <div className="metricBoard metricBoardMacro">
            {macroSection?.metrics.map((metric) => (
              <div className="metricTile" key={metric.id}>
                <div className="metricTileLabel">{metric.label}</div>
                <div className="metricTileDate">{metric.context ?? ""}</div>
                <div className="metricValue">{formatMetric(metric)}</div>
                <div className={`metricDelta metric-${metric.trend ?? "flat"}`}>
                  {metric.change && <span>{metric.change}</span>}
                  {metric.change_percent && <span>{metric.change_percent}</span>}
                </div>
              </div>
            ))}
          </div>
        </article>

        <article className="panel analysisPanel">
          <div className="panelHead">
            <div>
              <div className="panelKicker">Markets</div>
              <h2>Cross-asset board</h2>
            </div>
            <span className="panelCount">{marketsSection?.metrics.length ?? 0} metrics</span>
          </div>
          <div className="analysisTop marketsTop">
            <p className="analysisText">{sectionCopy(marketsSection)}</p>
            <div className="analysisLines">
              {marketsSection?.what_changed && <p><span>Change</span>{marketsSection.what_changed}</p>}
              {marketsSection?.why_now && <p><span>Why now</span>{marketsSection.why_now}</p>}
              {marketsSection?.risk_summary && <p className="heroRisk"><span>Risk</span>{marketsSection.risk_summary}</p>}
            </div>
          </div>
          <div className="marketGroups">
            {groupMarketMetrics(marketsSection?.metrics ?? []).map((group) => (
              <section className="marketGroup" key={`${group.region}-${group.group}`}>
                <div className="marketGroupHead">
                  <span>{group.region}</span>
                  <h3>{group.group}</h3>
                </div>
                <div className="metricBoard metricBoardMarket">
                  {group.metrics.map((metric) => (
                    <div className="metricTile" key={metric.id}>
                      <div className="metricTileLabel">{metric.label}</div>
                      <div className="metricTileDate">{metric.context ?? ""}</div>
                      <div className="metricValue">{formatMetric(metric)}</div>
                      <div className={`metricDelta metric-${metric.trend ?? "flat"}`}>
                        {metric.change && <span>{metric.change}</span>}
                        {metric.change_percent && <span>{metric.change_percent}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            ))}
          </div>
        </article>
      </section>

      <section className="secondaryGrid">
        <article className="panel secondaryPanel weatherPanel">
          <div className="panelHead">
            <div>
              <div className="panelKicker">Weather</div>
              <h2>{locationLabel ?? "Local forecast"}</h2>
            </div>
          </div>
          <p className="analysisText">{weatherLine(weatherSection, locationLabel)}</p>
          <div className="metricBoard metricBoardWeather">
            {weatherSection?.metrics.map((metric) => (
              <div className="metricTile compactMetricTile" key={metric.id}>
                <div className="metricTileLabel">{metric.label}</div>
                <div className="metricTileDate">{metric.context ?? ""}</div>
                <div className="metricValue">{formatMetric(metric)}</div>
              </div>
            ))}
          </div>
          <div className="analysisLines">
            {weatherSection?.what_changed && <p><span>Change</span>{weatherSection.what_changed}</p>}
            {weatherSection?.why_now && <p><span>Why now</span>{weatherSection.why_now}</p>}
          </div>
        </article>

        <article className="panel secondaryPanel">
          <div className="panelHead">
            <div>
              <div className="panelKicker">Disruptions</div>
              <h2>Secondary radar</h2>
            </div>
          </div>
          {hasSignal(disruptionsSection) ? (
            <div className="miniStoryStack">
              <p className="analysisText">{sectionCopy(disruptionsSection)}</p>
              {disruptionsSection?.clusters.slice(0, 2).map((cluster) => (
                <div className="miniStory" key={cluster.id}>
                  <div className="storyMeta">
                    <span className={`badge badge-${storyState(cluster).toLowerCase()}`}>{storyState(cluster)}</span>
                    <span className={`tone tone-${cluster.significance}`}>{cluster.significance}</span>
                  </div>
                  <strong>{cluster.title}</strong>
                  <p>{cluster.summary}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="analysisText">No disruption thread is strong enough to justify primary screen space in this snapshot.</p>
          )}
        </article>

        <article className="panel secondaryPanel">
          <div className="panelHead">
            <div>
              <div className="panelKicker">Science</div>
              <h2>Low-signal watch</h2>
            </div>
          </div>
          <p className="analysisText">
            {hasSignal(scienceSection)
              ? sectionCopy(scienceSection)
              : "Science is currently under-sourced in this briefing and is intentionally compressed until it carries stronger signal."}
          </p>
        </article>
      </section>
    </main>
  );
}
