"""Watchdog dashboard — minimal single-page Streamlit app."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import altair as alt
import pandas as pd
import requests
import streamlit as st
from cards import (
    chart_header_html,
    footer_html,
    header_html,
    hero_html,
    recent_rows_html,
)
from streamlit_autorefresh import st_autorefresh


# Local copy — importing from app.* pulls in SQLAlchemy/asyncpg, breaking Streamlit's
# process model. Keep in sync with anomaly_detector.py manually.
def metric_readings(error_count: int, baseline_mean: float, z_score: float) -> dict:
    baseline = max(baseline_mean, 0.4)
    multiplier = error_count / baseline
    pct_above = ((error_count - baseline) / baseline) * 100
    score = min(100, round(20 + z_score * 8))
    if z_score >= 10:
        plain = "Severe spike"
    elif z_score >= 5:
        plain = "Critical spike"
    elif z_score >= 3:
        plain = "Unusually high"
    elif z_score >= 2:
        plain = "Slightly elevated"
    else:
        plain = "Within normal range"
    return {
        "multiplier": multiplier,
        "pct_above": pct_above,
        "score": score,
        "plain": plain,
        "z": z_score,
        "baseline": baseline,
    }


API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Watchdog", page_icon="🔭", layout="centered")
st_autorefresh(interval=10_000, key="refresh")

# Reduce Streamlit's default vertical padding between widget blocks
st.markdown(
    """
<style>
  section[data-testid="stMain"] .block-container {
    padding-top: 1rem !important;
    padding-bottom: 0.5rem !important;
  }
  div[data-testid="stHtml"] { margin-bottom: -0.75rem !important; }
  div[data-testid="stAltairChart"] { margin-top: -0.25rem !important; }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


def _get(path: str, params: dict | None = None) -> list | dict | None:
    try:
        resp = requests.get(f"{API_URL}{path}", params=params, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


def fetch_anomalies(limit: int = 10) -> list[dict]:
    return _get("/anomalies", {"limit": limit}) or []


def fetch_trends(hours: int = 24) -> pd.DataFrame:
    data = _get("/health/trends", {"hours": hours})
    if not data:
        return pd.DataFrame(columns=["bucket", "service_name", "error_count"])
    df = pd.DataFrame(data)
    df["bucket"] = pd.to_datetime(df["bucket"], utc=True)
    return df


anomalies = fetch_anomalies()
trends_df = fetch_trends()

# Active incident = most recent CRITICAL or HIGH anomaly
active = next(
    (a for a in anomalies if a.get("severity") in ("CRITICAL", "HIGH")),
    None,
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

clock = datetime.now(timezone.utc).strftime("%H:%M:%S")

active_readings = (
    metric_readings(
        error_count=active["error_count"],
        baseline_mean=(
            active.get("baseline_mean")
            if active.get("baseline_mean") is not None
            else 0.4
        ),
        z_score=active["z_score"],
    )
    if active
    else None
)

st.html(header_html(clock=clock))

# Tweaks popover — right-aligned, replaces sidebar
_, col_tweaks = st.columns([5, 1])
with col_tweaks:
    with st.popover("⚙", use_container_width=True):
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

# ---------------------------------------------------------------------------
# Hero + Investigate button
# ---------------------------------------------------------------------------

st.html(hero_html(active, metric_style, readings=active_readings))

if active:
    _, col_inv, _ = st.columns([3, 2, 3])
    with col_inv:
        if st.button("Investigate →", key="investigate", use_container_width=True):
            st.session_state["pre_open_first"] = True
        elif "pre_open_first" not in st.session_state:
            st.session_state["pre_open_first"] = False

# ---------------------------------------------------------------------------
# Sparkline — 24h aggregated error-count trend with anomaly markers
# (chart goes above Recent per design spec)
# ---------------------------------------------------------------------------

if show_chart and not trends_df.empty:
    agg = (
        trends_df.groupby("bucket", as_index=False)["error_count"]
        .sum()
        .sort_values("bucket")
    )
    peak = int(agg["error_count"].max()) if not agg.empty else 0
    focus_service = active["service_name"] if active else None
    st.html(chart_header_html(focus_service, peak))

    x_enc = alt.X(
        "bucket:T",
        axis=alt.Axis(
            title=None,
            labelAngle=0,
            tickCount=2,
            grid=False,
            domain=False,
            ticks=False,
            labelColor="#6b7a94",
            labelFont="JetBrains Mono, monospace",
            labelFontSize=10,
        ),
    )
    y_enc = alt.Y(
        "error_count:Q",
        axis=None,
        scale=alt.Scale(zero=True),
    )

    area = (
        alt.Chart(agg)
        .mark_area(color="#c8d0df", opacity=0.06, interpolate="monotone")
        .encode(x=x_enc, y=y_enc)
    )
    line = (
        alt.Chart(agg)
        .mark_line(color="#c8d0df", strokeWidth=1.6, interpolate="monotone")
        .encode(x=x_enc, y=y_enc)
    )

    anomaly_times = pd.DataFrame(
        [
            {
                "bucket": pd.to_datetime(a["detected_at"], utc=True),
                "error_count": a["error_count"],
            }
            for a in anomalies
            if a.get("detected_at")
        ]
    )

    layers = [area, line]
    if not anomaly_times.empty:
        dots = (
            alt.Chart(anomaly_times)
            .mark_point(color="#e05555", size=120, filled=True, opacity=0.9)
            .encode(
                x=alt.X("bucket:T"),
                y=alt.Y("error_count:Q"),
                tooltip=["bucket:T", "error_count:Q"],
            )
        )
        layers.append(dots)

    chart = (
        alt.layer(*layers)
        .properties(height=170)
        .configure_view(strokeWidth=0, fill="transparent")
        .configure_axis(grid=False)
    )
    st.altair_chart(chart, use_container_width=True)

# ---------------------------------------------------------------------------
# Recent anomaly timeline
# ---------------------------------------------------------------------------

pre_open = st.session_state.get("pre_open_first", False)
st.html(recent_rows_html(anomalies, metric_style, pre_open_first=pre_open))

# Reset after one render so repeated refreshes don't keep it open
st.session_state["pre_open_first"] = False

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.html(footer_html(API_URL))
