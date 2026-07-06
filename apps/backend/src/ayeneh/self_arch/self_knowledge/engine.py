"""SELF-03 Self-Knowledge Engine.

7-phase pipeline for constructing and maintaining a SelfKnowledgeObject:

1. OperationalEvidence — gather operational evidence about the system
2. SelfModel — integrate self-model data as evidence source
3. Verification — verify knowledge claims against evidence
4. KnowledgeClassification — classify knowledge into categories
5. ConfidenceCalibration — calibrate confidence levels
6. KnowledgeIntegration — integrate new knowledge with existing
7. SelfKnowledgeBase — assemble and return the updated knowledge base
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from ayeneh.self_arch.self_knowledge.types import (
    EPISTEMIC_STATUSES,
    KNOWLEDGE_CATEGORIES,
    SelfKnowledgeObject,
)

logger = structlog.get_logger(__name__)

# Default knowledge claims for initial system state
_DEFAULT_KNOWLEDGE: tuple[dict[str, Any], ...] = (
    {
        'statement': 'System operates via a multi-module pipeline architecture',
        'category': 'architectural_assumptions',
        'confidence': 0.9,
        'verification_status': 'strongly_supported',
        'evidence': ('module_discovery_results', 'architecture_documentation'),
    },
    {
        'statement': 'Context window limits the depth of multi-step reasoning',
        'category': 'verified_limitations',
        'confidence': 0.85,
        'verification_status': 'verified',
        'evidence': ('operational_observation', 'performance_benchmark'),
    },
    {
        'statement': 'Episodic memory retrieval accuracy degrades with temporal distance',
        'category': 'behavioral_tendencies',
        'confidence': 0.75,
        'verification_status': 'strongly_supported',
        'evidence': ('memory_retrieval_tests', 'user_feedback'),
    },
    {
        'statement': 'Dialogue state tracking maintains coherence across turns',
        'category': 'verified_capabilities',
        'confidence': 0.8,
        'verification_status': 'strongly_supported',
        'evidence': ('state_machine_tests', 'conversation_analysis'),
    },
    {
        'statement': 'Self-model accuracy is limited by introspection capabilities',
        'category': 'verified_limitations',
        'confidence': 0.7,
        'verification_status': 'provisionally_supported',
        'evidence': ('self_model_analysis', 'comparison_with_behavior'),
    },
)

# Validation targets for future knowledge expansion
_DEFAULT_VALIDATION_TARGETS: tuple[str, ...] = (
    'validate_reasoning_depth_limits',
    'verify_memory_retrieval_accuracy',
    'assess_dialogue_coherence_over_long_conversations',
    'test_self_model_vs_actual_behavior_alignment',
    'evaluate_cross_module_consistency',
)


class SelfKnowledgeEngine:
    """Constructs and maintains SelfKnowledgeObjects through a 7-phase pipeline (SELF-03)."""

    def __init__(self, ai_router: Any = None) -> None:
        self._ai_router = ai_router
        self._knowledge_entries: list[SelfKnowledgeObject] = []
        self._knowledge_index: dict[str, int] = {}

    @property
    def knowledge_entries(self) -> list[SelfKnowledgeObject]:
        """Return current knowledge entries."""
        return list(self._knowledge_entries)

    @property
    def knowledge_count(self) -> int:
        """Return the number of knowledge entries."""
        return len(self._knowledge_entries)

    def build(
        self,
        operational_data: dict[str, Any] | None = None,
        self_model_data: dict[str, Any] | None = None,
        existing_knowledge: tuple[SelfKnowledgeObject, ...] | None = None,
    ) -> tuple[SelfKnowledgeObject, ...]:
        """Run the full 7-phase self-knowledge pipeline.

        Returns a tuple of all SelfKnowledgeObjects in the knowledge base.
        """
        logger.info('self03_pipeline_start')

        # Phase 1 — OperationalEvidence
        evidence = self._phase_operational_evidence(operational_data)

        # Phase 2 — SelfModel
        model_evidence = self._phase_self_model(self_model_data)

        # Phase 3 — Verification
        verified_claims = self._phase_verification(evidence, model_evidence)

        # Phase 4 — KnowledgeClassification
        classified = self._phase_knowledge_classification(verified_claims)

        # Phase 5 — ConfidenceCalibration
        calibrated = self._phase_confidence_calibration(classified)

        # Phase 6 — KnowledgeIntegration
        integrated = self._phase_knowledge_integration(
            calibrated, existing_knowledge,
        )

        # Phase 7 — SelfKnowledgeBase
        knowledge_base = self._phase_self_knowledge_base(integrated)

        logger.info(
            'self03_pipeline_end',
            knowledge_count=len(knowledge_base),
        )
        return tuple(knowledge_base)

    # ------------------------------------------------------------------
    # Phase 1 — OperationalEvidence
    # ------------------------------------------------------------------

    def _phase_operational_evidence(
        self, operational_data: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        """Gather operational evidence about the system."""
        evidence: list[dict[str, Any]] = []

        if operational_data is not None:
            # Extract evidence from operational data
            if 'module_status' in operational_data:
                for mod, status in operational_data['module_status'].items():
                    evidence.append({
                        'type': 'direct_observation',
                        'description': f'Module {mod} status: {status}',
                        'reliability': 0.9 if status == 'active' else 0.5,
                    })

            if 'error_count' in operational_data:
                evidence.append({
                    'type': 'failure_analysis',
                    'description': f'System error count: {operational_data["error_count"]}',
                    'reliability': 0.85,
                })

            if 'response_times' in operational_data:
                evidence.append({
                    'type': 'operational_data',
                    'description': f'Average response time: {operational_data["response_times"]}',
                    'reliability': 0.8,
                })

        # Always include default evidence from system introspection
        evidence.append({
            'type': 'direct_observation',
            'description': 'System pipeline architecture confirmed operational',
            'reliability': 0.9,
        })

        logger.debug(
            'phase_1_operational_evidence',
            evidence_count=len(evidence),
        )
        return evidence

    # ------------------------------------------------------------------
    # Phase 2 — SelfModel
    # ------------------------------------------------------------------

    def _phase_self_model(
        self, self_model_data: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        """Integrate self-model data as evidence source."""
        evidence: list[dict[str, Any]] = []

        if self_model_data is not None:
            if 'capabilities' in self_model_data:
                for cap in self_model_data['capabilities']:
                    evidence.append({
                        'type': 'self_report',
                        'description': f'Reported capability: {cap}',
                        'reliability': 0.7,
                    })

            if 'limitations' in self_model_data:
                for lim in self_model_data['limitations']:
                    evidence.append({
                        'type': 'self_report',
                        'description': f'Reported limitation: {lim}',
                        'reliability': 0.75,
                    })

        logger.debug(
            'phase_2_self_model',
            evidence_count=len(evidence),
        )
        return evidence

    # ------------------------------------------------------------------
    # Phase 3 — Verification
    # ------------------------------------------------------------------

    def _phase_verification(
        self,
        operational_evidence: list[dict[str, Any]],
        model_evidence: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Verify knowledge claims against evidence."""
        all_evidence = operational_evidence + model_evidence
        claims: list[dict[str, Any]] = []

        # Verify default knowledge claims against available evidence
        for claim in _DEFAULT_KNOWLEDGE:
            verification_score = self._verify_claim(claim, all_evidence)
            claims.append({
                **claim,
                'verification_score': verification_score,
                'evidence_count': len(all_evidence),
            })

        logger.debug(
            'phase_3_verification',
            claim_count=len(claims),
        )
        return claims

    def _verify_claim(
        self,
        claim: dict[str, Any],
        evidence: list[dict[str, Any]],
    ) -> float:
        """Verify a single claim against available evidence."""
        claim_confidence = claim.get('confidence', 0.0)
        evidence_reliability = 0.0

        if evidence:
            reliabilities = [e.get('reliability', 0.5) for e in evidence]
            evidence_reliability = sum(reliabilities) / len(reliabilities)

        return round((claim_confidence + evidence_reliability) / 2.0, 4)

    # ------------------------------------------------------------------
    # Phase 4 — KnowledgeClassification
    # ------------------------------------------------------------------

    def _phase_knowledge_classification(
        self, claims: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Classify knowledge into categories."""
        classified: list[dict[str, Any]] = []

        for claim in claims:
            category = claim.get('category', 'open_questions')
            if category not in KNOWLEDGE_CATEGORIES:
                category = 'open_questions'

            classified.append({
                **claim,
                'classified_category': category,
            })

        logger.debug(
            'phase_4_knowledge_classification',
            classified_count=len(classified),
        )
        return classified

    # ------------------------------------------------------------------
    # Phase 5 — ConfidenceCalibration
    # ------------------------------------------------------------------

    def _phase_confidence_calibration(
        self, classified: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Calibrate confidence levels based on evidence quality."""
        calibrated: list[dict[str, Any]] = []

        for entry in classified:
            raw_confidence = entry.get('confidence', 0.0)
            verification_score = entry.get('verification_score', 0.0)
            evidence_count = entry.get('evidence_count', 0)

            # Calibration: weight by evidence quantity and quality
            evidence_factor = min(1.0, evidence_count / 5.0)
            calibrated_confidence = (
                raw_confidence * 0.4
                + verification_score * 0.4
                + evidence_factor * 0.2
            )

            calibrated.append({
                **entry,
                'calibrated_confidence': round(min(1.0, calibrated_confidence), 4),
            })

        logger.debug(
            'phase_5_confidence_calibration',
            calibrated_count=len(calibrated),
        )
        return calibrated

    # ------------------------------------------------------------------
    # Phase 6 — KnowledgeIntegration
    # ------------------------------------------------------------------

    def _phase_knowledge_integration(
        self,
        calibrated: list[dict[str, Any]],
        existing_knowledge: tuple[SelfKnowledgeObject, ...] | None,
    ) -> list[SelfKnowledgeObject]:
        """Integrate new knowledge with existing knowledge base."""
        integrated: list[SelfKnowledgeObject] = []

        # Add existing knowledge first
        if existing_knowledge is not None:
            integrated.extend(existing_knowledge)

        # Add or update with calibrated claims
        for entry in calibrated:
            statement = entry.get('statement', '')
            # Check if this statement already exists
            existing_idx = None
            for i, existing in enumerate(integrated):
                if existing.statement == statement:
                    existing_idx = i
                    break

            knowledge_obj = SelfKnowledgeObject(
                knowledge_id=str(uuid.uuid4()),
                statement=statement,
                evidence_sources=tuple(entry.get('evidence', ())),
                confidence=entry.get('calibrated_confidence', entry.get('confidence', 0.0)),
                verification_status=entry.get('verification_status', 'unknown'),
                associated_modules=(),
                revision_history=(),
                known_exceptions=(),
                applicable_contexts=(entry.get('classified_category', ''),),
                future_validation_targets=_DEFAULT_VALIDATION_TARGETS,
            )

            if existing_idx is not None:
                integrated[existing_idx] = knowledge_obj
            else:
                integrated.append(knowledge_obj)

        logger.debug(
            'phase_6_knowledge_integration',
            total_count=len(integrated),
        )
        return integrated

    # ------------------------------------------------------------------
    # Phase 7 — SelfKnowledgeBase
    # ------------------------------------------------------------------

    def _phase_self_knowledge_base(
        self, integrated: list[SelfKnowledgeObject],
    ) -> list[SelfKnowledgeObject]:
        """Assemble and return the updated knowledge base."""
        self._knowledge_entries = integrated
        self._knowledge_index = {
            entry.knowledge_id: i
            for i, entry in enumerate(integrated)
        }

        # Update internal tracking
        for entry in integrated:
            logger.debug(
                'self03_knowledge_entry',
                knowledge_id=entry.knowledge_id,
                statement=entry.statement[:50],
                confidence=entry.confidence,
                status=entry.verification_status,
            )

        logger.debug(
            'phase_7_self_knowledge_base',
            total_entries=len(integrated),
        )
        return integrated
