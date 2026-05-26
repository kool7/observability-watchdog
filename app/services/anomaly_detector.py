from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.models.anomaly import Severity


@dataclass
class AnomalyResult:
    service_name: str
    detected_at: datetime
    window_start: datetime
    window_end: datetime
    error_count: int
    z_score: float
    threshold_breached: float
    severity: Severity


def _classify_severity(z_score: float) -> Severity:
    if z_score >= 5.0:
        return Severity.CRITICAL
    if z_score >= 4.0:
        return Severity.HIGH
    if z_score >= 3.0:
        return Severity.MEDIUM
    return Severity.LOW


class ZScoreDetector:
    def __init__(
        self,
        window_minutes: int = 5,
        z_threshold: float = 2.0,
        lookback_hours: int = 1,
    ) -> None:
        self.window_minutes = window_minutes
        self.z_threshold = z_threshold
        self.lookback_hours = lookback_hours

    def analyze(
        self,
        service_name: str,
        error_timestamps: list[datetime],
        at: datetime,
    ) -> AnomalyResult | None:
        cutoff = at - timedelta(hours=self.lookback_hours)
        window_duration = timedelta(minutes=self.window_minutes)
        total_slots = int(timedelta(hours=self.lookback_hours) / window_duration)

        # Bucket timestamps into fixed windows within the lookback period
        buckets: dict[int, int] = {}
        for ts in error_timestamps:
            if ts < cutoff or ts > at:
                continue
            # clamp so timestamps at exactly `at` fall in the last slot
            slot = min(int((ts - cutoff) / window_duration), total_slots - 1)
            buckets[slot] = buckets.get(slot, 0) + 1
        counts = [buckets.get(i, 0) for i in range(total_slots)]

        if len(counts) < 2:
            return None

        current_count = counts[-1]
        baseline = counts[:-1]

        try:
            mean = statistics.mean(baseline)
            stdev = statistics.stdev(baseline)
        except statistics.StatisticsError:
            return None

        # Use a minimum stdev floor so a perfectly flat baseline still
        # produces a meaningful z-score when a real spike occurs.
        stdev = max(stdev, 0.5)

        z = (current_count - mean) / stdev

        if z <= self.z_threshold:
            return None

        window_end = at
        window_start = at - window_duration

        return AnomalyResult(
            service_name=service_name,
            detected_at=datetime.now(timezone.utc),
            window_start=window_start,
            window_end=window_end,
            error_count=current_count,
            z_score=round(z, 4),
            threshold_breached=self.z_threshold,
            severity=_classify_severity(z),
        )
