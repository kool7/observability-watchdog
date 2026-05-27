# Observability Watchdog — UI Redesign Handoff

This document captures the design rework done for the **Project 3: Intelligent Observability & Event Watchdog** assessment dashboard. Feed it to Claude Code along with the prototype files so it can rebuild the dashboard inside your existing Python/Streamlit stack.

> **Design philosophy: ruthlessly minimal.** Every dashboard naturally accumulates noise — KPI cards, tabs, side panels, sparklines for everything. This redesign cuts to a single question: *"is anything wrong right now?"* Answer that loudly, then defer all other detail behind progressive disclosure. The prototype shows ~5 pieces of information by default, not ~50.

---

## 1. Original problem (your input)

> Project 3: Intelligent Observability & Event Watchdog — Site Reliability Engineering (SRE).
> Develop a service that parses application or platform logs to detect anomalies or "spikes" in errors using AI logic. When thresholds are breached, the system must trigger a simulated webhook alert and visualize health trends.

> I need your help to design UI and if you can help me out with more suggestion on the basis of assessment description what errors to show how to calculate those.

> Currently using `Z-score = 30`. It measures how far above the historical average the current error count is, in units of standard deviation. Normal baseline for payment-service = ~0 errors per 5-minute window. With a `_MIN_STDEV` floor of 1.0, `Z = (30 - 0) / 1.0 = 30`. Anything above 2.0 triggers an anomaly. Z=30 means "this is 30 standard deviations beyond normal" — essentially impossible under normal conditions. That's CRITICAL.

> But this is hard to digest for a dev or anyone using this dashboard.

**Constraints surfaced later in the chat:**
- Stack is pure Python with Streamlit (no React in production)
- Assessment has limited time — don't over-engineer
- Original dashboard required too much scrolling
- Top-nav links should be real tabs, not decorative
- Settings/tweaks panel needs a permanent, obvious way in

---

## 2. The core fix: make the anomaly metric digestible

`Z-score = 30` is mathematically correct but communicates nothing to a non-statistician. The prototype replaces it with **four layered representations**, all computed from the same raw data your detector already produces:

### Translations (Python pseudocode — drop straight into `app/services/anomaly_detector.py` or a new helper)

```python
def metric_readings(error_count: int, baseline_mean: float, z_score: float) -> dict:
    """Translate raw anomaly stats into reader-friendly forms.

    Returns all four representations; the dashboard picks one to show.
    """
    baseline = max(baseline_mean, 0.4)   # floor avoids divide-by-zero spam
    multiplier = error_count / baseline   #   →  "30× normal"
    pct_above = ((error_count - baseline) / baseline) * 100  # → "+7400%"

    # 0–100 anomaly score: z=2 → 36, z=5 → 60, z=10+ → 100
    score = min(100, round(20 + z_score * 8))

    if z_score >= 10:   plain = "Severe spike"
    elif z_score >= 5:  plain = "Critical spike"
    elif z_score >= 3:  plain = "Unusually high"
    elif z_score >= 2:  plain = "Slightly elevated"
    else:               plain = "Within normal range"

    return {
        "multiplier": multiplier,   # default UI choice
        "pct_above": pct_above,
        "score": score,             # 0–100 gauge-friendly
        "plain": plain,             # zero-math
        "z": z_score,               # kept for SREs who want the math
        "baseline": baseline,
    }
```

**Recommendation:** default the dashboard to **"30× normal"** (the multiplier). Show z-score on hover/expand only. The anomaly response API can return all of these so the UI never has to recompute.

### Anomaly model — what to add to the response

Your current `AnomalyResponse` has `error_count`, `z_score`, `severity`, `webhook_fired`, `ai_narrative`. Add:

- `baseline_mean: float` — required to compute the multiplier client-side
- `top_errors: list[{msg: str, count: int}]` — the top 3–5 normalized error messages in the window; tells the user *what* broke, not just *that* it did
- `trend_direction: Literal["rising", "recovering", "flat"]` — compare current bucket count to previous: powers the ↗/↘/→ arrow in the UI
- `time_to_detect_seconds: int` — `detected_at - window_end` in seconds; a direct quality signal for your detector

---

## 3. Other SRE metrics worth surfacing (rank ordered by usefulness)

