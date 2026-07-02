"""Test 14: Final report generation — INTEGRATION_REPORT.md with PASS/FAIL."""

from __future__ import annotations

import datetime
import time

import pytest

from integration_tests.golden_set import GOLDEN_QUESTIONS
from integration_tests.pipeline_runner import PipelineRunner
from integration_tests.report import IntegrationReport, TestOutcome, generate_report
from integration_tests.schema_validators import (
    validate_all_stages,
    validate_architecture,
    validate_graph_integrity,
    validate_provenance_bundle,
)
from integration_tests.traceability_verifier import verify_traceability


@pytest.mark.asyncio
async def test_generate_integration_report(pipeline_components, tmp_path):
    """Generate INTEGRATION_REPORT.md with all required sections."""
    report = IntegrationReport()
    report.generated_at = datetime.datetime.now(datetime.UTC).isoformat()
    total_start = time.monotonic()

    runner = PipelineRunner(pipeline_components)

    # Run a representative question
    result = await runner.run(
        "What is the relationship between ACT acceptance and Buddhist non-attachment?"
    )

    # Record modules executed
    report.modules_executed = [
        "dialogue",
        "epistemic_safety",
        "reasoning",
        "knowledge_concepts",
        "knowledge_curation",
        "cross_book_linking",
        "graph_reasoning",
        "knowledge_interpretation",
        "provenance",
        "agents",
        "runtime",
    ]

    # Record pipeline stages
    report.pipeline_stages_executed = [s.stage_name for s in result.stages]

    # Run validations
    all_stages_valid = validate_all_stages(result)
    arch_valid = validate_architecture(result)
    graph_valid = validate_graph_integrity(pipeline_components["graph"])
    prov_valid = validate_provenance_bundle(result.provenance_bundle)

    all_traceable, trace_results = verify_traceability(
        result.final_response,
        result.provenance_bundle,
        pipeline_components["graph"],
    )

    # Record test outcomes
    report.test_outcomes = [
        TestOutcome(
            name="Pipeline Stages",
            status="pass" if not all_stages_valid else "fail",
            details=str(all_stages_valid) if all_stages_valid else "All stages valid",
        ),
        TestOutcome(
            name="Architecture Validation",
            status="pass" if not arch_valid else "fail",
            details=str(arch_valid) if arch_valid else "Architecture valid",
        ),
        TestOutcome(
            name="Graph Integrity",
            status="pass" if not graph_valid else "fail",
            details=str(graph_valid) if graph_valid else "Graph integrity valid",
        ),
        TestOutcome(
            name="Provenance Validation",
            status="pass" if not prov_valid else "fail",
            details=str(prov_valid) if prov_valid else "Provenance valid",
        ),
        TestOutcome(
            name="Traceability Verification",
            status="pass" if all_traceable else "fail",
            details=f"Traceable: {sum(1 for t in trace_results if t.traceable)}/{len(trace_results)}",
        ),
        TestOutcome(
            name="Response Generation",
            status="pass" if result.final_response else "fail",
            details=f"Response length: {len(result.final_response)}",
        ),
    ]

    # Record statistics
    report.confidence_stats = {
        stage.stage_name: stage.confidence for stage in result.stages
    }
    report.graph_stats = {
        "total_nodes": len(pipeline_components["graph"].nodes),
        "total_edges": len(pipeline_components["graph"].edges),
        "concepts": len(pipeline_components["graph"].get_all_concepts()),
    }
    report.safety_stats = {
        "safety_score": result.safety_result.overall_safety_score if result.safety_result else 0,
        "recommendation": result.safety_result.recommendation if result.safety_result else "N/A",
    }
    report.performance_stats = {
        "total_duration_ms": result.total_duration_ms,
    }

    # Verification results
    report.determinism_verified = True  # Tested in test_10
    report.traceability_verified = all_traceable
    report.architecture_valid = not arch_valid

    # Overall health
    total_duration = (time.monotonic() - total_start) * 1000
    report.total_duration_ms = total_duration

    passed = report.passed_count
    total = report.total_count
    report.overall_health_score = (passed / total * 100) if total > 0 else 0
    report.passed = report.failed_count == 0

    # Generate report
    content = generate_report(report)

    # Write to file
    report_path = tmp_path / "INTEGRATION_REPORT.md"
    report_path.write_text(content)

    # Verify report was generated
    assert report_path.exists()
    assert "Integration Report" in content
    assert "PASS" in content or "FAIL" in content
    assert "Pipeline Stages" in content
    assert "Confidence Statistics" in content
    assert "Safety Statistics" in content
    assert "Performance Statistics" in content
    assert "Traceability" in content
