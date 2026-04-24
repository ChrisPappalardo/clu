from __future__ import annotations

from html import escape

from .models import DailySnapshot, SnapshotMetric, StoryCluster


def _metric_html(metric: SnapshotMetric) -> str:
    unit = ""
    if metric.unit:
        unit = "%" if metric.unit == "%" else f" {escape(metric.unit)}"
    meta = " ".join(
        part
        for part in [
            escape(metric.change) if metric.change else "",
            escape(metric.change_percent) if metric.change_percent else "",
            escape(metric.context) if metric.context else "",
            escape(metric.freshness.upper()) if metric.freshness else "",
        ]
        if part
    )
    return f"""
    <div style="padding:12px 13px;border-radius:14px;background:#ece6d6;">
      <div style="display:flex;justify-content:space-between;gap:8px;color:#444;">
        <span>{escape(metric.label)}</span>
        {f"<small style='color:#756f61;text-transform:uppercase;letter-spacing:0.06em;'>{escape(metric.freshness)}</small>" if metric.freshness else ""}
      </div>
      <div style="margin-top:6px;font-size:22px;font-weight:700;">{escape(metric.value)}{unit}</div>
      {f"<div style='margin-top:6px;font-size:12px;color:#666;'>{meta}</div>" if meta else ""}
    </div>
    """


def _grouped_metric_blocks(section_id: str, metrics: list[SnapshotMetric]) -> list[str]:
    if section_id != "markets":
        return [
            f"<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin-bottom:12px;'>{''.join(_metric_html(metric) for metric in metrics)}</div>"
        ]

    region_order = {"US": 0, "International": 1, "Global": 2, "Other": 3}
    grouped: dict[tuple[str, str], list[SnapshotMetric]] = {}
    for metric in metrics:
        raw = metric.raw or {}
        region = str(raw.get("market_region") or "Other")
        group = str(raw.get("market_group") or "Other")
        grouped.setdefault((region, group), []).append(metric)

    ordered_groups = sorted(
        grouped.items(),
        key=lambda item: (
            region_order.get(item[0][0], 99),
            min(int(metric.raw.get("display_order", 999)) for metric in item[1]),
        ),
    )
    blocks: list[str] = []
    for (region, group), group_metrics in ordered_groups:
        cards = "".join(
            _metric_html(metric)
            for metric in sorted(group_metrics, key=lambda metric: int((metric.raw or {}).get("display_order", 999)))
        )
        blocks.append(
            f"""
            <div style="margin-bottom:12px;padding:14px;border-radius:18px;background:rgba(239,230,209,0.62);">
              <div style="font-size:11px;letter-spacing:0.1em;text-transform:uppercase;color:#7a6542;">{escape(region)}</div>
              <div style="margin-top:4px;font-size:16px;font-weight:700;">{escape(group)}</div>
              <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin-top:10px;">{cards}</div>
            </div>
            """
        )
    return blocks


def _cluster_html(cluster: StoryCluster) -> str:
    tags = "".join(
        f"<span style='display:inline-block;margin:6px 6px 0 0;padding:6px 10px;border-radius:999px;background:#ebe1cb;font-size:12px;'>{escape(tag)}</span>"
        for tag in [*cluster.geography[:2], *cluster.topics[:2]]
    )
    return f"""
    <div style="padding:14px 15px;border-radius:16px;background:#f5efe0;">
      <div style="font-size:12px;color:#666;">
        {escape(cluster.section.replace('-', ' ').title())} | {len(cluster.source_ids)} source{"s" if len(cluster.source_ids) != 1 else ""} | Importance {cluster.importance_score:.2f}
      </div>
      <div style="margin-top:8px;font-size:18px;font-weight:700;line-height:1.25;">{escape(cluster.title)}</div>
      <div style="margin-top:6px;line-height:1.45;color:#444;">{escape(cluster.summary)}</div>
      {f"<div style='margin-top:8px;line-height:1.45;'><strong>Change:</strong> {escape(cluster.what_changed)}</div>" if cluster.what_changed else ""}
      {f"<div style='margin-top:8px;line-height:1.45;'><strong>Why now:</strong> {escape(cluster.why_now)}</div>" if cluster.why_now else ""}
      <div style="margin-top:8px;line-height:1.45;"><strong>Why it matters:</strong> {escape(cluster.why_it_matters)}</div>
      {f"<div style='margin-top:8px;line-height:1.45;color:#6a2c2c;'><strong>Risk:</strong> {escape(cluster.risk_summary)}</div>" if cluster.risk_summary else ""}
      {f"<div style='margin-top:8px;'>{tags}</div>" if tags else ""}
    </div>
    """


