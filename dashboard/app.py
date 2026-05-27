"""Watchdog dashboard — minimal single-page Streamlit app."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import altair as alt
import pandas as pd
import requests
import streamlit as st
from cards import header_html, hero_html, recent_rows_html
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

# ---------------------------------------------------------------------------
# Sidebar — Tweaks (exactly 2 controls)
# ---------------------------------------------------------------------------

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


def fetch_trends(hours: int = 6) -> pd.DataFrame:
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
# Header + Hero
# ---------------------------------------------------------------------------

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

st.html(header_html())
st.html(hero_html(active, metric_style, readings=active_readings))

# ---------------------------------------------------------------------------
# Mini sparkline (single aggregated error-count line)
# ---------------------------------------------------------------------------

if show_chart and not trends_df.empty:
    agg = (
        trends_df.groupby("bucket", as_index=False)["error_count"]
        .sum()
        .sort_values("bucket")
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

    line = (
        alt.Chart(agg)
        .mark_line(color="#5B8FB0", strokeWidth=1.5)
        .encode(
            x=alt.X("bucket:T", axis=alt.Axis(title=None, labelAngle=-30, tickCount=6)),
            y=alt.Y("error_count:Q", axis=alt.Axis(title=None, tickCount=4)),
        )
        .properties(height=110)
    )

    chart = line
    if not anomaly_times.empty:
        dots = (
            alt.Chart(anomaly_times)
            .mark_point(color="#e05555", size=80, filled=True)
            .encode(
                x=alt.X("bucket:T"),
                y=alt.Y("error_count:Q"),
                tooltip=["bucket:T", "error_count:Q"],
            )
        )
        chart = line + dots

    st.altair_chart(chart, use_container_width=True)

# ---------------------------------------------------------------------------
# Recent anomaly timeline
# ---------------------------------------------------------------------------

st.html(recent_rows_html(anomalies, metric_style))

st.caption(
    f"Last refreshed {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC · "
    f"source `{API_URL}`"
)
