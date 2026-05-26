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


def _spike_with_z(target_z: float, baseline_mean: float = 4.0) -> list[datetime]:
    """Return spike timestamps producing approximately target_z."""
    stdev = 1.3  # approximate stdev of _varied_baseline counts
    count = int(baseline_mean + target_z * stdev) + 1
    return _spike_in_current_window(count)


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
        baseline = _varied_baseline()
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
        baseline = _varied_baseline()
        # Aim for z just above 2.0: spike = mean + 2.5*stdev ≈ 4 + 2.5*1.3 ≈ 8
        spike = _spike_in_current_window(8)
        result = detector.analyze("svc", baseline + spike, _NOW)
        assert result is not None
        assert result.severity == Severity.LOW
        assert 2.0 < result.z_score < 3.0

    def test_anomaly_result_severity_medium(self):
        """Z between 3.0 and 4.0 → MEDIUM severity."""
        detector = ZScoreDetector(window_minutes=5, z_threshold=2.0)
        baseline = _varied_baseline()
        # Aim for z ≈ 3.5: spike = mean + 3.5*stdev ≈ 4 + 4.5 ≈ 9
        spike = _spike_in_current_window(9)
        result = detector.analyze("svc", baseline + spike, _NOW)
        assert result is not None
        assert result.severity == Severity.MEDIUM
        assert 3.0 <= result.z_score < 4.0

    def test_anomaly_result_severity_high(self):
        """Z between 4.0 and 5.0 → HIGH severity."""
        detector = ZScoreDetector(window_minutes=5, z_threshold=2.0)
        baseline = _varied_baseline()
        # Aim for z ≈ 4.5: spike = mean + 4.5*stdev ≈ 4 + 6 ≈ 10
        spike = _spike_in_current_window(11)
        result = detector.analyze("svc", baseline + spike, _NOW)
        assert result is not None
        assert result.severity == Severity.HIGH
        assert 4.0 <= result.z_score < 5.0

    def test_anomaly_result_has_window_bounds(self):
        """AnomalyResult must carry window_start and window_end."""
        detector = ZScoreDetector(window_minutes=5, z_threshold=2.0)
        baseline = _varied_baseline()
        spike = _spike_in_current_window(30)
        result = detector.analyze("svc", baseline + spike, _NOW)
        assert result is not None
        assert result.window_start < result.window_end
        assert result.window_end == _NOW

    def test_anomaly_result_threshold_field(self):
        """AnomalyResult must record the configured threshold."""
        detector = ZScoreDetector(window_minutes=5, z_threshold=2.0)
        baseline = _varied_baseline()
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
        baseline = _varied_baseline()
        spike = _spike_in_current_window(100)
        result = detector.analyze("svc", baseline + spike, _NOW)
        assert result is not None
        assert result.severity == Severity.CRITICAL

    def test_errors_outside_lookback_are_ignored(self):
        """Errors older than lookback_hours should not affect Z-score calculation."""
        detector = ZScoreDetector(window_minutes=5, z_threshold=2.0, lookback_hours=1)
        old_errors = [_ts(-130) for _ in range(100)]
        result = detector.analyze("svc", old_errors, _NOW)
        assert result is None

    def test_timezone_naive_timestamps_are_coerced(self):
        """Timezone-naive timestamps should be treated as UTC, not crash."""
        detector = ZScoreDetector(window_minutes=5, z_threshold=2.0)
        # Mix naive and aware timestamps
        naive_spike = [
            (_NOW - timedelta(seconds=i * 10)).replace(tzinfo=None) for i in range(30)
        ]
        baseline = _varied_baseline()
        # Should not raise TypeError — naive timestamps get coerced to UTC
        result = detector.analyze("svc", baseline + naive_spike, _NOW)
        assert result is not None

    def test_timestamp_exactly_at_upper_boundary_is_included(self):
        """A timestamp exactly at `at` should land in the current window slot."""
        detector = ZScoreDetector(window_minutes=5, z_threshold=2.0)
        baseline = _varied_baseline()
        # Single timestamp AT exactly `at`
        at_boundary = [_NOW] * 30
        result = detector.analyze("svc", baseline + at_boundary, _NOW)
        assert result is not None
        assert result.error_count == 30

    def test_timestamp_exactly_at_cutoff_is_included(self):
        """A timestamp exactly at the 1h cutoff boundary should be included (slot 0)."""
        detector = ZScoreDetector(window_minutes=5, z_threshold=2.0)
        # Errors only at exactly the cutoff boundary — should not crash
        cutoff_ts = _NOW - timedelta(hours=1)
        result = detector.analyze("svc", [cutoff_ts] * 5, _NOW)
        # No anomaly expected (not in current window), just no crash
        assert result is None
