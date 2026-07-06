"""SELF-04 Self-Consistency Engine — 8-phase consistency pipeline."""

from __future__ import annotations

import time
import uuid
from typing import Any

import structlog

from ayeneh.self_arch.self_consistency.types import (
    CONSISTENCY_LEVELS,
    CONSISTENCY_PHASES,
    CONFLICT_CATEGORIES,
    CONFIDENCE_DIMENSIONS,
    ConflictDescriptor,
    ConsistencyConfidence,
    ConsistencyObject,
    ConsistencyResult,
    CrossModuleRelationship,
    EvidenceItem,
    ExplainabilityMetadata,
    HealthIndicator,
    IntegrityCheck,
    ModuleConsistencyStatus,
    ResolutionAction,
)

logger = structlog.get_logger(__name__)

# Default modules in the Ayeneh architecture for cross-module analysis
DEFAULT_ARCHITECTURE_MODULES: list[str] = [
    'cog', 'inf', 'dlg', 'dec', 'act', 'int', 'memo', 'self',
]

# Default module relationships
DEFAULT_RELATIONSHIPS: list[tuple[str, str, str]] = [
    ('cog', 'inf', 'data_dependency'),
    ('cog', 'dlg', 'control_flow'),
    ('inf', 'dec', 'data_dependency'),
    ('dec', 'act', 'control_flow'),
    ('act', 'int', 'feedback_loop'),
    ('int', 'cog', 'state_update'),
    ('memo', 'cog', 'data_dependency'),
    ('memo', 'inf', 'data_dependency'),
    ('self', 'int', 'monitoring'),
    ('self', 'cog', 'introspection'),
]


