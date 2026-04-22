import { useEffect, useState } from "react";

type SnapshotItem = {
  id: string;
  title: string;
  summary: string;
  source_name: string;
  url?: string;
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
  items: SnapshotItem[];
  metrics: SnapshotMetric[];
};

type Snapshot = {
  snapshot_date: string;
  lead_summary: string;
  themes: string[];
  sections: SnapshotSection[];
};

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export default function App() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
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
  }, []);

  if (error) {
    return <main className="shell"><p className="error">{error}</p></main>;
  }

  if (!snapshot) {
    return <main className="shell"><p>Waiting for the first briefing...</p></main>;
  }

  return (
    <main className="shell">
      <section className="hero">
        <div className="eyebrow">CLU Daily Snapshot</div>
        <h1>{snapshot.snapshot_date}</h1>
        <p className="lead">{snapshot.lead_summary}</p>
        <div className="themeRow">
          {snapshot.themes.map((theme) => (
            <span className="theme" key={theme}>{theme}</span>
          ))}
        </div>
      </section>

      <section className="grid">
        {snapshot.sections.map((section) => (
          <article className="card" key={section.id}>
            <div className="cardHeader">
              <h2>{section.title}</h2>
              <p>{section.summary}</p>
            </div>
            {section.items.length > 0 && (
              <div className="stack">
                {section.items.map((item) => (
                  <a className="item" key={item.id} href={item.url} target="_blank" rel="noreferrer">
                    <strong>{item.title}</strong>
                    <span>{item.summary}</span>
                    <small>{item.source_name}</small>
                  </a>
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