| Metric | How to calculate | Why it matters |
|---|---|---|
| **× baseline multiplier** | `errors_in_window / max(baseline_mean, 1)` | Universal — every reader understands "30× normal" |
| **Top error grouping** | Group `ERROR` messages by normalized template (strip user IDs, timing, retry counts); top 5 by count in the window | The single most actionable signal — tells you *what* failed |
| **Trend direction** | Compare current window count to previous window: rising / recovering / flat | Drives the "Active incident" banner copy: "rising" vs "recovering" |
| **Error rate %** | `errors / (errors + warns + infos)` per window | Catches a service that has dropped to low traffic but is failing 100% of requests — pure error count misses this |
| **Time to detect** | `detected_at - window_end` | Quality signal for the detector itself |
| **Cascade detection** | Count of distinct services with `severity ≥ MEDIUM` in same 5-min window | Identifies multi-service incidents (e.g. shared DB outage) |
| **Burn rate (SLO)** | `current_error_rate / SLO_budget_rate` over rolling 1h window | Standard Google SRE metric if you add an SLO target |
| **Recovery time** | Time between first breach and first `z < threshold` window | Powers MTTR/MTTA reporting |

You do **not** need to ship all of these. The top three (multiplier, top errors, trend direction) plus the existing AI narrative will already make the dashboard far more useful than the current version.

---

## 4. Dashboard structure (what's in the prototype)

The prototype is **a single page with no tabs**. The page reads top-to-bottom and answers progressively more detailed questions. There is one fixed-width column (~760px max), generous vertical whitespace, and most detail is hidden until clicked.

### Layout

```
┌─────────────────────────────────────────────────┐
│  ⊙ Watchdog                ● Live · 16:08  [⚙] │   ← thin sticky header
├─────────────────────────────────────────────────┤
│                                                 │
│                                                 │
│              ● ACTIVE INCIDENT                  │   ← status hero (the
│                payment-service                  │     centerpiece — only
│                                                 │     content above the
│                    ┌─────┐                      │     fold)
│                    │ 30× │                      │
│                    └─────┘
│                 above normal                    │
│                                                 │
│     "Database connection timeouts on the        │
│      payment-gateway."                          │
│                                                 │
│              [ Investigate → ]                  │
│                                                 │
├─────────────────────────────────────────────────┤
│                                                 │
│   LAST 6 HOURS · payment-service                │   ← single quiet
│   ▁▁▁▁▁▁▁▁▁▂▁▁▁▁▂▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁●        │     sparkline with
│   16:08                                  10:13  │     red dots at
│                                                 │     anomaly buckets
├─────────────────────────────────────────────────┤
│                                                 │
│   RECENT                            3 events    │
│   ─────────────────────────────────────────     │
│   ● 16:06  2m ago  payment-service  30× normal ▸│   ← one-line rows;
│   ● 15:56 12m ago  payment-service  22× normal ▸│     click to expand
│   ● 15:21 47m ago  auth-service      4× normal ▸│     inline
│                                                 │
└─────────────────────────────────────────────────┘
```

### What's on screen by default

Five things, total:
1. The header (brand · live indicator · tweaks)
2. The status hero (one of: "All systems normal" / "Active incident + service + multiplier + one-sentence AI summary + one CTA")
3. A single 6-hour sparkline with anomaly markers
4. A timeline of recent anomalies, one line each
5. Footer

That's it. No KPI cards. No tabs. No side panels. No service health column. No webhook log section. No separate top-errors panel.

### Progressive disclosure (what shows when expanded)

Clicking a row in **Recent** expands it inline to reveal:
- Full AI narrative (not just the first sentence)
- Errors in window with baseline comparison
- Top error message
- Webhook delivery status + latency
- Window times
- `View logs` and `Open runbook` actions

Click again to collapse. Only one row open at a time, so the page never gets long.

### Status hero — the two modes

**Healthy:**
- Green checkmark glyph
- "All systems normal"
- Subtitle: "No anomalies detected in the last 6 hours."

**Incident:**
- Pulsing red dot + "ACTIVE INCIDENT" label
- Service name in mono
- The multiplier in a huge typographic display (`30×`)
- "above normal" caption
- First sentence of the AI narrative, italic, dimmed
- Single CTA: `Investigate →` — scrolls to and auto-expands that anomaly in Recent

