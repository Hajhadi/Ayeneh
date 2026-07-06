"""SELF-05 Self-Evolution Engine — 8-phase evolution pipeline."""

from __future__ import annotations

import time
import uuid
from typing import Any

import structlog

from ayeneh.self_arch.self_evolution.types import (
    APPROVAL_STATUSES,
    EVOLUTION_CATEGORIES,
    EVOLUTION_PHASES,
    IMPACT_CATEGORIES,
    RISK_LEVELS,
    CapabilityOpportunity,
    EvolutionObject,
    EvolutionProposal,
    EvolutionResult,
    OperationalRecord,
    RiskAssessment,
    TrendAnalysis,
    VersionUpdate,
)

logger = structlog.get_logger(__name__)

# Default metrics tracked for longitudinal analysis
DEFAULT_METRICS: list[str] = [
    'response_quality',
    'retrieval_accuracy',
    'reasoning_depth',
    'safety_score',
    'user_satisfaction',
    'module_health',
    'consistency_score',
]

# Default modules
DEFAULT_MODULES: list[str] = [
    'cog', 'inf', 'dlg', 'dec', 'act', 'int', 'memo', 'self',
]


class SelfEvolutionEngine:
    """Drives architectural evolution through an 8-phase pipeline.

    Phases:
        1. OperationalHistory    — gather historical operational data
        2. LongitudinalAnalysis  — analyze trends over time
        3. CapabilityOpportunities — identify improvement opportunities
        4. EvolutionProposal     — propose specific evolution changes
        5. ConsistencyValidation — validate proposals against architecture
        6. RiskAssessment        — assess risks of proposed changes
        7. ApprovedEvolution     — approve/reject/defer proposals
        8. ArchitectureVersionUpdate — apply approved changes and update version
    """

    def __init__(
        self,
        modules: list[str] | None = None,
        architecture_version: str = '1.0.0',
    ) -> None:
        self._modules = modules or list(DEFAULT_MODULES)
        self._architecture_version = architecture_version

    def evolve(
        self,
        context: dict[str, Any] | None = None,
        session_id: str = '',
    ) -> EvolutionResult:
        """Run the full 8-phase evolution pipeline."""
        start = time.monotonic()
        ctx = context or {}
        errors: list[str] = []

        logger.info(
            "evolution_started",
            session_id=session_id,
            architecture_version=self._architecture_version,
        )

        # Phase 1: OperationalHistory
        records = self._phase_operational_history(ctx, errors)

        # Phase 2: LongitudinalAnalysis
        trends = self._phase_longitudinal_analysis(records, ctx, errors)

        # Phase 3: CapabilityOpportunities
        opportunities = self._phase_capability_opportunities(trends, ctx, errors)

        # Phase 4: EvolutionProposal
        proposals = self._phase_evolution_proposal(opportunities, ctx, errors)

        # Phase 5: ConsistencyValidation
        validated_proposals = self._phase_consistency_validation(proposals, ctx, errors)

        # Phase 6: RiskAssessment
        risk_assessments = self._phase_risk_assessment(validated_proposals, ctx, errors)

        # Phase 7: ApprovedEvolution
        approved_proposals = self._phase_approved_evolution(
            validated_proposals, risk_assessments, ctx, errors,
        )

        # Phase 8: ArchitectureVersionUpdate
        version_updates = self._phase_architecture_version_update(
            approved_proposals, errors,
        )

        # Compute overall confidence
        confidence = self._compute_confidence(
            records, trends, opportunities, approved_proposals, risk_assessments,
        )

        # Build the evolution object
        evolution_id = str(uuid.uuid4())
        affected_modules = tuple(
            m for m in self._modules
            if any(m in p.affected_modules for p in approved_proposals)
        )

        proposal_summary = '; '.join(p.title for p in approved_proposals) if approved_proposals else 'No proposals approved'
        motivation_parts = [p.motivation for p in approved_proposals if p.motivation]
        motivation = '; '.join(motivation_parts) if motivation_parts else 'Continuous improvement'

        evidence_parts = []
        for trend in trends:
            evidence_parts.append(f"{trend.metric_name}: {trend.direction} (magnitude: {trend.magnitude:.2f})")
        supporting_evidence = tuple(evidence_parts) if evidence_parts else ('Initial baseline assessment',)

        benefit_parts = []
        for p in approved_proposals:
            benefit_parts.extend(p.expected_benefits)
        expected_benefits = tuple(benefit_parts) if benefit_parts else ('Improved consistency', 'Better performance')

        risk_parts = []
        for ra in risk_assessments:
            risk_parts.append(f"{ra.risk_level}: {ra.risk_description}")
        known_risks = tuple(risk_parts) if risk_parts else ('Minimal risk with approved changes',)

        approval_status = 'approved' if approved_proposals else 'proposed'

        obj = EvolutionObject(
            evolution_id=evolution_id,
            architecture_version=self._architecture_version,
            proposal=proposal_summary,
            motivation=motivation,
            supporting_evidence=supporting_evidence,
            affected_modules=affected_modules,
            expected_benefits=expected_benefits,
            known_risks=known_risks,
            approval_status=approval_status,
            implementation_history=tuple({
                'update_id': vu.update_id,
                'previous_version': vu.previous_version,
                'new_version': vu.new_version,
                'change_summary': vu.change_summary,
            } for vu in version_updates),
            version_metadata={
                'current_version': self._architecture_version,
                'proposals_evaluated': len(proposals),
                'proposals_approved': len(approved_proposals),
                'risks_assessed': len(risk_assessments),
            },
            explainability_metadata={
                'reasoning_chain': (
                    f"Analyzed {len(records)} operational records",
                    f"Identified {len(trends)} trends",
                    f"Found {len(opportunities)} opportunities",
                    f"Generated {len(proposals)} proposals",
                    f"Approved {len(approved_proposals)} proposals",
                    f"Applied {len(version_updates)} version updates",
                ),
                'modules_evolved': list(affected_modules),
                'evolution_categories': list(set(p.category for p in approved_proposals)),
            },
        )

        duration_ms = (time.monotonic() - start) * 1000

        logger.info(
            "evolution_completed",
            evolution_id=evolution_id,
            proposals_approved=len(approved_proposals),
            confidence=confidence,
            duration_ms=duration_ms,
        )

        return EvolutionResult(
            evolution_id=evolution_id,
            evolution_object=obj,
            operational_records=tuple(records),
            trends=tuple(trends),
            opportunities=tuple(opportunities),
            proposals=tuple(approved_proposals),
            risk_assessments=tuple(risk_assessments),
            version_updates=tuple(version_updates),
            confidence=confidence,
            duration_ms=duration_ms,
            errors=tuple(errors),
        )

    # ------------------------------------------------------------------
    # Phase implementations
    # ------------------------------------------------------------------

    def _phase_operational_history(
        self,
        ctx: dict[str, Any],
        errors: list[str],
    ) -> list[OperationalRecord]:
        """Phase 1: Gather historical operational data."""
        try:
            records: list[OperationalRecord] = []
            record_idx = 0

            # Use context-provided records
            for rec in ctx.get('operational_records', []):
                if isinstance(rec, dict):
                    records.append(OperationalRecord(
                        record_id=rec.get('id', f"rec_{record_idx}"),
                        module=rec.get('module', ''),
                        metric_name=rec.get('metric', ''),
                        metric_value=rec.get('value', 0.0),
                        context=rec.get('context', {}),
                    ))
                    record_idx += 1

            # Generate synthetic baseline records if none provided
            if not records:
                for module in self._modules:
                    for metric in DEFAULT_METRICS[:3]:
                        records.append(OperationalRecord(
                            record_id=f"rec_{record_idx}",
                            module=module,
                            metric_name=metric,
                            metric_value=0.8,  # baseline
                            context={'source': 'baseline'},
                        ))
                        record_idx += 1

            logger.debug("phase_operational_history_completed", records=len(records))
            return records
        except Exception as exc:
            errors.append(f"Phase 1 (OperationalHistory) error: {exc}")
            return []

    def _phase_longitudinal_analysis(
        self,
        records: list[OperationalRecord],
        ctx: dict[str, Any],
        errors: list[str],
    ) -> list[TrendAnalysis]:
        """Phase 2: Analyze trends over time."""
        try:
            trends: list[TrendAnalysis] = []

            # Group records by metric
            metric_records: dict[str, list[OperationalRecord]] = {}
            for rec in records:
                if rec.metric_name not in metric_records:
                    metric_records[rec.metric_name] = []
                metric_records[rec.metric_name].append(rec)

            for metric_name, metric_recs in metric_records.items():
                values = [r.metric_value for r in metric_recs]
                avg_value = sum(values) / len(values) if values else 0.0
                modules = tuple(set(r.module for r in metric_recs))

                # Simple trend detection
                if len(values) >= 2:
                    first_half = values[:len(values) // 2]
                    second_half = values[len(values) // 2:]
                    first_avg = sum(first_half) / len(first_half) if first_half else 0.0
                    second_avg = sum(second_half) / len(second_half) if second_half else 0.0
                    diff = second_avg - first_avg

                    if diff > 0.05:
                        direction = 'improving'
                    elif diff < -0.05:
                        direction = 'degrading'
                    else:
                        direction = 'stable'
                    magnitude = abs(diff)
                else:
                    direction = 'stable'
                    magnitude = 0.0

                trends.append(TrendAnalysis(
                    trend_id=str(uuid.uuid4()),
                    metric_name=metric_name,
                    direction=direction,
                    magnitude=magnitude,
                    confidence=min(1.0, len(values) * 0.2),
                    affected_modules=modules,
                    data_points=len(values),
                ))

            # Check context-provided trends
            for trend_data in ctx.get('trends', []):
                if isinstance(trend_data, dict):
                    trends.append(TrendAnalysis(
                        trend_id=trend_data.get('id', str(uuid.uuid4())),
                        metric_name=trend_data.get('metric', ''),
                        direction=trend_data.get('direction', 'stable'),
                        magnitude=trend_data.get('magnitude', 0.0),
                        confidence=trend_data.get('confidence', 0.5),
                        affected_modules=tuple(trend_data.get('modules', [])),
                    ))

            logger.debug("phase_longitudinal_analysis_completed", trends=len(trends))
            return trends
        except Exception as exc:
            errors.append(f"Phase 2 (LongitudinalAnalysis) error: {exc}")
            return []

    def _phase_capability_opportunities(
        self,
        trends: list[TrendAnalysis],
        ctx: dict[str, Any],
        errors: list[str],
    ) -> list[CapabilityOpportunity]:
        """Phase 3: Identify improvement opportunities."""
        try:
            opportunities: list[CapabilityOpportunity] = []
            opp_idx = 0

            # Identify opportunities from degrading trends
            for trend in trends:
                if trend.direction == 'degrading':
                    opportunities.append(CapabilityOpportunity(
                        opportunity_id=f"opp_{opp_idx}",
                        category='performance_optimization',
                        description=f"Reverse degrading trend in {trend.metric_name}",
                        current_state=f"{trend.metric_name} is degrading (magnitude: {trend.magnitude:.2f})",
                        desired_state=f"{trend.metric_name} should be stable or improving",
                        affected_modules=trend.affected_modules,
                        priority=0.8 if trend.magnitude > 0.2 else 0.6,
                        evidence=(f"Trend magnitude: {trend.magnitude:.2f}",),
                    ))
                    opp_idx += 1

            # Identify opportunities from improving trends (amplify)
            for trend in trends:
                if trend.direction == 'improving' and trend.magnitude > 0.1:
                    opportunities.append(CapabilityOpportunity(
                        opportunity_id=f"opp_{opp_idx}",
                        category='capability_expansion',
                        description=f"Amplify improving trend in {trend.metric_name}",
                        current_state=f"{trend.metric_name} is improving",
                        desired_state=f"Accelerate improvement in {trend.metric_name}",
                        affected_modules=trend.affected_modules,
                        priority=0.5,
                        evidence=(f"Improvement magnitude: {trend.magnitude:.2f}",),
                    ))
                    opp_idx += 1

            # Check context-provided opportunities
            for opp_data in ctx.get('opportunities', []):
                if isinstance(opp_data, dict):
                    opportunities.append(CapabilityOpportunity(
                        opportunity_id=opp_data.get('id', f"opp_{opp_idx}"),
                        category=opp_data.get('category', 'capability_expansion'),
                        description=opp_data.get('description', ''),
                        current_state=opp_data.get('current_state', ''),
                        desired_state=opp_data.get('desired_state', ''),
                        affected_modules=tuple(opp_data.get('modules', [])),
                        priority=opp_data.get('priority', 0.5),
                    ))
                    opp_idx += 1

            # Ensure at least one opportunity exists
            if not opportunities:
                opportunities.append(CapabilityOpportunity(
                    opportunity_id=f"opp_{opp_idx}",
                    category='capability_refinement',
                    description='Continuous architecture refinement',
                    current_state='Baseline architecture state',
                    desired_state='Improved architecture through incremental refinement',
                    affected_modules=tuple(self._modules),
                    priority=0.3,
                    evidence=('Baseline assessment',),
                ))

            logger.debug("phase_capability_opportunities_completed", opportunities=len(opportunities))
            return opportunities
        except Exception as exc:
            errors.append(f"Phase 3 (CapabilityOpportunities) error: {exc}")
            return []

    def _phase_evolution_proposal(
        self,
        opportunities: list[CapabilityOpportunity],
        ctx: dict[str, Any],
        errors: list[str],
    ) -> list[EvolutionProposal]:
        """Phase 4: Propose specific evolution changes."""
        try:
            proposals: list[EvolutionProposal] = []

            for opp in opportunities:
                proposal = EvolutionProposal(
                    proposal_id=str(uuid.uuid4()),
                    category=opp.category,
                    title=f"Evolution: {opp.description[:60]}",
                    description=opp.description,
                    motivation=f"Opportunity identified: {opp.current_state} -> {opp.desired_state}",
                    expected_benefits=(f"Improved {opp.category.replace('_', ' ')}",),
                    affected_modules=opp.affected_modules,
                    implementation_steps=(
                        f"Analyze current state of {', '.join(opp.affected_modules)}",
                        f"Implement changes for {opp.category}",
                        "Validate changes through testing",
                        "Deploy and monitor",
                    ),
                    rollback_plan=f"Revert changes to {', '.join(opp.affected_modules)} if issues detected",
                    priority=opp.priority,
                )
                proposals.append(proposal)

            logger.debug("phase_evolution_proposal_completed", proposals=len(proposals))
            return proposals
        except Exception as exc:
            errors.append(f"Phase 4 (EvolutionProposal) error: {exc}")
            return []

    def _phase_consistency_validation(
        self,
        proposals: list[EvolutionProposal],
        ctx: dict[str, Any],
        errors: list[str],
    ) -> list[EvolutionProposal]:
        """Phase 5: Validate proposals against architecture consistency."""
        try:
            validated: list[EvolutionProposal] = []

            for proposal in proposals:
                # Check if proposal affects modules not in our architecture
                unknown_modules = [m for m in proposal.affected_modules if m not in self._modules]

                if unknown_modules:
                    errors.append(
                        f"Proposal {proposal.proposal_id} affects unknown modules: {unknown_modules}"
                    )
                    continue

                # Validate category
                if proposal.category not in EVOLUTION_CATEGORIES:
                    errors.append(
                        f"Proposal {proposal.proposal_id} has invalid category: {proposal.category}"
                    )
                    continue

                validated.append(proposal)

            # If all proposals were rejected, include at least the highest priority one
            if not validated and proposals:
                validated.append(proposals[0])

            logger.debug("phase_consistency_validation_completed", validated=len(validated))
            return validated
        except Exception as exc:
            errors.append(f"Phase 5 (ConsistencyValidation) error: {exc}")
            return proposals

    def _phase_risk_assessment(
        self,
        proposals: list[EvolutionProposal],
        ctx: dict[str, Any],
        errors: list[str],
    ) -> list[RiskAssessment]:
        """Phase 6: Assess risks of proposed changes."""
        try:
            assessments: list[RiskAssessment] = []

            for proposal in proposals:
                # Determine risk level based on scope and category
                num_modules = len(proposal.affected_modules)
                if num_modules > 4:
                    risk_level = 'high'
                    probability = 0.6
                    severity = 0.7
                elif num_modules > 2:
                    risk_level = 'medium'
                    probability = 0.4
                    severity = 0.5
                else:
                    risk_level = 'low'
                    probability = 0.2
                    severity = 0.3

                # Safety enhancements have lower risk
                if proposal.category == 'safety_enhancement':
                    risk_level = 'negligible'
                    probability = 0.1
                    severity = 0.2

                # Architectural refactoring has higher risk
                if proposal.category == 'architectural_refactoring':
                    risk_level = 'high' if num_modules > 2 else 'medium'
                    probability = 0.5
                    severity = 0.6

                mitigation = f"Implement incrementally with rollback capability for {', '.join(proposal.affected_modules)}"

                assessments.append(RiskAssessment(
                    risk_id=str(uuid.uuid4()),
                    proposal_id=proposal.proposal_id,
                    risk_level=risk_level,
                    risk_description=f"Risk of changing {', '.join(proposal.affected_modules)} ({proposal.category})",
                    mitigation_strategy=mitigation,
                    impact_areas=tuple(IMPACT_CATEGORIES[:min(num_modules, len(IMPACT_CATEGORIES))]),
                    probability=probability,
                    severity=severity,
                ))

            logger.debug("phase_risk_assessment_completed", assessments=len(assessments))
            return assessments
        except Exception as exc:
            errors.append(f"Phase 6 (RiskAssessment) error: {exc}")
            return []

    def _phase_approved_evolution(
        self,
        proposals: list[EvolutionProposal],
        risk_assessments: list[RiskAssessment],
        ctx: dict[str, Any],
        errors: list[str],
    ) -> list[EvolutionProposal]:
        """Phase 7: Approve, reject, or defer proposals."""
        try:
            approved: list[EvolutionProposal] = []
            risk_map = {ra.proposal_id: ra for ra in risk_assessments}

            # Check context for explicit approvals/rejections
            approved_ids = set(ctx.get('approved_proposals', []))
            rejected_ids = set(ctx.get('rejected_proposals', []))

            for proposal in proposals:
                # Explicit rejection
                if proposal.proposal_id in rejected_ids:
                    continue

                # Explicit approval
                if proposal.proposal_id in approved_ids:
                    approved.append(proposal)
                    continue

                # Auto-approve based on risk
                risk = risk_map.get(proposal.proposal_id)
                if risk and risk.risk_level in ('negligible', 'low'):
                    approved.append(proposal)
                elif risk and risk.risk_level == 'medium' and proposal.priority >= 0.6:
                    approved.append(proposal)
                elif proposal.priority >= 0.8:
                    # High priority overrides medium risk
                    approved.append(proposal)
                # else: not approved (implicitly deferred)

            # Ensure at least one proposal is approved if there are any
            if not approved and proposals:
                approved.append(proposals[0])

            logger.debug("phase_approved_evolution_completed", approved=len(approved))
            return approved
        except Exception as exc:
            errors.append(f"Phase 7 (ApprovedEvolution) error: {exc}")
            return []

    def _phase_architecture_version_update(
        self,
        approved_proposals: list[EvolutionProposal],
        errors: list[str],
    ) -> list[VersionUpdate]:
        """Phase 8: Apply approved changes and update version."""
        try:
            updates: list[VersionUpdate] = []

            if not approved_proposals:
                return updates

            # Parse current version
            parts = self._architecture_version.split('.')
            major = int(parts[0]) if len(parts) > 0 else 1
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0

            # Determine version bump based on change categories
            categories = set(p.category for p in approved_proposals)
            if 'architectural_refactoring' in categories:
                minor += 1
                patch = 0
            elif any(c in categories for c in ('capability_expansion', 'capability_refinement')):
                patch += 1
            else:
                patch += 1

            new_version = f"{major}.{minor}.{patch}"

            updates.append(VersionUpdate(
                update_id=str(uuid.uuid4()),
                previous_version=self._architecture_version,
                new_version=new_version,
                change_summary=f"Applied {len(approved_proposals)} evolution proposals",
                modules_affected=tuple(
                    m for p in approved_proposals for m in p.affected_modules
                ),
                is_rollback=False,
            ))

            # Update internal version
            self._architecture_version = new_version

            logger.debug("phase_architecture_version_update_completed", new_version=new_version)
            return updates
        except Exception as exc:
            errors.append(f"Phase 8 (ArchitectureVersionUpdate) error: {exc}")
            return []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _compute_confidence(
        self,
        records: list[OperationalRecord],
        trends: list[TrendAnalysis],
        opportunities: list[CapabilityOpportunity],
        approved_proposals: list[EvolutionProposal],
        risk_assessments: list[RiskAssessment],
    ) -> float:
        """Compute overall evolution confidence."""
        components = []

        # Data confidence (more records = higher confidence)
        data_confidence = min(1.0, len(records) * 0.1) if records else 0.3
        components.append(data_confidence)

        # Trend confidence
        if trends:
            trend_confidence = sum(t.confidence for t in trends) / len(trends)
            components.append(trend_confidence)

        # Risk confidence (lower risk = higher confidence)
        if risk_assessments:
            risk_confidence = 1.0 - sum(
                0.3 if ra.risk_level == 'high' else 0.2 if ra.risk_level == 'medium' else 0.1 if ra.risk_level == 'low' else 0.0
                for ra in risk_assessments
            ) / max(len(risk_assessments), 1)
            components.append(max(0.0, risk_confidence))

        # Proposal confidence
        if approved_proposals:
            components.append(0.8)  # base confidence for having approved proposals

        return sum(components) / len(components) if components else 0.5
