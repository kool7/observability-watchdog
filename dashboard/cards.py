"""HTML template functions for the Watchdog dashboard header and status hero."""

from __future__ import annotations

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
    text-decoration: none;
    cursor: default;
  }
</style>
"""


def header_html() -> str:
    return f"""{_CSS}
<div class="wd-header">
  <span class="wd-brand">⊙ Watchdog</span>
  <span class="wd-live"><span class="wd-dot-green"></span> Live</span>
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

    first_sentence = (anomaly.get("ai_narrative") or "").split(".")[0]
    if first_sentence:
        first_sentence += "."

    return f"""
<div class="wd-hero wd-hero-alert">
  <div class="wd-pulse-wrap">
    <span class="wd-pulse"></span>
    <span class="wd-incident-label">Active Incident</span>
  </div>
  <div class="wd-service">{anomaly["service_name"]}</div>
  {metric_html}
  <p class="wd-ai-summary">{first_sentence}</p>
  <span class="wd-cta">Investigate →</span>
</div>
"""
