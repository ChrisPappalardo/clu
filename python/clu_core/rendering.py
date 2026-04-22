from __future__ import annotations

from html import escape

from .models import DailySnapshot


def render_snapshot_html(snapshot: DailySnapshot) -> str:
    sections_html: list[str] = []
    for section in snapshot.sections:
        item_html = "".join(
            f"""
            <li style="margin-bottom:12px;">
              <div style="font-weight:600;">{escape(item.title)}</div>
              <div style="margin-top:4px;color:#444;">{escape(item.summary)}</div>
              <div style="margin-top:4px;font-size:12px;color:#666;">{escape(item.source_name)}</div>
            </li>
            """
            for item in section.items
        )
        metric_html = "".join(
            f"""
            <li style="margin-bottom:8px;">
              <strong>{escape(metric.label)}:</strong> {escape(metric.value)}
              {f" ({escape(metric.change)})" if metric.change else ""}
            </li>
            """
            for metric in section.metrics
        )
        sections_html.append(
            f"""
            <section style="margin:24px 0;padding:20px;border:1px solid #ddd;border-radius:12px;background:#fff;">
              <h2 style="margin:0 0 8px 0;">{escape(section.title)}</h2>
              <p style="margin:0 0 16px 0;color:#333;">{escape(section.summary)}</p>
              {"<ul style='padding-left:20px;'>" + item_html + "</ul>" if item_html else ""}
              {"<ul style='padding-left:20px;'>" + metric_html + "</ul>" if metric_html else ""}
            </section>
            """
        )

    theme_html = "".join(
        f"<li style='margin-bottom:6px;'>{escape(theme)}</li>" for theme in snapshot.themes
    )

    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>CLU Daily Snapshot</title>
  </head>
  <body style="margin:0;background:#f4f1ea;color:#1b1c1d;font-family:Georgia, serif;">
    <main style="max-width:840px;margin:0 auto;padding:32px 20px 48px;">
      <header style="margin-bottom:24px;">
        <div style="letter-spacing:0.08em;font-size:12px;text-transform:uppercase;color:#7a5c2e;">CLU Daily Snapshot</div>
        <h1 style="margin:8px 0 12px;font-size:36px;">{escape(snapshot.snapshot_date)}</h1>
        <p style="font-size:18px;line-height:1.5;">{escape(snapshot.lead_summary)}</p>
      </header>
      <section style="margin-bottom:24px;padding:20px;border-radius:12px;background:#efe6d1;">
        <h2 style="margin-top:0;">Themes</h2>
        <ul style="padding-left:20px;margin-bottom:0;">{theme_html}</ul>
      </section>
      {''.join(sections_html)}
    </main>
  </body>
</html>
"""

