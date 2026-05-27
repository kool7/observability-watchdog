from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.models.anomaly import Severity

# Minimum stdev floor so a flat baseline still produces a meaningful z-score
# when a real spike occurs. Set to 1.0 (one standard error unit) to avoid
# over-sensitivity on low-traffic services.
_MIN_STDEV = 1.0


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
    baseline_mean: float = 0.0


def metric_readings(error_count: int, baseline_mean: float, z_score: float) -> dict:
    """Translate raw anomaly stats into reader-friendly representations.

    Returns multiplier ("30× normal"), 0-100 score, plain-English label,
    percentage above baseline, the raw z-score, and the floored baseline value.
    """
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

        # Bucket timestamps into fixed windows within the lookback period.
        # Coerce naive timestamps to UTC to avoid TypeError on comparison.
        buckets: dict[int, int] = {}
        for ts in error_timestamps:
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts < cutoff or ts > at:
                continue
            # clamp so timestamps at exactly `at` fall in the last slot
            slot = min(int((ts - cutoff) / window_duration), total_slots - 1)
            buckets[slot] = buckets.get(slot, 0) + 1

        counts = [buckets.get(i, 0) for i in range(total_slots)]
        current_count = counts[-1]
        baseline = counts[:-1]

        try:
            mean = statistics.mean(baseline)
            stdev = statistics.stdev(baseline)
        except statistics.StatisticsError:
            return None

        stdev = max(stdev, _MIN_STDEV)
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
            baseline_mean=round(mean, 4),
        )
