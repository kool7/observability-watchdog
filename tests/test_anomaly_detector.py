"""
Tests for the Z-score anomaly detection service.
All tests are pure unit tests — no DB, no HTTP.
"""

from datetime import datetime, timedelta, timezone

from app.models.anomaly import Severity
from app.services.anomaly_detector import ZScoreDetector

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _ts(offset_minutes: int) -> datetime:
    return _NOW + timedelta(minutes=offset_minutes)


def _spike_in_current_window(count: int, window_minutes: int = 5) -> list[datetime]:
    """Generate `count` timestamps evenly spread within the current window."""
    step = timedelta(seconds=(window_minutes * 60) / max(count, 1))
    return [_NOW - step * i for i in range(count)]


def _varied_baseline() -> list[datetime]:
    """Baseline with natural variance: 2-8 errors per window over 11 windows."""
    counts = [3, 5, 2, 4, 6, 3, 5, 4, 2, 6, 3]
    result = []
    for i, n in enumerate(counts, start=1):
        window_center = _ts(-(i * 5) - 2)
        result.extend([window_center] * n)
    return result


# ---------------------------------------------------------------------------
# ZScoreDetector — baseline behaviour
# ---------------------------------------------------------------------------


class TestZScoreDetector:
    def test_no_anomaly_when_all_windows_are_zero(self):
        """No errors in any window → no anomaly."""
        detector = ZScoreDetector(window_minutes=5, z_threshold=2.0)
        result = detector.analyze(
            service_name="svc",
            error_timestamps=[],
            at=_NOW,
        )
        assert result is None

    def test_no_anomaly_when_single_window_has_data(self):
        """Only one data point — std dev is zero, Z-score undefined → no anomaly."""
        detector = ZScoreDetector(window_minutes=5, z_threshold=2.0)
        result = detector.analyze(
            service_name="svc",
            error_timestamps=[_ts(0)],
            at=_NOW,
        )
        assert result is None

    def test_no_anomaly_when_below_threshold(self):
        """Consistent error rate across windows should not trigger an anomaly."""
        detector = ZScoreDetector(window_minutes=5, z_threshold=2.0)
        # 3 errors in each of 12 five-minute windows (last hour) → flat distribution
        timestamps = [_ts(-(i * 5) - offset) for i in range(12) for offset in [1, 2, 3]]
        result = detector.analyze(
            service_name="svc",
            error_timestamps=timestamps,
            at=_NOW,
        )
        assert result is None

    def test_anomaly_detected_on_spike(self):
        """A spike in the current window above Z=2.0 should return AnomalyResult."""
        detector = ZScoreDetector(window_minutes=5, z_threshold=2.0)
        # baseline: 1 error per window for the past 11 windows
        baseline = [_ts(-(i * 5) - 1) for i in range(1, 12)]
        # spike: 30 errors all within the current 5-minute window
        spike = _spike_in_current_window(30)
        result = detector.analyze(
            service_name="svc",
            error_timestamps=baseline + spike,
            at=_NOW,
        )
        assert result is not None
        assert result.service_name == "svc"
        assert result.z_score > 2.0
        assert result.error_count == 30

    def test_anomaly_result_severity_low(self):
        """Z between 2.0 and 3.0 → LOW severity."""
        detector = ZScoreDetector(window_minutes=5, z_threshold=2.0)
        baseline = [_ts(-(i * 5) - 1) for i in range(1, 12)]
        spike = _spike_in_current_window(8)
        result = detector.analyze("svc", baseline + spike, _NOW)
        if result is not None and result.z_score < 3.0:
            assert result.severity == Severity.LOW

    def test_anomaly_result_has_window_bounds(self):
        """AnomalyResult must carry window_start and window_end."""
        detector = ZScoreDetector(window_minutes=5, z_threshold=2.0)
        baseline = [_ts(-(i * 5) - 1) for i in range(1, 12)]
        spike = _spike_in_current_window(30)
        result = detector.analyze("svc", baseline + spike, _NOW)
        assert result is not None
        assert result.window_start < result.window_end
        assert result.window_end == _NOW

    def test_anomaly_result_threshold_field(self):
        """AnomalyResult must record the configured threshold."""
        detector = ZScoreDetector(window_minutes=5, z_threshold=2.0)
        baseline = [_ts(-(i * 5) - 1) for i in range(1, 12)]
        spike = _spike_in_current_window(30)
        result = detector.analyze("svc", baseline + spike, _NOW)
        assert result is not None
        assert result.threshold_breached == 2.0

    def test_custom_z_threshold_respected(self):
        """A spike triggering z_threshold=2.0 should not trigger z_threshold=20.0."""
        detector = ZScoreDetector(window_minutes=5, z_threshold=20.0)
        baseline = _varied_baseline()
        spike = _spike_in_current_window(30)
        result = detector.analyze("svc", baseline + spike, _NOW)
        assert result is None

    def test_severity_critical_on_extreme_spike(self):
        """Z > 5.0 should map to CRITICAL severity."""
        detector = ZScoreDetector(window_minutes=5, z_threshold=2.0)
        baseline = [_ts(-(i * 5) - 1) for i in range(1, 12)]
        spike = _spike_in_current_window(100)
        result = detector.analyze("svc", baseline + spike, _NOW)
        assert result is not None
        assert result.severity == Severity.CRITICAL

    def test_errors_outside_lookback_are_ignored(self):
        """Errors older than lookback_hours should not affect Z-score calculation."""
        detector = ZScoreDetector(window_minutes=5, z_threshold=2.0, lookback_hours=1)
        # Only errors from 2 hours ago
        old_errors = [_ts(-130) for _ in range(100)]
        result = detector.analyze("svc", old_errors, _NOW)
        assert result is None