class SelfConsistencyEngine:
    """Ensures internal consistency across all cognitive modules through an 8-phase pipeline.

    Phases:
        1. ArchitectureState     — snapshot the current architecture state
        2. CrossModuleAnalysis   — analyze relationships between modules
        3. ConsistencyDetection  — detect consistency at each level
        4. ConflictIdentification — identify specific conflicts
        5. EvidenceEvaluation    — evaluate evidence for/against consistency
        6. ConsistencyResolution — resolve detected conflicts
        7. IntegrityUpdate       — update integrity status
        8. ArchitectureHealth    — compute overall architecture health
    """

    def __init__(self, modules: list[str] | None = None) -> None:
        self._modules = modules or list(DEFAULT_ARCHITECTURE_MODULES)

    def check(
        self,
        context: dict[str, Any] | None = None,
        session_id: str = '',
    ) -> ConsistencyResult:
        """Run the full 8-phase consistency check pipeline."""
        start = time.monotonic()
        ctx = context or {}
        errors: list[str] = []

        logger.info(
            "consistency_check_started",
            session_id=session_id,
            modules=len(self._modules),
        )

        # Phase 1: ArchitectureState
        arch_state = self._phase_architecture_state(ctx, errors)

        # Phase 2: CrossModuleAnalysis
        relationships = self._phase_cross_module_analysis(ctx, errors)

        # Phase 3: ConsistencyDetection
        module_statuses = self._phase_consistency_detection(arch_state, relationships, ctx, errors)

        # Phase 4: ConflictIdentification
        conflicts = self._phase_conflict_identification(module_statuses, relationships, errors)

        # Phase 5: EvidenceEvaluation
        evidence = self._phase_evidence_evaluation(conflicts, module_statuses, ctx, errors)

        # Phase 6: ConsistencyResolution
        resolutions = self._phase_consistency_resolution(conflicts, evidence, errors)

        # Phase 7: IntegrityUpdate
        integrity_checks = self._phase_integrity_update(module_statuses, resolutions, errors)

        # Phase 8: ArchitectureHealth
        health_indicators = self._phase_architecture_health(
            module_statuses, conflicts, resolutions, integrity_checks, errors,
        )

        # Compute overall confidence
        confidence = self._compute_confidence(
            module_statuses, conflicts, resolutions, health_indicators,
        )

        # Build the consistency object
        consistency_id = str(uuid.uuid4())
        affected_modules = tuple(s.module_name for s in module_statuses if s.score < 0.7)
        conflict_dicts = tuple({
            'conflict_id': c.conflict_id,
            'category': c.category,
            'severity': c.severity,
            'description': c.description,
        } for c in conflicts)

        overall_status = 'consistent'
        if any(c.severity in ('high', 'critical') for c in conflicts):
            overall_status = 'inconsistent'
        elif any(c.severity == 'medium' for c in conflicts):
            overall_status = 'partially_consistent'

        obj = ConsistencyObject(
            consistency_id=consistency_id,
            affected_modules=affected_modules,
            consistency_type=overall_status,
            supporting_evidence=tuple(e.evidence_id for e in evidence),
            detected_conflicts=conflict_dicts,
            resolution_status='resolved' if resolutions else 'unresolved',
            confidence=confidence,
            architectural_impact=self._assess_architectural_impact(conflicts, health_indicators),
            recommended_actions=self._generate_recommendations(conflicts, health_indicators),
            explainability_metadata={
                'reasoning_chain': (
                    f"Analyzed {len(self._modules)} modules",
                    f"Detected {len(conflicts)} conflicts",
                    f"Applied {len(resolutions)} resolutions",
                    f"Architecture health: {confidence:.2f}",
                ),
                'modules_checked': list(self._modules),
                'consistency_levels_checked': CONSISTENCY_LEVELS,
            },
        )

        duration_ms = (time.monotonic() - start) * 1000

        logger.info(
            "consistency_check_completed",
            consistency_id=consistency_id,
            conflicts=len(conflicts),
            confidence=confidence,
            duration_ms=duration_ms,
        )

        return ConsistencyResult(
            consistency_id=consistency_id,
            consistency_object=obj,
            module_statuses=tuple(module_statuses),
            conflicts=tuple(conflicts),
            relationships=tuple(relationships),
            evidence=tuple(evidence),
            resolutions=tuple(resolutions),
            integrity_checks=tuple(integrity_checks),
            health_indicators=tuple(health_indicators),
            confidence=confidence,
            duration_ms=duration_ms,
            errors=tuple(errors),
        )

    # ------------------------------------------------------------------
    # Phase implementations
    # ------------------------------------------------------------------

    def _phase_architecture_state(
        self,
        ctx: dict[str, Any],
        errors: list[str],
    ) -> dict[str, Any]:
        """Phase 1: Snapshot the current architecture state."""
        try:
            state = {
                'modules': self._modules,
                'module_count': len(self._modules),
                'timestamp': time.time(),
                'context_keys': list(ctx.keys()),
                'architecture_version': ctx.get('architecture_version', '1.0.0'),
            }
            logger.debug("phase_architecture_state_completed", modules=len(self._modules))
            return state
        except Exception as exc:
            errors.append(f"Phase 1 (ArchitectureState) error: {exc}")
            return {'modules': self._modules, 'module_count': len(self._modules)}

    def _phase_cross_module_analysis(
        self,
        ctx: dict[str, Any],
        errors: list[str],
    ) -> list[CrossModuleRelationship]:
        """Phase 2: Analyze relationships between modules."""
        try:
            relationships: list[CrossModuleRelationship] = []
            for source, target, rel_type in DEFAULT_RELATIONSHIPS:
                if source in self._modules and target in self._modules:
                    relationships.append(CrossModuleRelationship(
                        source_module=source,
                        target_module=target,
                        relationship_type=rel_type,
                        consistency_score=0.85,  # default good score
                        is_bidirectional=rel_type == 'feedback_loop',
                    ))

            # Add context-specified relationships
            for rel in ctx.get('relationships', []):
                if isinstance(rel, dict):
                    relationships.append(CrossModuleRelationship(
                        source_module=rel.get('source', ''),
                        target_module=rel.get('target', ''),
                        relationship_type=rel.get('type', 'data_dependency'),
                        consistency_score=rel.get('score', 0.8),
                    ))

            logger.debug("phase_cross_module_analysis_completed", relationships=len(relationships))
            return relationships
        except Exception as exc:
            errors.append(f"Phase 2 (CrossModuleAnalysis) error: {exc}")
            return []

    def _phase_consistency_detection(
        self,
        arch_state: dict[str, Any],
        relationships: list[CrossModuleRelationship],
        ctx: dict[str, Any],
        errors: list[str],
    ) -> list[ModuleConsistencyStatus]:
        """Phase 3: Detect consistency at each level for each module."""
        try:
            statuses: list[ModuleConsistencyStatus] = []
            for module in self._modules:
                # Base score from context or default
                base_score = ctx.get('module_scores', {}).get(module, 0.85)
                # Adjust based on relationships
                rel_scores = [
                    r.consistency_score for r in relationships
                    if r.source_module == module or r.target_module == module
                ]
                avg_rel_score = sum(rel_scores) / len(rel_scores) if rel_scores else base_score

                score = (base_score + avg_rel_score) / 2.0
                conflicts_count = sum(1 for r in rel_scores if r < 0.7)

                status = 'consistent' if score >= 0.8 else 'partially_consistent' if score >= 0.5 else 'inconsistent'

                statuses.append(ModuleConsistencyStatus(
                    module_name=module,
                    consistency_level=status,
                    score=score,
                    conflicts_detected=conflicts_count,
                    details=f"Score: {score:.2f}, {conflicts_count} potential conflicts",
                ))

            logger.debug("phase_consistency_detection_completed", modules=len(statuses))
            return statuses
        except Exception as exc:
            errors.append(f"Phase 3 (ConsistencyDetection) error: {exc}")
            return [ModuleConsistencyStatus(module_name=m) for m in self._modules]

    def _phase_conflict_identification(
        self,
        module_statuses: list[ModuleConsistencyStatus],
        relationships: list[CrossModuleRelationship],
        errors: list[str],
    ) -> list[ConflictDescriptor]:
        """Phase 4: Identify specific conflicts between modules."""
        try:
            conflicts: list[ConflictDescriptor] = []
            conflict_idx = 0

            # Check for inconsistent modules
            for status in module_statuses:
                if status.score < 0.7:
                    conflicts.append(ConflictDescriptor(
                        conflict_id=f"conflict_{conflict_idx}",
                        category='behavioral_inconsistency',
                        description=f"Module '{status.module_name}' has low consistency score: {status.score:.2f}",
                        severity='high' if status.score < 0.4 else 'medium',
                        affected_modules=(status.module_name,),
                        evidence=(status.details,),
                        resolution_status='unresolved',
                    ))
                    conflict_idx += 1

            # Check relationship-based conflicts
            for rel in relationships:
                if rel.consistency_score < 0.6:
                    conflicts.append(ConflictDescriptor(
                        conflict_id=f"conflict_{conflict_idx}",
                        category='dependency_inconsistency',
                        description=(
                            f"Weak consistency between '{rel.source_module}' and "
                            f"'{rel.target_module}' (score: {rel.consistency_score:.2f})"
                        ),
                        severity='high' if rel.consistency_score < 0.3 else 'medium',
                        affected_modules=(rel.source_module, rel.target_module),
                        evidence=(f"Relationship type: {rel.relationship_type}",),
                        resolution_status='unresolved',
                    ))
                    conflict_idx += 1

            # Check for version mismatches from context
            for mismatch in errors:
                if 'version' in mismatch.lower():
                    conflicts.append(ConflictDescriptor(
                        conflict_id=f"conflict_{conflict_idx}",
                        category='version_mismatch',
                        description=mismatch,
                        severity='medium',
                        affected_modules=tuple(self._modules[:2]),
                        resolution_status='unresolved',
                    ))
                    conflict_idx += 1

            logger.debug("phase_conflict_identification_completed", conflicts=len(conflicts))
            return conflicts
        except Exception as exc:
            errors.append(f"Phase 4 (ConflictIdentification) error: {exc}")
            return []

    def _phase_evidence_evaluation(
        self,
        conflicts: list[ConflictDescriptor],
        module_statuses: list[ModuleConsistencyStatus],
        ctx: dict[str, Any],
        errors: list[str],
    ) -> list[EvidenceItem]:
        """Phase 5: Evaluate evidence for and against consistency."""
        try:
            evidence: list[EvidenceItem] = []
            evidence_idx = 0

            # Evidence from module statuses
            for status in module_statuses:
                supports = status.score >= 0.7
                evidence.append(EvidenceItem(
                    evidence_id=f"ev_{evidence_idx}",
                    source=status.module_name,
                    content=f"Module consistency score: {status.score:.2f}",
                    reliability=status.score,
                    supports_consistency=supports,
                ))
                evidence_idx += 1

            # Evidence from conflicts
            for conflict in conflicts:
                evidence.append(EvidenceItem(
                    evidence_id=f"ev_{evidence_idx}",
                    source=conflict.conflict_id,
                    content=conflict.description,
                    reliability=0.7 if conflict.severity == 'medium' else 0.9,
                    supports_consistency=False,
                ))
                evidence_idx += 1

            # Evidence from context
            for ev in ctx.get('evidence', []):
                if isinstance(ev, dict):
                    evidence.append(EvidenceItem(
                        evidence_id=f"ev_{evidence_idx}",
                        source=ev.get('source', 'context'),
                        content=ev.get('content', ''),
                        reliability=ev.get('reliability', 0.7),
                        supports_consistency=ev.get('supports_consistency', True),
                    ))
                    evidence_idx += 1

            logger.debug("phase_evidence_evaluation_completed", evidence=len(evidence))
            return evidence
        except Exception as exc:
            errors.append(f"Phase 5 (EvidenceEvaluation) error: {exc}")
            return []

    def _phase_consistency_resolution(
        self,
        conflicts: list[ConflictDescriptor],
        evidence: list[EvidenceItem],
        errors: list[str],
    ) -> list[ResolutionAction]:
        """Phase 6: Resolve detected conflicts."""
        try:
            resolutions: list[ResolutionAction] = []
            for conflict in conflicts:
                # Determine resolution strategy based on severity and category
                if conflict.severity == 'critical':
                    strategy = 'escalation'
                    outcome = 'requires_human_review'
                elif conflict.severity == 'high':
                    strategy = 'manual_review'
                    outcome = 'flagged_for_review'
                elif conflict.category == 'version_mismatch':
                    strategy = 'merge'
                    outcome = 'version_reconciled'
                elif conflict.category == 'dependency_inconsistency':
                    strategy = 'priority_override'
                    outcome = 'dependency_reordered'
                else:
                    strategy = 'automatic'
                    outcome = 'auto_resolved'

                confidence_impact = 0.05 if strategy == 'automatic' else -0.02

                resolutions.append(ResolutionAction(
                    action_id=f"res_{conflict.conflict_id}",
                    conflict_id=conflict.conflict_id,
                    strategy=strategy,
                    description=f"Resolution for {conflict.category}: {outcome}",
                    outcome=outcome,
                    confidence_impact=confidence_impact,
                ))

            logger.debug("phase_consistency_resolution_completed", resolutions=len(resolutions))
            return resolutions
        except Exception as exc:
            errors.append(f"Phase 6 (ConsistencyResolution) error: {exc}")
            return []

    def _phase_integrity_update(
        self,
        module_statuses: list[ModuleConsistencyStatus],
        resolutions: list[ResolutionAction],
        errors: list[str],
    ) -> list[IntegrityCheck]:
        """Phase 7: Update integrity status."""
        try:
            checks: list[IntegrityCheck] = []

            # Module integrity
            module_avg_score = (
                sum(s.score for s in module_statuses) / len(module_statuses)
                if module_statuses else 0.0
            )
            checks.append(IntegrityCheck(
                check_id=str(uuid.uuid4()),
                check_type='module_integrity',
                passed=module_avg_score >= 0.7,
                score=module_avg_score,
                details=f"Average module consistency: {module_avg_score:.2f}",
            ))

            # Resolution integrity
            auto_resolved = sum(1 for r in resolutions if r.outcome == 'auto_resolved')
            resolution_rate = auto_resolved / max(len(resolutions), 1)
            checks.append(IntegrityCheck(
                check_id=str(uuid.uuid4()),
                check_type='resolution_integrity',
                passed=resolution_rate >= 0.5,
                score=resolution_rate,
                details=f"Auto-resolution rate: {resolution_rate:.2%}",
            ))

            # Relationship integrity
            high_severity = sum(1 for r in resolutions if r.strategy in ('escalation', 'manual_review'))
            checks.append(IntegrityCheck(
                check_id=str(uuid.uuid4()),
                check_type='relationship_integrity',
                passed=high_severity == 0,
                score=1.0 - (high_severity * 0.2),
                details=f"High-severity issues: {high_severity}",
            ))

            logger.debug("phase_integrity_update_completed", checks=len(checks))
            return checks
        except Exception as exc:
            errors.append(f"Phase 7 (IntegrityUpdate) error: {exc}")
            return []

    def _phase_architecture_health(
        self,
        module_statuses: list[ModuleConsistencyStatus],
        conflicts: list[ConflictDescriptor],
        resolutions: list[ResolutionAction],
        integrity_checks: list[IntegrityCheck],
        errors: list[str],
    ) -> list[HealthIndicator]:
        """Phase 8: Compute overall architecture health."""
        try:
            indicators: list[HealthIndicator] = []

            # Module health
            module_health = (
                sum(s.score for s in module_statuses) / len(module_statuses)
                if module_statuses else 0.0
            )
            indicators.append(HealthIndicator(
                indicator_name='module_health',
                value=module_health,
                threshold=0.7,
                is_healthy=module_health >= 0.7,
                trend='stable',
            ))

            # Conflict health
            conflict_ratio = len(conflicts) / max(len(module_statuses), 1)
            conflict_health = max(0.0, 1.0 - conflict_ratio)
            indicators.append(HealthIndicator(
                indicator_name='conflict_health',
                value=conflict_health,
                threshold=0.6,
                is_healthy=conflict_health >= 0.6,
                trend='stable',
            ))

            # Resolution health
            resolution_health = (
                sum(1 for r in resolutions if r.outcome != 'requires_human_review') / max(len(resolutions), 1)
                if resolutions else 1.0
            )
            indicators.append(HealthIndicator(
                indicator_name='resolution_health',
                value=resolution_health,
                threshold=0.8,
                is_healthy=resolution_health >= 0.8,
                trend='stable',
            ))

            # Integrity health
            integrity_health = (
                sum(c.score for c in integrity_checks) / len(integrity_checks)
                if integrity_checks else 0.0
            )
            indicators.append(HealthIndicator(
                indicator_name='integrity_health',
                value=integrity_health,
                threshold=0.75,
                is_healthy=integrity_health >= 0.75,
                trend='stable',
            ))

            logger.debug("phase_architecture_health_completed", indicators=len(indicators))
            return indicators
        except Exception as exc:
            errors.append(f"Phase 8 (ArchitectureHealth) error: {exc}")
            return []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _compute_confidence(
        self,
        module_statuses: list[ModuleConsistencyStatus],
        conflicts: list[ConflictDescriptor],
        resolutions: list[ResolutionAction],
        health_indicators: list[HealthIndicator],
    ) -> float:
        """Compute overall consistency confidence."""
        components = []

        if module_statuses:
            components.append(sum(s.score for s in module_statuses) / len(module_statuses))

        if conflicts:
            severity_penalty = sum(
                0.3 if c.severity == 'critical' else 0.2 if c.severity == 'high' else 0.1 if c.severity == 'medium' else 0.05
                for c in conflicts
            )
            components.append(max(0.0, 1.0 - severity_penalty))

        if resolutions:
            resolution_success = sum(1 for r in resolutions if r.outcome != 'requires_human_review') / len(resolutions)
            components.append(resolution_success)

        if health_indicators:
            components.append(sum(h.value for h in health_indicators) / len(health_indicators))

        return sum(components) / len(components) if components else 0.5

    def _assess_architectural_impact(
        self,
        conflicts: list[ConflictDescriptor],
        health_indicators: list[HealthIndicator],
    ) -> str:
        """Assess the architectural impact of detected conflicts."""
        high_severity = sum(1 for c in conflicts if c.severity in ('high', 'critical'))
        unhealthy = sum(1 for h in health_indicators if not h.is_healthy)

        if high_severity >= 3 or unhealthy >= 2:
            return 'critical_architectural_impact'
        elif high_severity >= 1 or unhealthy >= 1:
            return 'moderate_architectural_impact'
        elif conflicts:
            return 'low_architectural_impact'
        return 'no_architectural_impact'

    def _generate_recommendations(
        self,
        conflicts: list[ConflictDescriptor],
        health_indicators: list[HealthIndicator],
    ) -> tuple[str, ...]:
        """Generate recommended actions based on findings."""
        recommendations: list[str] = []

        for conflict in conflicts:
            if conflict.severity in ('high', 'critical'):
                recommendations.append(
                    f"Review and resolve {conflict.category} affecting {', '.join(conflict.affected_modules)}"
                )

        for indicator in health_indicators:
            if not indicator.is_healthy:
                recommendations.append(
                    f"Investigate {indicator.indicator_name} (value: {indicator.value:.2f}, threshold: {indicator.threshold})"
                )

        if not recommendations:
            recommendations.append('No immediate action required — architecture is consistent')

        return tuple(recommendations)