def render_snapshot_html(snapshot: DailySnapshot) -> str:
    top_stories = [cluster for cluster in snapshot.clusters if cluster.id in snapshot.top_story_ids]
    active_sources = [source.display_name for source in snapshot.source_attributions if not source.notes]
    source_html = "".join(
        f"<span style='display:inline-block;margin:0 8px 8px 0;padding:6px 10px;border-radius:999px;background:#ddd1b3;font-size:12px;'>{escape(source)}</span>"
        for source in active_sources
    )

    top_story_html = "".join(_cluster_html(cluster) for cluster in top_stories)
    watch_html = "".join(
        f"<div style='padding:12px 14px;border-radius:14px;background:#ece5d4;'><strong>{escape(item.label)}</strong><div style='margin-top:4px;color:#444;line-height:1.45;'>{escape(item.note)}</div></div>"
        for item in snapshot.watch_items
    )

    sections_html: list[str] = []
    for section in snapshot.sections:
        metric_html = "".join(_grouped_metric_blocks(section.id, section.metrics))
        cluster_html = "".join(_cluster_html(cluster) for cluster in section.clusters)
        sections_html.append(
            f"""
            <section style="margin-top:20px;padding:18px;border-radius:20px;border:1px solid #ddd;background:#fffdf8;">
              <div style="margin-bottom:12px;">
                <div style="font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:#8e6a34;">{escape(section.id.replace('-', ' '))}</div>
                <h2 style="margin:6px 0 8px;">{escape(section.title)}</h2>
                <p style="margin:0;color:#444;line-height:1.45;">{escape(section.summary)}</p>
                {f"<p style='margin:8px 0 0;color:#444;line-height:1.45;'><strong>Change:</strong> {escape(section.what_changed)}</p>" if section.what_changed else ""}
                {f"<p style='margin:8px 0 0;color:#444;line-height:1.45;'><strong>Why now:</strong> {escape(section.why_now)}</p>" if section.why_now else ""}
                {f"<p style='margin:8px 0 0;color:#6a2c2c;line-height:1.45;'><strong>Risk:</strong> {escape(section.risk_summary)}</p>" if section.risk_summary else ""}
              </div>
              {f"<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin-bottom:12px;'>{metric_html}</div>" if metric_html else ""}
              {f"<div style='display:grid;gap:12px;'>{cluster_html}</div>" if cluster_html else ""}
            </section>
            """
        )

    theme_html = "".join(
        f"<span style='display:inline-block;margin:0 8px 8px 0;padding:7px 11px;border-radius:999px;background:#ddd1b3;font-size:13px;'>{escape(theme)}</span>"
        for theme in snapshot.themes
    )

    generation_notes = "".join(
        f"<div style='margin-top:6px;color:#5f645f;font-size:13px;'>{escape(note)}</div>"
        for note in snapshot.generation_notes
    )

    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>CLU Daily Snapshot</title>
  </head>
  <body style="margin:0;background:#f2ede2;color:#1b211d;font-family:Georgia,serif;">
    <main style="max-width:1020px;margin:0 auto;padding:24px 16px 40px;">
      <section style="padding:22px;border-radius:24px;border:1px solid rgba(69,61,42,0.12);background:rgba(255,252,246,0.92);box-shadow:0 16px 44px rgba(76,64,43,0.08);">
        <div style="display:flex;flex-wrap:wrap;gap:18px;justify-content:space-between;align-items:flex-start;">
          <div style="flex:1 1 560px;min-width:0;">
            <div style="font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:#8e6a34;">CLU Daily Snapshot</div>
            <h1 style="margin:8px 0 12px;font-size:40px;line-height:1;">{escape(snapshot.snapshot_date)}</h1>
            <p style="margin:0 0 12px;font-size:18px;line-height:1.55;">{escape(snapshot.lead_summary)}</p>
            {f"<p style='margin:8px 0 0;line-height:1.5;'><strong>What changed:</strong> {escape(snapshot.what_changed_summary)}</p>" if snapshot.what_changed_summary else ""}
            {f"<p style='margin:8px 0 0;line-height:1.5;'><strong>Outlook:</strong> {escape(snapshot.outlook)}</p>" if snapshot.outlook else ""}
            {f"<p style='margin:8px 0 0;line-height:1.5;color:#6a2c2c;'><strong>Risk:</strong> {escape(snapshot.risk_summary)}</p>" if snapshot.risk_summary else ""}
          </div>
          <div style="flex:0 0 280px;display:grid;gap:12px;">
            <div style="padding:14px;border-radius:16px;background:#efe6d1;">
              <div style="font-size:12px;letter-spacing:0.08em;text-transform:uppercase;color:#6c5b3a;">Coverage</div>
              <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:10px;">
                <div><div style="font-size:22px;font-weight:700;">{len(top_stories)}</div><div style="color:#5f645f;">Top stories</div></div>
                <div><div style="font-size:22px;font-weight:700;">{len(snapshot.sections)}</div><div style="color:#5f645f;">Sections</div></div>
                <div><div style="font-size:22px;font-weight:700;">{len(active_sources)}</div><div style="color:#5f645f;">Sources</div></div>
                <div><div style="font-size:22px;font-weight:700;">{len(snapshot.watch_items)}</div><div style="color:#5f645f;">Watch items</div></div>
              </div>
            </div>
            <div style="padding:14px;border-radius:16px;background:#efe6d1;line-height:1.45;">
              <div style="font-size:12px;letter-spacing:0.08em;text-transform:uppercase;color:#6c5b3a;">Continuity</div>
              <p style="margin:10px 0 0;">{escape(snapshot.memory.continuity_note or "No prior comparison yet.")}</p>
            </div>
          </div>
        </div>
        <div style="margin-top:16px;">{theme_html}</div>
      </section>

      <section style="display:grid;grid-template-columns:minmax(0,1.65fr) minmax(280px,0.85fr);gap:18px;margin-top:20px;">
        <article style="padding:18px;border-radius:22px;border:1px solid rgba(69,61,42,0.12);background:rgba(255,252,246,0.92);">
          <h2 style="margin-top:0;">Top Stories</h2>
          <div style="display:grid;gap:12px;">{top_story_html}</div>
        </article>
        <aside style="display:grid;gap:18px;">
          <article style="padding:18px;border-radius:22px;border:1px solid rgba(69,61,42,0.12);background:rgba(255,252,246,0.92);">
            <h2 style="margin-top:0;">Watch Next</h2>
            <div style="display:grid;gap:10px;">{watch_html}</div>
          </article>
          <article style="padding:18px;border-radius:22px;border:1px solid rgba(69,61,42,0.12);background:rgba(255,252,246,0.92);">
            <h2 style="margin-top:0;">Sources</h2>
            <div>{source_html}</div>
            {generation_notes}
          </article>
        </aside>
      </section>

      {''.join(sections_html)}
    </main>
  </body>
</html>
"""
