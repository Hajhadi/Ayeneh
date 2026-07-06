"""INT-01 Cognitive Orchestrator — 7-phase orchestration pipeline."""

from __future__ import annotations

import time
import uuid
from typing import Any

import structlog

from ayeneh.int.orchestrator.types import (
    CoordinationMessage,
    DependencyEdge,
    ExecutionStep,
    ExplainabilityMetadata,
    IntegrationResult,
    ModuleSelection,
    MODULE_CAPABILITIES,
    ORCHESTRATION_STATUSES,
    OrchestrationObject,
    OrchestrationResult,
)

logger = structlog.get_logger(__name__)


class CognitiveOrchestrator:
    """Orchestrates multi-module cognitive processing through a 7-phase pipeline.

    Phases:
        1. IntentAnalysis        — parse the task and identify what needs to happen
        2. ModuleSelection        — choose which modules participate
        3. DependencyResolution   — determine inter-module dependencies
        4. ExecutionScheduling    — build an ordered execution plan
        5. CrossModuleCoordination — simulate inter-module message exchange
        6. ResultIntegration      — merge outputs from all modules
        7. UnifiedResponse        — produce the final orchestration object
    """

    def __init__(self) -> None:
        self._available_modules: dict[str, tuple[str, ...]] = {}

    def register_module(self, module_id: str, capabilities: tuple[str, ...]) -> None:
        self._available_modules[module_id] = capabilities

    def orchestrate(
        self,
        task_description: str = '',
        task_id: str = '',
        context: dict[str, Any] | None = None,
        required_capabilities: list[str] | None = None,
        session_id: str = '',
    ) -> OrchestrationResult:
        start = time.monotonic()
        ctx = context or {}
        errors: list[str] = []
        required = required_capabilities or []

        logger.info(
            "orchestration_started",
            task_id=task_id,
            session_id=session_id,
            task=task_description[:80],
        )

        # Phase 1: IntentAnalysis
        intent = self._phase_intent_analysis(task_description, ctx, errors)

        # Phase 2: ModuleSelection
        selected = self._phase_module_selection(intent, required, errors)

        # Phase 3: DependencyResolution
        deps = self._phase_dependency_resolution(selected, errors)

        # Phase 4: ExecutionScheduling
        steps = self._phase_execution_scheduling(selected, deps, errors)

        # Phase 5: CrossModuleCoordination
        messages = self._phase_cross_module_coordination(selected, steps, errors)

        # Phase 6: ResultIntegration
        integration = self._phase_result_integration(selected, messages, errors)

        # Phase 7: UnifiedResponse
        orchestration_id = str(uuid.uuid4())
        obj = self._phase_unified_response(
            orchestration_id, task_id, selected, steps, integration, errors,
        )

        duration_ms = (time.monotonic() - start) * 1000

        logger.info(
            "orchestration_completed",
            orchestration_id=orchestration_id,
            modules=len(selected),
            confidence=obj.confidence,
            duration_ms=duration_ms,
        )

        return OrchestrationResult(
            orchestration_id=orchestration_id,
            orchestration_object=obj,
            selected_modules=tuple(selected),
            execution_steps=tuple(steps),
            integration=integration,
            confidence=obj.confidence,
            duration_ms=duration_ms,
            errors=tuple(errors),
        )

    # ------------------------------------------------------------------
    # Phase implementations
    # ------------------------------------------------------------------

    def _phase_intent_analysis(
        self,
        task_description: str,
        ctx: dict[str, Any],
        errors: list[str],
    ) -> dict[str, Any]:
        """Phase 1: Parse the task and identify what needs to happen."""
        try:
            intent = {
                'task_description': task_description,
                'intent_type': ctx.get('intent_type', 'general'),
                'complexity': ctx.get('complexity', 'medium'),
                'required_capabilities': ctx.get('required_capabilities', []),
                'constraints': ctx.get('constraints', []),
                'priority': ctx.get('priority', 0.5),
                'urgency': ctx.get('urgency', 'normal'),
            }
            logger.debug("phase_intent_analysis_completed")
            return intent
        except Exception as exc:
            errors.append(f"Phase 1 (IntentAnalysis) error: {exc}")
            return {'task_description': task_description, 'intent_type': 'general'}

    def _phase_module_selection(
        self,
        intent: dict[str, Any],
        required_capabilities: list[str],
        errors: list[str],
    ) -> list[ModuleSelection]:
        """Phase 2: Choose which modules participate."""
        try:
            selections: list[ModuleSelection] = []
            requested_caps = required_capabilities or intent.get('required_capabilities', [])

            for module_id, capabilities in self._available_modules.items():
                matched = [c for c in capabilities if c in requested_caps or not requested_caps]
                if matched:
                    selections.append(ModuleSelection(
                        module_id=module_id,
                        capability=matched[0],
                        priority=intent.get('priority', 0.5),
                        estimated_cost=1.0 / max(len(matched), 1),
                        selection_reasoning=f"Matches capabilities: {', '.join(matched)}",
                    ))

            # If no registered modules, create synthetic selections from requested caps
            if not selections and requested_caps:
                for i, cap in enumerate(requested_caps):
                    selections.append(ModuleSelection(
                        module_id=f"module_{i}",
                        capability=cap,
                        priority=intent.get('priority', 0.5),
                        selection_reasoning=f"Synthetic selection for required capability: {cap}",
                    ))

            # Ensure at least one selection
            if not selections:
                selections.append(ModuleSelection(
                    module_id='default_module',
                    capability='general',
                    priority=0.5,
                    selection_reasoning='Default selection — no specific capabilities requested',
                ))

            logger.debug("phase_module_selection_completed", count=len(selections))
            return selections
        except Exception as exc:
            errors.append(f"Phase 2 (ModuleSelection) error: {exc}")
            return [ModuleSelection(module_id='fallback', capability='general')]

    def _phase_dependency_resolution(
        self,
        selections: list[ModuleSelection],
        errors: list[str],
    ) -> list[DependencyEdge]:
        """Phase 3: Determine inter-module dependencies."""
        try:
            edges: list[DependencyEdge] = []
            for i, sel in enumerate(selections):
                if i > 0:
                    edges.append(DependencyEdge(
                        source=selections[i - 1].module_id,
                        target=sel.module_id,
                        dependency_type='data',
                        weight=0.8,
                        is_critical=True,
                    ))

            # Add capability-based dependencies
            cap_deps = {
                'knowledge_retrieval': ['memory_management'],
                'dialogue_processing': ['knowledge_retrieval'],
                'decision_making': ['inference'],
            }
            for sel in selections:
                for target_cap, source_caps in cap_deps.items():
                    if sel.capability == target_cap:
                        for other in selections:
                            if other.capability in source_caps:
                                edges.append(DependencyEdge(
                                    source=other.module_id,
                                    target=sel.module_id,
                                    dependency_type='control',
                                    weight=0.6,
                                    is_critical=False,
                                ))

            logger.debug("phase_dependency_resolution_completed", edges=len(edges))
            return edges
        except Exception as exc:
            errors.append(f"Phase 3 (DependencyResolution) error: {exc}")
            return []

    def _phase_execution_scheduling(
        self,
        selections: list[ModuleSelection],
        deps: list[DependencyEdge],
        errors: list[str],
    ) -> list[ExecutionStep]:
        """Phase 4: Build an ordered execution plan."""
        try:
            # Topological sort based on dependencies
            dep_map: dict[str, set[str]] = {}
            for sel in selections:
                dep_map[sel.module_id] = set()
            for edge in deps:
                if edge.target in dep_map:
                    dep_map[edge.target].add(edge.source)

            ordered: list[str] = []
            remaining = set(dep_map.keys())
            while remaining:
                ready = [m for m in remaining if not dep_map.get(m, set()) - set(ordered)]
                if not ready:
                    ready = list(remaining)
                for m in sorted(ready):
                    ordered.append(m)
                    remaining.discard(m)

            steps: list[ExecutionStep] = []
            sel_map = {s.module_id: s for s in selections}
            for i, module_id in enumerate(ordered):
                sel = sel_map.get(module_id, ModuleSelection(module_id=module_id))
                steps.append(ExecutionStep(
                    step_id=f"step_{i}",
                    module_id=module_id,
                    action=f"execute_{sel.capability}",
                    inputs=tuple(dep_map.get(module_id, set())),
                    outputs=(f"output_{module_id}",),
                    strategy='sequential' if i > 0 else 'sequential',
                    estimated_duration_ms=100.0,
                ))

            logger.debug("phase_execution_scheduling_completed", steps=len(steps))
            return steps
        except Exception as exc:
            errors.append(f"Phase 4 (ExecutionScheduling) error: {exc}")
            return [
                ExecutionStep(step_id=f"step_{i}", module_id=s.module_id, action="execute")
                for i, s in enumerate(selections)
            ]

    def _phase_cross_module_coordination(
        self,
        selections: list[ModuleSelection],
        steps: list[ExecutionStep],
        errors: list[str],
    ) -> list[CoordinationMessage]:
        """Phase 5: Simulate inter-module message exchange."""
        try:
            messages: list[CoordinationMessage] = []
            for i, step in enumerate(steps):
                if i > 0:
                    messages.append(CoordinationMessage(
                        source_module=steps[i - 1].module_id,
                        target_module=step.module_id,
                        message_type='data',
                        payload={'step_output': steps[i - 1].outputs[0] if steps[i - 1].outputs else ''},
                    ))
                # Acknowledgment
                messages.append(CoordinationMessage(
                    source_module=step.module_id,
                    target_module='orchestrator',
                    message_type='notification',
                    payload={'status': 'completed', 'step_id': step.step_id},
                ))

            logger.debug("phase_cross_module_coordination_completed", messages=len(messages))
            return messages
        except Exception as exc:
            errors.append(f"Phase 5 (CrossModuleCoordination) error: {exc}")
            return []

    def _phase_result_integration(
        self,
        selections: list[ModuleSelection],
        messages: list[CoordinationMessage],
        errors: list[str],
    ) -> IntegrationResult:
        """Phase 6: Merge outputs from all modules."""
        try:
            module_outputs: dict[str, Any] = {}
            for sel in selections:
                module_outputs[sel.module_id] = {
                    'capability': sel.capability,
                    'status': 'completed',
                    'output_available': True,
                }

            completion_count = sum(
                1 for m in messages
                if m.message_type == 'notification'
                and m.payload.get('status') == 'completed'
            )

            total_steps = len(selections)
            completion_ratio = completion_count / max(total_steps, 1)

            conflicts: list[dict[str, Any]] = []
            if len(selections) > 1:
                caps = [s.capability for s in selections]
                if len(caps) != len(set(caps)):
                    conflicts.append({
                        'type': 'capability_overlap',
                        'modules': [s.module_id for s in selections if s.capability in caps],
                        'severity': 'low',
                    })

            summary_parts = [
                f"Integrated {len(selections)} modules",
                f"completion_ratio={completion_ratio:.1%}",
            ]
            if conflicts:
                summary_parts.append(f"{len(conflicts)} conflict(s) detected")

            confidence = completion_ratio * 0.7 + (1.0 - min(len(conflicts) * 0.1, 0.3)) * 0.3

            return IntegrationResult(
                module_outputs=module_outputs,
                conflicts=tuple(conflicts),
                merged_summary='; '.join(summary_parts),
                confidence=confidence,
            )
        except Exception as exc:
            errors.append(f"Phase 6 (ResultIntegration) error: {exc}")
            return IntegrationResult(merged_summary=f"Integration failed: {exc}")

    def _phase_unified_response(
        self,
        orchestration_id: str,
        task_id: str,
        selections: list[ModuleSelection],
        steps: list[ExecutionStep],
        integration: IntegrationResult,
        errors: list[str],
    ) -> OrchestrationObject:
        """Phase 7: Produce the final orchestration object."""
        try:
            execution_graph = {
                'steps': [s.step_id for s in steps],
                'module_sequence': [s.module_id for s in steps],
            }
            dependency_graph = {
                'edges': [
                    {'source': inp, 'target': step.step_id}
                    for step in steps
                    for inp in step.inputs
                ],
            }
            execution_timeline = tuple(
                {
                    'step_id': s.step_id,
                    'module': s.module_id,
                    'action': s.action,
                    'estimated_duration_ms': s.estimated_duration_ms,
                }
                for s in steps
            )
            step_costs = {s.module_id: s.estimated_duration_ms for s in steps}
            resource_allocation = {
                s.module_id: {'capability': s.capability, 'cost': step_costs.get(s.module_id, 0.0)}
                for s in selections
            }

            explainability = ExplainabilityMetadata(
                reasoning_chain=(
                    f"Selected {len(selections)} modules for task",
                    f"Created {len(steps)} execution steps",
                    f"Integrated results with confidence {integration.confidence:.2f}",
                ),
                contributing_factors=tuple(
                    {'module': s.module_id, 'capability': s.capability}
                    for s in selections
                ),
                confidence_decomposition={
                    'module_selection': 0.8,
                    'integration_quality': integration.confidence,
                },
            )

            status = 'completed' if not errors else 'failed'

            obj = OrchestrationObject(
                orchestration_id=orchestration_id,
                task_id=task_id,
                participating_modules=tuple(s.module_id for s in selections),
                execution_graph=execution_graph,
                dependency_graph=dependency_graph,
                execution_timeline=execution_timeline,
                current_status=status,
                confidence=integration.confidence,
                resource_allocation=resource_allocation,
                final_integration_summary=integration.merged_summary,
                explainability_metadata={
                    'reasoning_chain': explainability.reasoning_chain,
                    'contributing_factors': explainability.contributing_factors,
                    'confidence_decomposition': explainability.confidence_decomposition,
                },
            )

            logger.debug("phase_unified_response_completed", status=status)
            return obj
        except Exception as exc:
            errors.append(f"Phase 7 (UnifiedResponse) error: {exc}")
            return OrchestrationObject(
                orchestration_id=orchestration_id,
                task_id=task_id,
                current_status='failed',
            )