### What got cut compared to a typical SRE dashboard

| Element | Cut because |
|---|---|
| KPI cards (total errors, anomalies fired, etc.) | Don't answer "is anything wrong now?" — they're vanity numbers |
| Tabs (Services, Anomalies, Webhooks, Logs) | Forces navigation. Inline disclosure beats tab switching for 90% of use cases |
| Multi-line chart with all 3 services | One aggregated line is enough at the overview level; per-service detail is in the expanded incident card |
| Service health side panel | Healthy services don't need real estate. If something's wrong, the hero says so |
| Standalone webhook log | Each anomaly carries its own delivery status — no value in a separate stream |
| Top-errors panel | Folded into the expanded anomaly card |
| Severity icons in emoji form | Replaced with calibrated dots; less playful, more readable |

### Tweaks (single panel, two controls)

- **Anomaly metric** — × baseline (default) / 0–100 score / Plain English / Z-score
- **Display** — toggle the trend chart on/off (some teams don't want a chart at all)

That's the entire tweak surface. Resist adding more.

---

## 5. Visual system (so Claude Code can match it)

- **Type:** Inter (UI) + JetBrains Mono (numbers, service names, IDs, timestamps)
- **Background ramp:** deep cool-slate using `oklch()` — `bg: 0.16 / surface-1: 0.20 / surface-2: 0.23 / surface-3: 0.27` at hue 250
- **Text ramp:** `text: 0.96 / dim: 0.74 / muted: 0.58`
- **Status colors:**
  - `ok: oklch(0.78 0.13 158)` — green
  - `info: oklch(0.74 0.12 240)` — blue
  - `warn: oklch(0.82 0.13 80)` — amber
  - `crit: oklch(0.68 0.20 25)` — red
- **No emoji** — severity rendered as small pulsing dots + uppercase pills (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`)
- **Charts:**
  - Multi-line for error rate over time, one line per service
  - Bar sparklines for service health (per-service histogram of recent buckets)
  - Anomaly markers = red dot + halo at the exact bucket
- **No SVG illustrations** beyond the watchdog mark + iconography for actions

---

## 6. Migrating to Streamlit (your actual stack)

The HTML prototype is a **visual spec**, not a runtime target. Because the layout is so simple, the Streamlit port is short.

### Mapping

| Prototype piece | Streamlit |
|---|---|
| Sticky header with brand + live dot | `st.html()` block at the top of the page — ~15 lines of HTML |
| Status hero | `st.html()` block — feed values via Python f-string; this is where the design lives, worth the polish |
| Mini chart (single line + anomaly dots) | `st.altair_chart()` — one `mark_line()` + one `mark_point()` layer, height ~110px |
| Recent timeline (expand on click) | `st.expander()` per row — Streamlit's native expander is exactly the right primitive |
| Tweaks panel | `st.sidebar` — 1 `st.selectbox` for the metric style, 1 `st.toggle` for the chart. That's it |
| Auto-refresh | `streamlit-autorefresh` package, 10s interval |
| Theme | `.streamlit/config.toml` under `[theme]` |

### `.streamlit/config.toml`

```toml
[theme]
base = "dark"
primaryColor = "#5B8FB0"               # steel accent (oklch 0.72 0.10 240)
backgroundColor = "#10141A"             # bg
secondaryBackgroundColor = "#1A2029"    # surface-2
textColor = "#EDF0F5"
font = "sans serif"
```

### Recommended `dashboard/app.py` shape

Keep your FastAPI service untouched. Rewrite just the dashboard:

```python
# dashboard/app.py
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from dashboard.api import fetch_trends, fetch_anomalies, fetch_webhook_events
from dashboard.metrics import metric_readings   # the helper from §2
from dashboard.cards import header_html, hero_html, chart   # st.html() templates + altair

st.set_page_config(page_title="Watchdog", page_icon="🔭", layout="centered")
st_autorefresh(interval=10_000, key="refresh")

# Sidebar = Tweaks panel
with st.sidebar:
    st.header("Tweaks")
    metric_style = st.selectbox(
        "Anomaly metric",
        options=["multiplier", "score", "plain", "zscore"],
        format_func=lambda v: {
            "multiplier": "× baseline",
            "score": "0–100 score",
            "plain": "Plain English",
            "zscore": "Z-score",
        }[v],
    )
    show_chart = st.toggle("Trend chart", value=True)

# Data
trends = fetch_trends(hours=6)
anomalies = fetch_anomalies()
webhooks = fetch_webhook_events()
active = next((a for a in anomalies if a["severity"] == "CRITICAL"), None)

# Header
st.html(header_html())

# Status hero (the centerpiece)
st.html(hero_html(active, metric_style))

# Mini chart
if show_chart:
    st.altair_chart(chart(trends, focus=active and active["service_name"]),
                    use_container_width=True)

# Recent timeline
st.markdown("##### Recent")
if not anomalies:
    st.caption("Nothing to report.")
for a in anomalies:
    r = metric_readings(a["error_count"], a["baseline_mean"], a["z_score"])
    label = f"{a['detected_at']:%H:%M}  ·  {a['service_name']}  ·  {r['multiplier']:.0f}× normal"
    with st.expander(label):
        st.write(a["ai_narrative"])
        col1, col2 = st.columns(2)
        col1.metric("Errors in window", a["error_count"],
                    delta=f"baseline {r['baseline']:.1f}")
        col2.metric("Webhook", f"{webhooks_for(a)['response_status']} · {webhooks_for(a)['latency_ms']}ms")
        st.code(a["top_errors"][0]["msg"], language="text")
        st.button("Open runbook", key=f"rb-{a['id']}")
```

That's the entire dashboard. ~50 lines, including imports.

### Minimum viable shipping order (limited time budget)

1. **Add `metric_readings()` helper** in `app/services/anomaly_detector.py` — biggest UX win for ~30 lines of Python.
2. **Add new fields to `AnomalyResponse`**: `baseline_mean`, `top_errors`, `trend_direction`, `time_to_detect_seconds` (§2).
3. **Rewrite `dashboard/app.py`** with the structure above. The `st.expander` per anomaly + status hero are 80% of the visual lift.
4. **Replace JS reload** with `streamlit-autorefresh`.
5. **Polish**: write `dashboard/cards.py` with the `header_html()` and `hero_html()` template functions — these are the only `st.html()` blocks. Use the CSS from the prototype's `<style>` tag.

Steps 1–3 already make the dashboard feel like a different product. Step 5 is the polish that makes screenshots presentation-worthy.

### Hero HTML template (paste-ready)

A single jinja-style Python f-string is enough. The CSS lives in a `<style>` block at the top of the page (inject once via `st.html()` in `header_html()`):

```python
def hero_html(anomaly: dict | None, metric_style: str) -> str:
    if not anomaly:
        return """
        <section class="hero hero-ok">
          <div class="hero-glyph-ok">✓</div>
          <h1 class="hero-h">All systems normal</h1>
          <p class="hero-sub">No anomalies detected in the last 6 hours.</p>
        </section>
        """
    r = metric_readings(anomaly["error_count"], anomaly["baseline_mean"], anomaly["z_score"])
    metric = {
        "multiplier": f'<div class="hero-metric mono">{r["multiplier"]:.0f}×</div>'
                      '<div class="hero-metric-cap">above normal</div>',
        "score":      f'<div class="hero-metric mono">{r["score"]}</div>'
                      '<div class="hero-metric-cap">anomaly score / 100</div>',
        "plain":      f'<div class="hero-metric hero-metric-text">{r["plain"]}</div>'
                      f'<div class="hero-metric-cap">{anomaly["error_count"]} errors · baseline &lt; {int(r["baseline"]) + 1}</div>',
        "zscore":     f'<div class="hero-metric mono">z={r["z"]:.1f}</div>'
                      '<div class="hero-metric-cap">standard deviations</div>',
    }[metric_style]
    first_sentence = anomaly["ai_narrative"].split(".")[0] + "."
    return f"""
    <section class="hero hero-alert">
      <div class="hero-status"><span class="hero-pulse"></span><span>Active incident</span></div>
      <div class="hero-service mono">{anomaly["service_name"]}</div>
      <div class="hero-metric-wrap">{metric}</div>
      <p class="hero-ai">{first_sentence}</p>
    </section>
    """
```

Drop the prototype's `<style>` block (just the hero/header/recent rules — ~150 lines of CSS) into `header_html()`'s output and you're done.

---

## 7. What to send Claude Code along with this file

**Send all of these:**
- ✅ This `handoff.md` (primary)
- ✅ `Observability Watchdog Dashboard.html` (the minimal entry — visual spec)
- ✅ `app.jsx` (minimal app + all components inline)
- ✅ `data.jsx` (mock data + `metricReadings()` translation function — port to Python)
- ✅ `tweaks-panel.jsx` (reference only — you'll replace with `st.sidebar`)
- ✅ `Observability Watchdog Dashboard (Detailed).html` (the busier earlier version, kept for reference in case you ever want service health / per-service charts back)
- ✅ Screenshots of the prototype (helps Claude Code grok visual hierarchy faster than reading CSS)
- ✅ Your existing `dashboard/app.py`, `app/services/anomaly_detector.py`, `app/schemas/anomaly.py`, `app/services/trends_service.py` so Claude Code knows the current code shape

**Then prompt Claude Code with something like:**

> Read `handoff.md` first. It describes the redesigned minimalist UI for my Observability Watchdog assessment. The HTML + JSX files in the project root are the visual spec, not code to copy — I'm in Python/Streamlit. **Critically: the goal is to make the dashboard radically simpler than it is today, not richer.**
>
> Please do, in order:
> 1. Add a `metric_readings()` helper to `app/services/anomaly_detector.py` matching §2 of the handoff.
> 2. Extend `AnomalyResponse` in `app/schemas/anomaly.py` with the new fields listed in §2 (`baseline_mean`, `top_errors`, `trend_direction`, `time_to_detect_seconds`).
> 3. Update the anomaly serializer (`app/services/anomaly_service.py` or equivalent) to populate those fields.
> 4. Rewrite `dashboard/app.py` per §4 — one page, no tabs, just: header → status hero → mini chart → recent timeline. Use `st.expander` for the recent rows.
> 5. Move filters to `st.sidebar` per §6.
> 6. Create `dashboard/cards.py` with the `hero_html()` template from §6.
> 7. Replace the JS reload with `streamlit-autorefresh`.
> 8. Apply the theme from `.streamlit/config.toml` in §6.
> 9. Keep all existing tests passing.
>
> Resist the urge to add KPI cards, sidebars with extra info, or extra tabs. The dashboard should answer "is anything wrong?" in the top fold.

---

## 8. Tweaks discoverability

The Tweaks panel in the prototype is a floating panel toggled by a gear icon in the header. In Streamlit this becomes `st.sidebar` which is always visible by default and collapses via Streamlit's built-in sidebar control — no custom protocol needed.

Keep the tweaks list short: only `Anomaly metric` (selectbox) and `Trend chart` (toggle). Resist adding more.

---

## 9. File index

| Path | Purpose |
|---|---|
| `Observability Watchdog Dashboard.html` | **Primary** — the minimalist visual spec. Header + status hero + mini chart + recent timeline |
| `Observability Watchdog Dashboard (Detailed).html` | Reference only — the earlier busier version with tabs, KPI cards, service health column, etc. Keep for ideas if a stakeholder ever wants more detail surfaced |
| `app.jsx` | Top-level App + all minimal components (header, status hero, mini chart, recent timeline rows) inline |
| `data.jsx` | Mock data shaped exactly like your existing API responses + `metricReadings()` translation function — **port this to Python** |
| `tweaks-panel.jsx` | Floating settings panel (Streamlit migration replaces with `st.sidebar`) |
| `panels.jsx` | (Detailed version only) — used by `Observability Watchdog Dashboard (Detailed).html` |
| `viz.jsx` | (Detailed version only) — used by `Observability Watchdog Dashboard (Detailed).html` |
| `handoff.md` | This document |

---

## 10. Open questions / next steps

- **Top error grouping**: needs a message-normalization function (strip UUIDs, timestamps, retry numbers, ms values). Either regex-based in Python or use Claude via your existing `claude_service` to cluster.
- **SLO target**: if you want burn-rate as a metric, decide a target (e.g. "99.5% of payment-service requests succeed over 30d") and add the SLO config to settings.
- **Acknowledgement flow**: the prototype has a "View anomaly" button but no actual acknowledge state. If you have time, add `anomaly.acknowledged_at` and an endpoint, then the dashboard can hide acknowledged incidents from the banner.
