"""Tests for observability.base — MetricCounter, MetricHistogram, MetricsPublisher, MetricsSnapshot."""

from __future__ import annotations

import threading

import pytest

from ayeneh.observability.base import (
    MetricCounter,
    MetricHistogram,
    MetricsPublisher,
    MetricsSnapshot,
)


# ---------------------------------------------------------------------------
# MetricCounter
# ---------------------------------------------------------------------------


class TestMetricCounter:
    def test_initial_value(self) -> None:
        c = MetricCounter("test")
        assert c.get() == 0

    def test_inc(self) -> None:
        c = MetricCounter("test")
        c.inc()
        assert c.get() == 1
        c.inc(5)
        assert c.get() == 6

    def test_dec(self) -> None:
        c = MetricCounter("test")
        c.inc(10)
        c.dec(3)
        assert c.get() == 7

    def test_reset(self) -> None:
        c = MetricCounter("test")
        c.inc(42)
        c.reset()
        assert c.get() == 0

    def test_thread_safety(self) -> None:
        c = MetricCounter("test")
        errors: list[Exception] = []

        def worker() -> None:
            try:
                for _ in range(1000):
                    c.inc(1)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert c.get() == 10000

    def test_name(self) -> None:
        c = MetricCounter("my_counter")
        assert c.name == "my_counter"


# ---------------------------------------------------------------------------
# MetricHistogram
# ---------------------------------------------------------------------------


class TestMetricHistogram:
    def test_initial_state(self) -> None:
        h = MetricHistogram("test")
        assert h.count() == 0
        assert h.avg() == 0.0

    def test_observe(self) -> None:
        h = MetricHistogram("test")
        h.observe(10.0)
        h.observe(20.0)
        h.observe(30.0)
        assert h.count() == 3
        assert h.avg() == 20.0
        assert h.total() == 60.0

    def test_percentiles(self) -> None:
        h = MetricHistogram("test")
        for i in range(100):
            h.observe(float(i))
        assert h.p50() == 50.0
        assert h.p99() == 99.0

    def test_max_size_bounded(self) -> None:
        h = MetricHistogram("test", max_size=5)
        for i in range(10):
            h.observe(float(i))
        # Only last 5 values retained
        assert h.count() == 10  # count tracks total observations
        # avg should be from the window (last 5: 5,6,7,8,9)
        assert h.avg() == 7.0

    def test_reset(self) -> None:
        h = MetricHistogram("test")
        h.observe(42.0)
        h.reset()
        assert h.count() == 0
        assert h.avg() == 0.0

    def test_empty_percentiles(self) -> None:
        h = MetricHistogram("test")
        assert h.p50() == 0.0
        assert h.p99() == 0.0

    def test_thread_safety(self) -> None:
        h = MetricHistogram("test")
        errors: list[Exception] = []

        def worker() -> None:
            try:
                for i in range(100):
                    h.observe(float(i))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert h.count() == 1000


# ---------------------------------------------------------------------------
# MetricsSnapshot
# ---------------------------------------------------------------------------


class TestMetricsSnapshot:
    def test_frozen(self) -> None:
        snap = MetricsSnapshot(module="test", counters={"a": 1})
        with pytest.raises(AttributeError):
            snap.module = "changed"  # type: ignore[misc]

    def test_has_timestamp(self) -> None:
        snap = MetricsSnapshot(module="test")
        assert snap.timestamp is not None

    def test_default_fields(self) -> None:
        snap = MetricsSnapshot(module="test")
        assert snap.counters == {}
        assert snap.histograms == {}


# ---------------------------------------------------------------------------
# MetricsPublisher (concrete subclass for testing)
# ---------------------------------------------------------------------------


class _TestPublisher(MetricsPublisher):
    def __init__(self) -> None:
        super().__init__("test_module")

    def export_prometheus_text(self) -> str:
        lines = []
        for name, c in self._counters.items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {c.get()}")
        for name, h in self._histograms.items():
            lines.append(f"# TYPE {name} histogram")
            lines.append(f"{name}_avg {h.avg()}")
        return "\n".join(lines)


class TestMetricsPublisher:
    def test_counter_lazy_creation(self) -> None:
        p = _TestPublisher()
        c1 = p._counter("requests")
        c2 = p._counter("requests")
        assert c1 is c2
        p.inc("requests")
        assert c1.get() == 1

    def test_histogram_lazy_creation(self) -> None:
        p = _TestPublisher()
        h1 = p._histogram("latency")
        h2 = p._histogram("latency")
        assert h1 is h2
        p.observe("latency", 42.0)
        assert h1.avg() == 42.0

    def test_snapshot(self) -> None:
        p = _TestPublisher()
        p.inc("requests", 5)
        p.observe("latency", 100.0)
        snap = p.snapshot()
        assert snap.module == "test_module"
        assert snap.counters["requests"] == 5
        assert snap.histograms["latency"]["avg"] == 100.0

    def test_snapshot_is_frozen(self) -> None:
        p = _TestPublisher()
        p.inc("requests")
        snap = p.snapshot()
        with pytest.raises(AttributeError):
            snap.module = "changed"  # type: ignore[misc]

    def test_prometheus_text(self) -> None:
        p = _TestPublisher()
        p.inc("requests", 10)
        text = p.export_prometheus_text()
        assert "requests 10" in text
        assert "# TYPE" in text

    def test_get_summary(self) -> None:
        p = _TestPublisher()
        p.inc("events", 3)
        summary = p.get_summary()
        assert summary["module"] == "test_module"
        assert "counters" in summary
        assert "histograms" in summary
        assert "timestamp" in summary
