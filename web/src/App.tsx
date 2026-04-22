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
  watch_points: string[];
};

type SnapshotMetric = {
  id: string;
  label: string;
  value: string;
  change?: string;
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

type SnapshotIndexEntry = {
  snapshot_id: string;
  snapshot_date: string;
  lead_summary: string;
  themes: string[];
};

type Snapshot = {
  snapshot_date: string;
  lead_summary: string;
  what_changed_summary?: string | null;
  outlook?: string | null;
  risk_summary?: string | null;
  themes: string[];
  top_story_ids: string[];
  watch_items: WatchItem[];
  sections: SnapshotSection[];
  clusters: StoryCluster[];
  memory: {
    prior_snapshot_date?: string | null;
    continuity_note?: string | null;
    continuing_cluster_ids: string[];
    newly_emerged_cluster_ids: string[];
  };
};

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

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

  const topStories = snapshot.top_story_ids
    .map((storyId) => snapshot.clusters.find((cluster) => cluster.id === storyId))
    .filter((cluster): cluster is StoryCluster => Boolean(cluster));

  return (
    <main className="shell">
      <section className="hero">
        <div className="eyebrow">CLU Daily Snapshot</div>
        <h1>{snapshot.snapshot_date}</h1>
        <p className="lead">{snapshot.lead_summary}</p>
        {snapshot.what_changed_summary && <p className="outlook"><strong>What changed:</strong> {snapshot.what_changed_summary}</p>}
        {snapshot.outlook && <p className="outlook"><strong>Outlook:</strong> {snapshot.outlook}</p>}
        {snapshot.risk_summary && <p className="riskLine"><strong>Risk:</strong> {snapshot.risk_summary}</p>}
        <div className="themeRow">
          {snapshot.themes.map((theme) => (
            <span className="theme" key={theme}>{theme}</span>
          ))}
        </div>
      </section>

      <section className="overviewGrid">
        <article className="panel">
          <h2>Top Stories</h2>
          <div className="stack">
            {topStories.map((story) => (
              <div className="storyCard" key={story.id}>
                <strong>{story.title}</strong>
                <span>{story.summary}</span>
                {story.what_changed && <p><strong>What changed:</strong> {story.what_changed}</p>}
                {story.why_now && <p><strong>Why now:</strong> {story.why_now}</p>}
                <small>{story.why_it_matters}</small>
                {story.risk_summary && <em className="riskText">{story.risk_summary}</em>}
                <div className="scoreRow">
                  <span>Importance {story.importance_score.toFixed(2)}</span>
                  <span>Novelty {story.novelty_score.toFixed(2)}</span>
                  {story.risk_level && <span>Risk {story.risk_level}</span>}
                </div>
              </div>
            ))}
          </div>
        </article>

        <article className="panel">
          <h2>Briefing Memory</h2>
          <p>{snapshot.memory.continuity_note ?? "No prior comparison yet."}</p>
          {snapshot.memory.prior_snapshot_date && (
            <p className="subtle">Compared with {snapshot.memory.prior_snapshot_date}</p>
          )}
          <div className="miniList">
            <div>
              <strong>Continuing</strong>
              <span>{snapshot.memory.continuing_cluster_ids.length}</span>
            </div>
            <div>
              <strong>New</strong>
              <span>{snapshot.memory.newly_emerged_cluster_ids.length}</span>
            </div>
            <div>
              <strong>History</strong>
              <span>{history.length}</span>
            </div>
          </div>
        </article>

        <article className="panel">
          <h2>Watch Next</h2>
          <div className="stack">
            {snapshot.watch_items.map((item) => (
              <div className="watchItem" key={`${item.section_id ?? "global"}-${item.label}`}>
                <strong>{item.label}</strong>
                <span>{item.note}</span>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="grid">
        {snapshot.sections.map((section) => (
          <article className="card" key={section.id}>
            <div className="cardHeader">
              <h2>{section.title}</h2>
              <p>{section.summary}</p>
              {section.narrative && <p className="narrative">{section.narrative}</p>}
              {section.what_changed && <p className="detailLine"><strong>What changed:</strong> {section.what_changed}</p>}
              {section.why_now && <p className="detailLine"><strong>Why now:</strong> {section.why_now}</p>}
              {section.risk_summary && <p className="riskText"><strong>Risk:</strong> {section.risk_summary}</p>}
            </div>
            {section.clusters.length > 0 && (
              <div className="stack">
                {section.clusters.map((cluster) => (
                  <div className="item storyCard" key={cluster.id}>
                    <strong>{cluster.title}</strong>
                    <span>{cluster.summary}</span>
                    {cluster.what_changed && <p><strong>What changed:</strong> {cluster.what_changed}</p>}
                    {cluster.why_now && <p><strong>Why now:</strong> {cluster.why_now}</p>}
                    <small>{cluster.why_it_matters}</small>
                    {cluster.risk_summary && <em className="riskText">{cluster.risk_summary}</em>}
                  </div>
                ))}
              </div>
            )}
            {section.metrics.length > 0 && (
              <div className="metrics">
                {section.metrics.map((metric) => (
                  <div className="metric" key={metric.id}>
                    <span>{metric.label}</span>
                    <strong>{metric.value}</strong>
                    {metric.change && <small>{metric.change}</small>}
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
