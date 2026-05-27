"""HTML template functions for the Watchdog dashboard header and status hero."""

from __future__ import annotations

import html as _html
from datetime import datetime, timezone


def _e(s: object) -> str:
    """HTML-escape any value before interpolating into markup."""
    return _html.escape(str(s))


def _relative_time(iso: str) -> str:
    """Convert ISO timestamp string to e.g. '4m ago'."""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt
        secs = int(delta.total_seconds())
        if secs < 60:
            return f"{secs}s ago"
        if secs < 3600:
            return f"{secs // 60}m ago"
        return f"{secs // 3600}h ago"
    except Exception:
        return ""


_SEVERITY_COLOR = {
    "CRITICAL": "oklch(0.68 0.20 25)",
    "HIGH": "oklch(0.75 0.16 45)",
    "MEDIUM": "oklch(0.82 0.13 80)",
    "LOW": "oklch(0.74 0.12 240)",
}

_CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&display=swap');

  .wd-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.5rem 0 1rem;
    border-bottom: 1px solid #2a3040;
    margin-bottom: 1.5rem;
  }
  .wd-brand {
    font-size: 1.1rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    color: #edf0f5;
  }
  .wd-live {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    color: #93a0b4;
  }
  .wd-dot-green {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: oklch(0.78 0.13 158);
    box-shadow: 0 0 6px oklch(0.78 0.13 158);
  }

  .wd-hero {
    border-radius: 12px;
    padding: 2.5rem 2rem;
    margin: 0.5rem 0 1.5rem;
    text-align: center;
  }
  .wd-hero-ok {
    background: #141c14;
    border: 1px solid #1e3020;
  }
  .wd-hero-alert {
    background: #1c1212;
    border: 1px solid #3d1a1a;
  }

  .wd-glyph-ok {
    font-size: 2rem;
    color: oklch(0.78 0.13 158);
    margin-bottom: 0.5rem;
  }
  .wd-hero-h {
    font-size: 1.4rem;
    font-weight: 700;
    color: #edf0f5;
    margin: 0 0 0.4rem;
  }
  .wd-hero-sub {
    font-size: 0.9rem;
    color: #6b7a94;
    margin: 0;
  }

  .wd-pulse-wrap {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
  }
  .wd-pulse {
    width: 10px; height: 10px;
    border-radius: 50%;
    background: oklch(0.68 0.20 25);
    box-shadow: 0 0 0 0 oklch(0.68 0.20 25 / 0.6);
    animation: pulse 1.6s infinite;
  }
  @keyframes pulse {
    0%   { box-shadow: 0 0 0 0   oklch(0.68 0.20 25 / 0.6); }
    70%  { box-shadow: 0 0 0 8px oklch(0.68 0.20 25 / 0); }
    100% { box-shadow: 0 0 0 0   oklch(0.68 0.20 25 / 0); }
  }
  .wd-incident-label {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    color: oklch(0.68 0.20 25);
    text-transform: uppercase;
  }
  .wd-service {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1rem;
    color: #93a0b4;
    margin: 0.2rem 0 0.8rem;
  }
  .wd-metric {
    font-family: 'JetBrains Mono', monospace;
    font-size: 3rem;
    font-weight: 600;
    color: oklch(0.68 0.20 25);
    line-height: 1;
    margin: 0 0 0.2rem;
  }
  .wd-metric-cap {
    font-size: 0.8rem;
    color: #6b7a94;
    margin: 0 0 1rem;
  }
  .wd-ai-summary {
    font-size: 0.88rem;
    color: #93a0b4;
    font-style: italic;
    max-width: 480px;
    margin: 0 auto 1.25rem;
    line-height: 1.5;
  }
  .wd-cta {
    display: inline-block;
    padding: 0.45rem 1.2rem;
    border-radius: 6px;
    background: oklch(0.68 0.20 25 / 0.15);
    border: 1px solid oklch(0.68 0.20 25 / 0.4);
    color: oklch(0.78 0.18 25);
    font-size: 0.85rem;
    font-weight: 600;
    font-family: inherit;
    text-decoration: none;
    cursor: pointer;
  }

  /* Style the native Streamlit Investigate button to match the hero CTA */
  [data-testid="stButton"][key="investigate"] button,
  div[data-testid="stButton"] button[kind="secondary"] {
    background: oklch(0.68 0.20 25 / 0.15) !important;
    border: 1px solid oklch(0.68 0.20 25 / 0.4) !important;
    color: oklch(0.78 0.18 25) !important;
    font-weight: 600 !important;
  }

  /* Recent timeline */
  .wd-recent-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin: 1.5rem 0 0.6rem;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid #2a3040;
  }
  .wd-recent-title {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    color: #6b7a94;
    text-transform: uppercase;
  }
  .wd-recent-count {
    font-size: 0.75rem;
    color: #6b7a94;
  }
  .wd-row {
    border-bottom: 1px solid #1e2530;
    list-style: none;
  }
  .wd-row summary {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 0;
    cursor: pointer;
    list-style: none;
    user-select: none;
  }
  .wd-row summary::-webkit-details-marker { display: none; }
  .wd-row summary:hover { background: #161d28; }
  .wd-row-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .wd-row-time {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    color: #edf0f5;
    min-width: 3rem;
  }
  .wd-row-ago {
    font-size: 0.78rem;
    color: #6b7a94;
    min-width: 4.5rem;
  }
  .wd-row-service {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    color: #93a0b4;
    flex: 1;
  }
  .wd-row-metric {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    font-weight: 600;
    margin-left: auto;
  }
  .wd-row-arrow {
    font-size: 0.7rem;
    color: #6b7a94;
    transition: transform 0.15s;
  }
  .wd-row[open] .wd-row-arrow { transform: rotate(90deg); }
  .wd-row-body {
    padding: 0.75rem 1rem 1rem 1.5rem;
    background: #111820;
    border-radius: 0 0 6px 6px;
    margin-bottom: 0.25rem;
  }
  .wd-row-narrative {
    font-size: 0.85rem;
    color: #93a0b4;
    font-style: italic;
    margin: 0 0 0.75rem;
    line-height: 1.5;
  }
  .wd-row-stats {
    display: flex;
    gap: 2rem;
    font-size: 0.8rem;
    color: #6b7a94;
    margin-bottom: 0.4rem;
  }
  .wd-row-stat-val {
    font-family: 'JetBrains Mono', monospace;
    color: #edf0f5;
    font-weight: 600;
  }
  .wd-row-window {
    font-size: 0.75rem;
    color: #4a5568;
    margin-top: 0.4rem;
  }
</style>
"""


def header_html(clock: str = "") -> str:
    clock_str = clock or ""
    return f"""{_CSS}
<div class="wd-header">
  <span class="wd-brand">⊙ Watchdog</span>
  <span class="wd-live">
    <span class="wd-dot-green"></span>
    {clock_str}
  </span>
</div>
"""


def hero_html(
    anomaly: dict | None, metric_style: str = "multiplier", readings: dict | None = None
) -> str:
    if not anomaly:
        return """
<div class="wd-hero wd-hero-ok">
  <div class="wd-glyph-ok">✓</div>
  <h2 class="wd-hero-h">All systems normal</h2>
  <p class="wd-hero-sub">No anomalies detected in the last 6 hours.</p>
</div>
"""
    r = readings or {}

    multiplier = r.get("multiplier", 0)
    score = r.get("score", 0)
    plain = r.get("plain", "Spike detected")
    baseline = r.get("baseline", 0.4)
    z = r.get("z", anomaly.get("z_score", 0))

    metric_html = {
        "multiplier": f'<div class="wd-metric">{multiplier:.0f}×</div>'
        '<div class="wd-metric-cap">above normal</div>',
        "score": f'<div class="wd-metric">{score}</div>'
        '<div class="wd-metric-cap">anomaly score / 100</div>',
        "plain": f'<div class="wd-metric" style="font-size:1.6rem">{plain}</div>'
        f'<div class="wd-metric-cap">{anomaly["error_count"]} errors'
        f" · baseline &lt; {int(baseline) + 1}</div>",
        "zscore": f'<div class="wd-metric">z={z:.1f}</div>'
        '<div class="wd-metric-cap">standard deviations above baseline</div>',
    }.get(metric_style, "")

    first_sentence = _e((anomaly.get("ai_narrative") or "").split(".")[0])
    if first_sentence:
        first_sentence += "."

    return f"""
<div class="wd-hero wd-hero-alert">
  <div class="wd-pulse-wrap">
    <span class="wd-pulse"></span>
    <span class="wd-incident-label">Active Incident</span>
  </div>
  <div class="wd-service">{_e(anomaly["service_name"])}</div>
  {metric_html}
  <p class="wd-ai-summary">{first_sentence}</p>
  <span class="wd-cta-placeholder"></span>
</div>
"""


def recent_rows_html(
    anomalies: list[dict],
    metric_style: str = "multiplier",
    pre_open_first: bool = False,
) -> str:
    if not anomalies:
        return (
            '<p style="color:#6b7a94;font-size:0.85rem;margin-top:1rem;">'
            "No anomalies in the last 6 hours.</p>"
        )

    rows = []
    for a in anomalies:
        sev = a.get("severity", "LOW")
        color = _SEVERITY_COLOR.get(sev, "#5B8FB0")
        bl = max(a.get("baseline_mean") or 0.4, 0.4)
        multiplier = a["error_count"] / bl
        z = a.get("z_score", 0)
        score = min(100, round(20 + z * 8))
        if z >= 10:
            plain = "Severe spike"
        elif z >= 5:
            plain = "Critical spike"
        elif z >= 3:
            plain = "Unusually high"
        elif z >= 2:
            plain = "Slightly elevated"
        else:
            plain = "Within normal range"

        metric_label = {
            "multiplier": f"{multiplier:.0f}× normal",
            "score": f"{score} / 100",
            "plain": plain,
            "zscore": f"z={z:.1f}",
        }.get(metric_style, f"{multiplier:.0f}× normal")

        iso = a.get("detected_at", "")
        time_str = iso[11:16] if len(iso) >= 16 else "—"
        ago = _relative_time(iso)
        narrative = (
            (a.get("ai_narrative") or "No AI narrative available.")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        webhook = "fired ✓" if a.get("webhook_fired") else "not fired"
        w_start = (a.get("window_start") or "")[:16].replace("T", " ")
        w_end = (a.get("window_end") or "")[:16].replace("T", " ")

        open_attr = " open" if (pre_open_first and len(rows) == 0) else ""
        rows.append(
            f"""
<details class="wd-row"{open_attr}>
  <summary>
    <span class="wd-row-dot"
      style="background:{color};box-shadow:0 0 5px {color}80;"></span>
    <span class="wd-row-time">{time_str}</span>
    <span class="wd-row-ago">{ago}</span>
    <span class="wd-row-service">{_e(a["service_name"])}</span>
    <span class="wd-row-metric" style="color:{color};">{metric_label}</span>
    <span class="wd-row-arrow">▶</span>
  </summary>
  <div class="wd-row-body">
    <p class="wd-row-narrative">{narrative}</p>
    <div class="wd-row-stats">
      <span>Errors&nbsp;<span class="wd-row-stat-val">{a["error_count"]}</span></span>
      <span>Baseline&nbsp;<span class="wd-row-stat-val">≈{bl:.1f}</span></span>
      <span>Webhook&nbsp;<span class="wd-row-stat-val">{webhook}</span></span>
    </div>
    <div class="wd-row-window">Window: {w_start} → {w_end} UTC</div>
  </div>
</details>"""
        )

    count = len(anomalies)
    return f"""
<div class="wd-recent-header">
  <span class="wd-recent-title">Recent</span>
  <span class="wd-recent-count">{count} event{"s" if count != 1 else ""}</span>
</div>
{"".join(rows)}
"""
