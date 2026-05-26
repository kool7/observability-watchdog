"""Streamlit dashboard — Observability Watchdog."""

import os
import time
from datetime import datetime, timezone

import pandas as pd
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")
REFRESH_INTERVAL = 10  # seconds

st.set_page_config(
    page_title="Observability Watchdog",
    page_icon="🔭",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Data fetching helpers
# ---------------------------------------------------------------------------


def _get(path: str, params: dict | None = None) -> list | dict | None:
    try:
        resp = requests.get(f"{API_URL}{path}", params=params, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


def fetch_trends(hours: int = 1) -> pd.DataFrame:
    data = _get("/health/trends", {"hours": hours})
    if not data:
        return pd.DataFrame(
            columns=[
                "bucket",
                "service_name",
                "error_count",
                "warn_count",
                "info_count",
            ]
        )
    df = pd.DataFrame(data)
    df["bucket"] = pd.to_datetime(df["bucket"], utc=True)
    return df


def fetch_anomalies(limit: int = 20) -> pd.DataFrame:
    data = _get("/anomalies", {"limit": limit})
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    if not df.empty:
        df["detected_at"] = pd.to_datetime(df["detected_at"], utc=True)
    return df


def fetch_webhook_events(limit: int = 20) -> pd.DataFrame:
    data = _get("/webhook/events", {"limit": limit})
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    if not df.empty:
        df["fired_at"] = pd.to_datetime(df["fired_at"], utc=True)
    return df


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("🔭 Observability Watchdog")
st.caption(
    f"Live data from `{API_URL}` · auto-refreshes every {REFRESH_INTERVAL}s · "
    f"last updated {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}"
)

trends_df = fetch_trends(hours=6)
anomalies_df = fetch_anomalies()
webhook_df = fetch_webhook_events()

# ---------------------------------------------------------------------------
# KPI strip
# ---------------------------------------------------------------------------

total_errors = int(trends_df["error_count"].sum()) if not trends_df.empty else 0
total_anomalies = len(anomalies_df)
webhooks_fired = (
    int((webhook_df["response_status"] // 100 == 2).sum())
    if not webhook_df.empty
    else 0
)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Errors (6h)", total_errors)
k2.metric("Anomalies Detected", total_anomalies)
k3.metric("Webhooks Fired", webhooks_fired)
k4.metric(
    "Services Monitored",
    trends_df["service_name"].nunique() if not trends_df.empty else 0,
)

st.divider()

# ---------------------------------------------------------------------------
# Chart 1 — Error Rate Over Time
# ---------------------------------------------------------------------------

st.subheader("Error Rate Over Time")
if trends_df.empty:
    st.info("No trend data yet — ingest some logs to see activity.")
else:
    pivot = trends_df.pivot_table(
        index="bucket",
        columns="service_name",
        values="error_count",
        aggfunc="sum",
        fill_value=0,
    )
    st.line_chart(pivot)

# ---------------------------------------------------------------------------
# Chart 2 — Service Health Matrix
# ---------------------------------------------------------------------------

st.subheader("Service Health Matrix")
if trends_df.empty:
    st.info("No data yet.")
else:
    latest_bucket = trends_df["bucket"].max()
    latest = trends_df[trends_df["bucket"] == latest_bucket].copy()
    latest["total"] = (
        latest["error_count"] + latest["warn_count"] + latest["info_count"]
    )
    latest["error_rate_%"] = (
        (latest["error_count"] / latest["total"].replace(0, 1)) * 100
    ).round(1)

    def _status(rate: float) -> str:
        if rate >= 20:
            return "🔴 Critical"
        if rate >= 10:
            return "🟡 Degraded"
        return "🟢 Healthy"

    latest["status"] = latest["error_rate_%"].apply(_status)
    st.dataframe(
        latest[
            [
                "service_name",
                "error_count",
                "warn_count",
                "info_count",
                "error_rate_%",
                "status",
            ]
        ]
        .sort_values("error_rate_%", ascending=False)
        .reset_index(drop=True),
        use_container_width=True,
        hide_index=True,
    )

st.divider()

# ---------------------------------------------------------------------------
# Chart 3 — Anomaly Events Timeline
# ---------------------------------------------------------------------------

col_left, col_right = st.columns([3, 2])

with col_left:
    st.subheader("Anomaly Events")
    if anomalies_df.empty:
        st.info("No anomalies detected yet.")
    else:
        SEVERITY_ICON = {"LOW": "🔵", "MEDIUM": "🟡", "HIGH": "🟠", "CRITICAL": "🔴"}
        display = anomalies_df[
            [
                "detected_at",
                "service_name",
                "severity",
                "error_count",
                "z_score",
                "webhook_fired",
            ]
        ].copy()
        display["severity"] = display["severity"].apply(
            lambda s: f"{SEVERITY_ICON.get(s, '')} {s}"
        )
        display["webhook_fired"] = display["webhook_fired"].apply(
            lambda v: "✅" if v else "❌"
        )
        display.columns = [
            "Detected At",
            "Service",
            "Severity",
            "Errors",
            "Z-Score",
            "Webhook",
        ]
        st.dataframe(
            display.reset_index(drop=True), use_container_width=True, hide_index=True
        )

# ---------------------------------------------------------------------------
# Chart 4 — AI Narrative Panel
# ---------------------------------------------------------------------------

with col_right:
    st.subheader("Latest AI Narrative")
    if anomalies_df.empty or "ai_narrative" not in anomalies_df.columns:
        st.info("No incidents narrated yet.")
    else:
        latest_anomaly = anomalies_df.sort_values("detected_at", ascending=False).iloc[
            0
        ]
        severity = latest_anomaly.get("severity", "UNKNOWN")
        icon = {"LOW": "🔵", "MEDIUM": "🟡", "HIGH": "🟠", "CRITICAL": "🔴"}.get(
            severity, "⚪"
        )
        st.markdown(f"**{icon} {severity}** — `{latest_anomaly['service_name']}`")
        st.markdown(f"*{latest_anomaly['detected_at'].strftime('%Y-%m-%d %H:%M UTC')}*")
        st.info(latest_anomaly.get("ai_narrative") or "No narrative available.")

st.divider()

# ---------------------------------------------------------------------------
# Chart 5 — Webhook Fired Log
# ---------------------------------------------------------------------------

st.subheader("Webhook Fired Log")
if webhook_df.empty:
    st.info("No webhook events yet.")
else:
    display = webhook_df[["fired_at", "anomaly_id", "response_status"]].copy()
    display["response_status"] = display["response_status"].apply(
        lambda s: f"✅ {s}" if 200 <= s < 300 else f"❌ {s}"
    )
    display.columns = ["Fired At", "Anomaly ID", "Response"]
    st.dataframe(
        display.reset_index(drop=True), use_container_width=True, hide_index=True
    )

# ---------------------------------------------------------------------------
# Auto-refresh
# ---------------------------------------------------------------------------

time.sleep(REFRESH_INTERVAL)
st.rerun()
