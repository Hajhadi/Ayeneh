"""Tests for observability.diagnostics — DiagnosticsCollector, SubsystemHealth."""

from __future__ import annotations

import pytest

from ayeneh.observability.diagnostics import DiagnosticsCollector, SubsystemHealth


class TestSubsystemHealth:
    def test_construction(self) -> None:
        h = SubsystemHealth(name="db", status="healthy", version="1.0")
        assert h.name == "db"
        assert h.status == "healthy"
        assert h.version == "1.0"

    def test_frozen(self) -> None:
        h = SubsystemHealth(name="db", status="healthy")
        with pytest.raises(AttributeError):
            h.status = "unhealthy"  # type: ignore[misc]

    def test_defaults(self) -> None:
        h = SubsystemHealth(name="x", status="healthy")
        assert h.message == ""
        assert h.latency_ms == 0.0
        assert h.counters == {}
        assert h.last_check is not None


class TestDiagnosticsCollector:
    def test_empty_collector(self) -> None:
        c = DiagnosticsCollector()
        results = c.collect_all()
        assert results == {}
        assert c.overall_status() == "not_configured"

    def test_register_and_collect(self) -> None:
        c = DiagnosticsCollector()
        c.register("db", lambda: SubsystemHealth(name="db", status="healthy"))
        c.register("redis", lambda: SubsystemHealth(name="redis", status="healthy"))
        results = c.collect_all()
        assert len(results) == 2
        assert results["db"].status == "healthy"
        assert results["redis"].status == "healthy"

    def test_overall_status_healthy(self) -> None:
        c = DiagnosticsCollector()
        c.register("a", lambda: SubsystemHealth(name="a", status="healthy"))
        c.register("b", lambda: SubsystemHealth(name="b", status="healthy"))
        assert c.overall_status() == "healthy"

    def test_overall_status_degraded(self) -> None:
        c = DiagnosticsCollector()
        c.register("a", lambda: SubsystemHealth(name="a", status="healthy"))
        c.register("b", lambda: SubsystemHealth(name="b", status="degraded"))
        assert c.overall_status() == "degraded"

    def test_overall_status_unhealthy(self) -> None:
        c = DiagnosticsCollector()
        c.register("a", lambda: SubsystemHealth(name="a", status="healthy"))
        c.register("b", lambda: SubsystemHealth(name="b", status="unhealthy"))
        assert c.overall_status() == "unhealthy"

    def test_check_raises_exception(self) -> None:
        c = DiagnosticsCollector()
        c.register("broken", (_ for _ in ()).throw)  # type: ignore[arg-type]
        # Replace with proper raising function
        c._subsystems["broken"] = lambda: (_ for _ in ()).throw(RuntimeError("boom"))  # type: ignore
        results = c.collect_all()
        assert results["broken"].status == "unhealthy"
        assert "boom" in results["broken"].message

    def test_check_returns_none(self) -> None:
        c = DiagnosticsCollector()
        c.register("none_sub", lambda: None)
        results = c.collect_all()
        assert results["none_sub"].status == "not_configured"

    def test_export(self) -> None:
        c = DiagnosticsCollector()
        c.register("svc", lambda: SubsystemHealth(name="svc", status="healthy", version="2.0"))
        report = c.export()
        assert report["overall_status"] == "healthy"
        assert report["total_subsystems"] == 1
        assert "timestamp" in report
        assert report["subsystems"]["svc"]["status"] == "healthy"
        assert report["subsystems"]["svc"]["version"] == "2.0"

    def test_export_is_json_serializable(self) -> None:
        import json
        c = DiagnosticsCollector()
        c.register("svc", lambda: SubsystemHealth(name="svc", status="healthy"))
        report = c.export()
        serialized = json.dumps(report)
        assert isinstance(serialized, str)
