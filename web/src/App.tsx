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
  importance_score: number;
  novelty_score: number;
  significance: string;
  watch_points: string[];
  source_ids: string[];
  source_names: string[];
  topics: string[];
  geography: string[];
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
    dropped_cluster_ids?: string[];
  };
};

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

function formatMetric(metric: SnapshotMetric) {
  const unit = metric.unit && metric.unit !== "%" ? ` ${metric.unit}` : metric.unit === "%" ? "%" : "";
  return `${metric.value}${unit}`;
}

function compactSectionTitle(id: string) {
  if (id === "world-news") return "World";
  if (id === "markets") return "Markets";
  if (id === "macro") return "Macro";
  if (id === "disruptions") return "Disruptions";
  return id.replace("-", " ");
}

export default function App() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [history, setHistory] = useState<SnapshotIndexEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/snapshot/latest`)
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(await response.text());
        }
        return response.json();
      })
      .then(setSnapshot)
      .catch((err: Error) => setError(err.message));

    fetch(`${API_BASE}/api/v1/snapshots`)
      .then((response) => (response.ok ? response.json() : []))
      .then(setHistory)
      .catch(() => setHistory([]));
  }, []);

  if (error) {
    return <main className="shell"><p className="error">{error}</p></main>;
  }

  if (!snapshot) {
    return <main className="shell"><p>Waiting for the first briefing...</p></main>;
  }

  const clusterLookup = new Map(snapshot.clusters.map((cluster) => [cluster.id, cluster]));
  const topStories = snapshot.top_story_ids
    .map((storyId) => clusterLookup.get(storyId))
    .filter((cluster): cluster is StoryCluster => Boolean(cluster));
  const activeSources = snapshot.source_attributions.filter((source) => !source.notes);
  const flaggedSources = snapshot.source_attributions.filter((source) => source.notes);

  return (
    <main className="shell">
      <section className="hero">
        <div className="heroMain">
          <div className="eyebrow">CLU Daily Snapshot</div>
          <h1>{snapshot.snapshot_date}</h1>
          <p className="lead">{snapshot.lead_summary}</p>
          {snapshot.what_changed_summary && (
            <p className="heroLine"><strong>What changed</strong> {snapshot.what_changed_summary}</p>
          )}
          {snapshot.outlook && (
            <p className="heroLine"><strong>Outlook</strong> {snapshot.outlook}</p>
          )}
          {snapshot.risk_summary && (
            <p className="heroLine riskLine"><strong>Risk</strong> {snapshot.risk_summary}</p>
          )}
        </div>
        <aside className="heroRail">
          <div className="railCard">
            <div className="railLabel">Coverage</div>
            <div className="statGrid">
              <div><strong>{topStories.length}</strong><span>Top stories</span></div>
              <div><strong>{snapshot.sections.length}</strong><span>Sections</span></div>
              <div><strong>{activeSources.length}</strong><span>Active sources</span></div>
              <div><strong>{history.length}</strong><span>Snapshots</span></div>
            </div>
          </div>
          <div className="railCard">
            <div className="railLabel">Continuity</div>
            <p>{snapshot.memory.continuity_note ?? "No prior comparison yet."}</p>
            {snapshot.memory.prior_snapshot_date && (
              <p className="subtle">Compared with {snapshot.memory.prior_snapshot_date}</p>
            )}
          </div>
        </aside>
        <div className="themeRow">
          {snapshot.themes.map((theme) => (
            <span className="theme" key={theme}>{theme}</span>
          ))}
        </div>
      </section>

      <section className="briefingGrid">
        <article className="panel panelWide">
          <div className="panelHeader">
            <h2>Top Stories</h2>
            <span>{topStories.length} selected</span>
          </div>
          <div className="storyList">
            {topStories.map((story) => (
              <div className="storyRow" key={story.id}>
                <div className="storyMeta">
                  <span>{compactSectionTitle(story.section)}</span>
                  <span>{story.source_ids.length} source{story.source_ids.length === 1 ? "" : "s"}</span>
                  <span>Importance {story.importance_score.toFixed(2)}</span>
                </div>
                <h3>{story.title}</h3>
                <p>{story.summary}</p>
                <div className="storyBody">
                  {story.what_changed && <p><strong>Change</strong> {story.what_changed}</p>}
                  {story.why_now && <p><strong>Why now</strong> {story.why_now}</p>}
                  <p><strong>Why it matters</strong> {story.why_it_matters}</p>
                </div>
                <div className="tagRow">
                  {story.geography.map((tag) => <span className="tag" key={`${story.id}-${tag}`}>{tag}</span>)}
                  {story.topics.map((tag) => <span className="tag tagMuted" key={`${story.id}-${tag}`}>{tag}</span>)}
                  {story.risk_summary && <span className="tag tagRisk">{story.risk_summary}</span>}
                </div>
              </div>
            ))}
          </div>
        </article>

        <aside className="sideStack">
          <article className="panel">
            <div className="panelHeader">
              <h2>Watch Next</h2>
            </div>
            <div className="stack">
              {snapshot.watch_items.map((item) => (
                <div className="watchItem" key={`${item.section_id ?? "global"}-${item.label}`}>
                  <strong>{item.label}</strong>
                  <span>{item.note}</span>
                </div>
              ))}
            </div>
          </article>

          <article className="panel">
            <div className="panelHeader">
              <h2>Sources</h2>
              <span>{activeSources.length} live</span>
            </div>
            <div className="sourceList">
              {activeSources.map((source) => (
                <span className="sourceChip" key={source.source_id}>{source.display_name}</span>
              ))}
              {flaggedSources.map((source) => (
                <span className="sourceChip sourceChipMuted" key={source.source_id}>{source.display_name}</span>
              ))}
            </div>
            {snapshot.generation_notes.length > 0 && (
              <div className="noteList">
                {snapshot.generation_notes.map((note) => (
                  <p className="subtle" key={note}>{note}</p>
                ))}
              </div>
            )}
          </article>
        </aside>
      </section>

      <section className="sectionGrid">
        {snapshot.sections.map((section) => (
          <article className={`sectionCard section-${section.id}`} key={section.id}>
            <div className="sectionHeader">
              <div>
                <div className="eyebrow sectionEyebrow">{compactSectionTitle(section.id)}</div>
                <h2>{section.title}</h2>
              </div>
              <p>{section.summary}</p>
            </div>

            {(section.narrative || section.what_changed || section.why_now || section.risk_summary) && (
              <div className="sectionNarrative">
                {section.narrative && <p>{section.narrative}</p>}
                {section.what_changed && <p><strong>Change</strong> {section.what_changed}</p>}
                {section.why_now && <p><strong>Why now</strong> {section.why_now}</p>}
                {section.risk_summary && <p className="riskText"><strong>Risk</strong> {section.risk_summary}</p>}
              </div>
            )}

            {section.metrics.length > 0 && (
              <div className="metricGrid">
                {section.metrics.map((metric) => (
                  <div className="metricCard" key={metric.id}>
                    <div className="metricHeader">
                      <span>{metric.label}</span>
                      {metric.freshness && <small>{metric.freshness}</small>}
                    </div>
                    <strong>{formatMetric(metric)}</strong>
                    <div className="metricMeta">
                      {metric.change && <span>{metric.change}</span>}
                      {metric.change_percent && <span>{metric.change_percent}</span>}
                      {metric.context && <span>{metric.context}</span>}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {section.clusters.length > 0 && (
              <div className="compactStories">
                {section.clusters.map((cluster) => (
                  <div className="compactStory" key={cluster.id}>
                    <div className="compactMeta">
                      <span>{cluster.source_ids.length} source{cluster.source_ids.length === 1 ? "" : "s"}</span>
                      <span>{cluster.significance}</span>
                    </div>
                    <strong>{cluster.title}</strong>
                    <p>{cluster.summary}</p>
                    {cluster.what_changed && <p><strong>Change</strong> {cluster.what_changed}</p>}
                  </div>
                ))}
              </div>
            )}
          </article>
        ))}
      </section>
    </main>
  );
}
