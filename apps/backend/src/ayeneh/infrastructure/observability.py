"""OpenTelemetry tracing and Prometheus metrics configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class TracingConfig:
    enabled: bool = False
    service_name: str = "ayeneh-api"
    endpoint: str = "http://localhost:4317"
    sample_rate: float = 1.0


@dataclass
class PrometheusMetrics:
    """In-memory Prometheus-style metrics counters.

    In production, these would be backed by prometheus_client.
    """

    request_count: dict[str, int] = field(default_factory=dict)
    request_duration_ms: dict[str, float] = field(default_factory=dict)
    error_count: dict[str, int] = field(default_factory=dict)
    llm_call_count: int = 0
    llm_call_duration_ms: float = 0.0
    embedding_call_count: int = 0
    embedding_call_duration_ms: float = 0.0
    memory_operations: dict[str, int] = field(default_factory=dict)
    evolution_operations: dict[str, int] = field(default_factory=dict)

    # Epistemic retrieval metrics
    epistemic_ranking_count: int = 0
    epistemic_ranking_duration_ms: float = 0.0
    epistemic_scope_filtered_count: int = 0
    epistemic_domain_distribution: dict[str, int] = field(default_factory=dict)
    epistemic_authority_distribution: dict[str, int] = field(default_factory=dict)
    epistemic_selection_reasons: dict[str, int] = field(default_factory=dict)

    # Epistemic analysis metrics
    epistemic_analysis_count: int = 0
    epistemic_analysis_duration_ms: float = 0.0
    epistemic_confidence_distribution: dict[str, int] = field(default_factory=dict)
    epistemic_framework_distribution: dict[str, int] = field(default_factory=dict)
    epistemic_intent_distribution: dict[str, int] = field(default_factory=dict)
    epistemic_uncertainty_requests: int = 0
    epistemic_cross_framework_requests: int = 0

    # Dialogue metrics
    dialogue_decision_count: int = 0
    dialogue_decision_duration_ms: float = 0.0
    dialogue_intervention_distribution: dict[str, int] = field(default_factory=dict)
    dialogue_dependency_risk_sum: float = 0.0
    dialogue_reflection_ratio: float = 0.0
    dialogue_question_ratio: float = 0.0
    dialogue_advice_ratio: float = 0.0
    dialogue_silence_ratio: float = 0.0
    dialogue_uncertainty_ratio: float = 0.0
    dialogue_policy_usage: dict[str, int] = field(default_factory=dict)
    dialogue_confidence_distribution: dict[str, int] = field(default_factory=dict)

    def record_request(self, method: str, path: str, status: int, duration_ms: float) -> None:
        key = f"{method}:{path}:{status}"
        self.request_count[key] = self.request_count.get(key, 0) + 1
        self.request_duration_ms[key] = self.request_duration_ms.get(key, 0) + duration_ms
        if status >= 400:
            self.error_count[key] = self.error_count.get(key, 0) + 1

    def record_llm_call(self, model: str, duration_ms: float) -> None:
        self.llm_call_count += 1
        self.llm_call_duration_ms += duration_ms

    def record_embedding_call(self, duration_ms: float) -> None:
        self.embedding_call_count += 1
        self.embedding_call_duration_ms += duration_ms

    def record_memory_operation(self, op: str) -> None:
        self.memory_operations[op] = self.memory_operations.get(op, 0) + 1

    def record_evolution_operation(self, op: str) -> None:
        self.evolution_operations[op] = self.evolution_operations.get(op, 0) + 1

    def record_epistemic_ranking(
        self,
        duration_ms: float,
        scope_filtered: int,
        domain_dist: dict[str, int],
        authority_dist: dict[str, int],
        selection_reasons: list[str],
    ) -> None:
        """Record epistemic retrieval ranking metrics."""
        self.epistemic_ranking_count += 1
        self.epistemic_ranking_duration_ms += duration_ms
        self.epistemic_scope_filtered_count += scope_filtered
        for domain, count in domain_dist.items():
            self.epistemic_domain_distribution[domain] = (
                self.epistemic_domain_distribution.get(domain, 0) + count
            )
        for authority, count in authority_dist.items():
            self.epistemic_authority_distribution[authority] = (
                self.epistemic_authority_distribution.get(authority, 0) + count
            )
        for reason in selection_reasons:
            # Normalize reason for aggregation
            key = reason[:50] if len(reason) > 50 else reason
            self.epistemic_selection_reasons[key] = (
                self.epistemic_selection_reasons.get(key, 0) + 1
            )

    def record_epistemic_analysis(
        self,
        duration_ms: float,
        confidence: float,
        frameworks: list[str],
        intent: str,
        requires_uncertainty: bool,
        cross_framework: bool,
    ) -> None:
        """Record epistemic analysis metrics."""
        self.epistemic_analysis_count += 1
        self.epistemic_analysis_duration_ms += duration_ms

        # Confidence distribution (bucketed)
        bucket = f"{int(confidence * 10) * 10}-{int(confidence * 10) * 10 + 10}"
        self.epistemic_confidence_distribution[bucket] = (
            self.epistemic_confidence_distribution.get(bucket, 0) + 1
        )

        for fw in frameworks:
            self.epistemic_framework_distribution[fw] = (
                self.epistemic_framework_distribution.get(fw, 0) + 1
            )

        self.epistemic_intent_distribution[intent] = (
            self.epistemic_intent_distribution.get(intent, 0) + 1
        )

        if requires_uncertainty:
            self.epistemic_uncertainty_requests += 1
        if cross_framework:
            self.epistemic_cross_framework_requests += 1

    def record_dialogue_decision(
        self,
        duration_ms: float,
        intervention: str,
        dependency_risk: float,
        confidence: float,
        policies_applied: list[str],
    ) -> None:
        """Record dialogue decision metrics."""
        self.dialogue_decision_count += 1
        self.dialogue_decision_duration_ms += duration_ms

        self.dialogue_intervention_distribution[intervention] = (
            self.dialogue_intervention_distribution.get(intervention, 0) + 1
        )

        self.dialogue_dependency_risk_sum += dependency_risk

        # Update ratios
        total = self.dialogue_decision_count
        if intervention in ("reflective_question", "observation_mirror", "pattern_reflection"):
            self.dialogue_reflection_ratio = (
                self.dialogue_reflection_ratio * (total - 1) + 1
            ) / total
        if intervention == "reflective_question":
            self.dialogue_question_ratio = (
                self.dialogue_question_ratio * (total - 1) + 1
            ) / total
        if intervention in ("knowledge_explanation", "evidence_presentation"):
            self.dialogue_advice_ratio = (
                self.dialogue_advice_ratio * (total - 1) + 1
            ) / total
        if intervention == "silence":
            self.dialogue_silence_ratio = (
                self.dialogue_silence_ratio * (total - 1) + 1
            ) / total
        if intervention == "uncertainty_statement":
            self.dialogue_uncertainty_ratio = (
                self.dialogue_uncertainty_ratio * (total - 1) + 1
            ) / total

        for policy in policies_applied:
            self.dialogue_policy_usage[policy] = (
                self.dialogue_policy_usage.get(policy, 0) + 1
            )

        bucket = f"{int(confidence * 10) * 10}-{int(confidence * 10) * 10 + 10}"
        self.dialogue_confidence_distribution[bucket] = (
            self.dialogue_confidence_distribution.get(bucket, 0) + 1
        )

    def export_prometheus_text(self) -> str:
        lines = []
        lines.append("# HELP ayeneh_requests_total Total HTTP requests")
        lines.append("# TYPE ayeneh_requests_total counter")
        for key, val in self.request_count.items():
            lines.append(f'ayeneh_requests_total{{route="{key}"}} {val}')

        lines.append("# HELP ayeneh_errors_total Total errors")
        lines.append("# TYPE ayeneh_errors_total counter")
        for key, val in self.error_count.items():
            lines.append(f'ayeneh_errors_total{{route="{key}"}} {val}')

        lines.append(f"# HELP ayeneh_llm_calls_total Total LLM calls")
        lines.append(f"# TYPE ayeneh_llm_calls_total counter")
        lines.append(f"ayeneh_llm_calls_total {self.llm_call_count}")

        lines.append(f"# HELP ayeneh_embedding_calls_total Total embedding calls")
        lines.append(f"# TYPE ayeneh_embedding_calls_total counter")
        lines.append(f"ayeneh_embedding_calls_total {self.embedding_call_count}")

        lines.append(f"# HELP ayeneh_llm_duration_ms_total Total LLM call duration")
        lines.append(f"# TYPE ayeneh_llm_duration_ms_total counter")
        lines.append(f"ayeneh_llm_duration_ms_total {self.llm_call_duration_ms:.2f}")

        lines.append(f"# HELP ayeneh_embedding_duration_ms_total Total embedding duration")
        lines.append(f"# TYPE ayeneh_embedding_duration_ms_total counter")
        lines.append(f"ayeneh_embedding_duration_ms_total {self.embedding_call_duration_ms:.2f}")

        # Epistemic retrieval metrics
        lines.append("# HELP ayeneh_epistemic_rankings_total Total epistemic rankings")
        lines.append("# TYPE ayeneh_epistemic_rankings_total counter")
        lines.append(f"ayeneh_epistemic_rankings_total {self.epistemic_ranking_count}")

        lines.append("# HELP ayeneh_epistemic_ranking_duration_ms_total Total ranking duration")
        lines.append("# TYPE ayeneh_epistemic_ranking_duration_ms_total counter")
        lines.append(f"ayeneh_epistemic_ranking_duration_ms_total {self.epistemic_ranking_duration_ms:.2f}")

        lines.append("# HELP ayeneh_epistemic_scope_filtered_total Scope-filtered sources")
        lines.append("# TYPE ayeneh_epistemic_scope_filtered_total counter")
        lines.append(f"ayeneh_epistemic_scope_filtered_total {self.epistemic_scope_filtered_count}")

        lines.append("# HELP ayeneh_epistemic_domain_distribution Epistemic domain distribution")
        lines.append("# TYPE ayeneh_epistemic_domain_distribution counter")
        for domain, count in self.epistemic_domain_distribution.items():
            lines.append(f'ayeneh_epistemic_domain_distribution{{domain="{domain}"}} {count}')

        lines.append("# HELP ayeneh_epistemic_authority_distribution Epistemic authority distribution")
        lines.append("# TYPE ayeneh_epistemic_authority_distribution counter")
        for authority, count in self.epistemic_authority_distribution.items():
            lines.append(f'ayeneh_epistemic_authority_distribution{{authority="{authority}"}} {count}')

        # Epistemic analysis metrics
        lines.append("# HELP ayeneh_epistemic_analyses_total Total epistemic analyses")
        lines.append("# TYPE ayeneh_epistemic_analyses_total counter")
        lines.append(f"ayeneh_epistemic_analyses_total {self.epistemic_analysis_count}")

        lines.append("# HELP ayeneh_epistemic_analysis_duration_ms_total Total analysis duration")
        lines.append("# TYPE ayeneh_epistemic_analysis_duration_ms_total counter")
        lines.append(f"ayeneh_epistemic_analysis_duration_ms_total {self.epistemic_analysis_duration_ms:.2f}")

        lines.append("# HELP ayeneh_epistemic_confidence_distribution Confidence distribution")
        lines.append("# TYPE ayeneh_epistemic_confidence_distribution counter")
        for bucket, count in self.epistemic_confidence_distribution.items():
            lines.append(f'ayeneh_epistemic_confidence_distribution{{bucket="{bucket}"}} {count}')

        lines.append("# HELP ayeneh_epistemic_framework_distribution Framework distribution")
        lines.append("# TYPE ayeneh_epistemic_framework_distribution counter")
        for fw, count in self.epistemic_framework_distribution.items():
            lines.append(f'ayeneh_epistemic_framework_distribution{{framework="{fw}"}} {count}')

        lines.append("# HELP ayeneh_epistemic_intent_distribution Intent distribution")
        lines.append("# TYPE ayeneh_epistemic_intent_distribution counter")
        for intent, count in self.epistemic_intent_distribution.items():
            lines.append(f'ayeneh_epistemic_intent_distribution{{intent="{intent}"}} {count}')

        lines.append("# HELP ayeneh_epistemic_uncertainty_requests Uncertainty requests")
        lines.append("# TYPE ayeneh_epistemic_uncertainty_requests counter")
        lines.append(f"ayeneh_epistemic_uncertainty_requests {self.epistemic_uncertainty_requests}")

        lines.append("# HELP ayeneh_epistemic_cross_framework_requests Cross-framework requests")
        lines.append("# TYPE ayeneh_epistemic_cross_framework_requests counter")
        lines.append(f"ayeneh_epistemic_cross_framework_requests {self.epistemic_cross_framework_requests}")

        # Dialogue metrics
        lines.append("# HELP ayeneh_dialogue_decisions_total Total dialogue decisions")
        lines.append("# TYPE ayeneh_dialogue_decisions_total counter")
        lines.append(f"ayeneh_dialogue_decisions_total {self.dialogue_decision_count}")

        lines.append("# HELP ayeneh_dialogue_decision_duration_ms_total Total decision duration")
        lines.append("# TYPE ayeneh_dialogue_decision_duration_ms_total counter")
        lines.append(f"ayeneh_dialogue_decision_duration_ms_total {self.dialogue_decision_duration_ms:.2f}")

        lines.append("# HELP ayeneh_dialogue_intervention_distribution Intervention distribution")
        lines.append("# TYPE ayeneh_dialogue_intervention_distribution counter")
        for intervention, count in self.dialogue_intervention_distribution.items():
            lines.append(f'ayeneh_dialogue_intervention_distribution{{intervention="{intervention}"}} {count}')

        avg_risk = self.dialogue_dependency_risk_sum / max(1, self.dialogue_decision_count)
        lines.append("# HELP ayeneh_dialogue_avg_dependency_risk Average dependency risk")
        lines.append("# TYPE ayeneh_dialogue_avg_dependency_risk gauge")
        lines.append(f"ayeneh_dialogue_avg_dependency_risk {avg_risk:.4f}")

        lines.append("# HELP ayeneh_dialogue_reflection_ratio Reflection ratio")
        lines.append("# TYPE ayeneh_dialogue_reflection_ratio gauge")
        lines.append(f"ayeneh_dialogue_reflection_ratio {self.dialogue_reflection_ratio:.4f}")

        lines.append("# HELP ayeneh_dialogue_question_ratio Question ratio")
        lines.append("# TYPE ayeneh_dialogue_question_ratio gauge")
        lines.append(f"ayeneh_dialogue_question_ratio {self.dialogue_question_ratio:.4f}")

        lines.append("# HELP ayeneh_dialogue_silence_ratio Silence ratio")
        lines.append("# TYPE ayeneh_dialogue_silence_ratio gauge")
        lines.append(f"ayeneh_dialogue_silence_ratio {self.dialogue_silence_ratio:.4f}")

        lines.append("# HELP ayeneh_dialogue_uncertainty_ratio Uncertainty ratio")
        lines.append("# TYPE ayeneh_dialogue_uncertainty_ratio gauge")
        lines.append(f"ayeneh_dialogue_uncertainty_ratio {self.dialogue_uncertainty_ratio:.4f}")

        lines.append("# HELP ayeneh_dialogue_policy_usage Policy usage")
        lines.append("# TYPE ayeneh_dialogue_policy_usage counter")
        for policy, count in self.dialogue_policy_usage.items():
            lines.append(f'ayeneh_dialogue_policy_usage{{policy="{policy}"}} {count}')

        lines.append("# HELP ayeneh_dialogue_confidence_distribution Confidence distribution")
        lines.append("# TYPE ayeneh_dialogue_confidence_distribution counter")
        for bucket, count in self.dialogue_confidence_distribution.items():
            lines.append(f'ayeneh_dialogue_confidence_distribution{{bucket="{bucket}"}} {count}')

        return "\n".join(lines) + "\n"


def setup_tracing(config: TracingConfig) -> Any:
    """Configure OpenTelemetry tracing. Returns the tracer or None."""
    if not config.enabled:
        return None

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({
            "service.name": config.service_name,
            "service.version": "0.1.0",
        })
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=config.endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        tracer = trace.get_tracer(config.service_name)
        logger.info("tracing_configured", endpoint=config.endpoint)
        return tracer
    except ImportError:
        logger.warning("opentelemetry_not_installed")
        return None
    except Exception as exc:
        logger.warning("tracing_setup_failed", error=str(exc))
        return None
