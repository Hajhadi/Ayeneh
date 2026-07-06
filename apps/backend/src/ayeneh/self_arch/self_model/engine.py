"""SELF-01 Self-Model Engine.

7-phase pipeline for constructing and maintaining a SelfModelObject:

1. ArchitectureState — determine the current architecture version and state
2. ModuleDiscovery — discover and catalogue available modules
3. CapabilityAssessment — assess system capabilities from module data
4. ConstraintIdentification — identify active constraints on the system
5. ResourceAssessment — assess available resources and their utilization
6. SelfModelConstruction — assemble the SelfModelObject
7. VersionUpdate — record revision history and update version metadata
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from ayeneh.self_arch.self_model.types import (
    ConstraintDescriptor,
    SelfModelConfidence,
    SelfModelObject,
)

logger = structlog.get_logger(__name__)

# Default modules for the Ayeneh architecture
_DEFAULT_MODULES: tuple[str, ...] = (
    'dlg',
    'inf',
    'int',
    'act',
    'dec',
    'memo',
    'cog',
    'self_arch',
)

_DEFAULT_MODULE_STATUS: dict[str, str] = {
    'dlg': 'active',
    'inf': 'active',
    'int': 'active',
    'act': 'active',
    'dec': 'active',
    'memo': 'active',
    'cog': 'active',
    'self_arch': 'active',
}

_DEFAULT_CAPABILITIES: tuple[dict[str, Any], ...] = (
    {
        'name': 'dialogue_management',
        'description': 'Multi-turn dialogue state tracking and management',
        'confidence': 0.8,
    },
    {
        'name': 'inference_engine',
        'description': 'Multi-hop reasoning and hypothesis generation',
        'confidence': 0.7,
    },
    {
        'name': 'memory_system',
        'description': 'Episodic and semantic memory storage and retrieval',
        'confidence': 0.75,
    },
    {
        'name': 'cognitive_modeling',
        'description': 'Beliefs, goals, values, and identity modeling',
        'confidence': 0.7,
    },
    {
        'name': 'self_architecture',
        'description': 'Self-modeling, identity continuity, and self-knowledge',
        'confidence': 0.5,
    },
)

_DEFAULT_LIMITATIONS: tuple[dict[str, Any], ...] = (
    {
        'type': 'temporal',
        'description': 'No persistent state across sessions without external storage',
        'severity': 'high',
    },
    {
        'type': 'perceptual',
        'description': 'Limited to text-based input channels',
        'severity': 'medium',
    },
    {
        'type': 'reasoning',
        'description': 'Context window limits constraint multi-step reasoning depth',
        'severity': 'medium',
    },
)

_DEFAULT_CONSTRAINTS: tuple[dict[str, Any], ...] = (
    {
        'type': 'resource',
        'description': 'Context window size limits working memory capacity',
        'is_active': True,
    },
    {
        'type': 'architectural',
        'description': 'Module communication via typed message passing',
        'is_active': True,
    },
)

_DEFAULT_RESOURCES: dict[str, float] = {
    'compute_capacity': 0.8,
    'memory_capacity': 0.7,
    'context_window': 0.6,
    'tool_availability': 0.9,
    'network_access': 0.5,
    'storage_capacity': 0.8,
}


class SelfModelEngine:
    """Constructs and maintains a SelfModelObject through a 7-phase pipeline (SELF-01)."""

    def __init__(self, ai_router: Any = None) -> None:
        self._ai_router = ai_router
        self._revision_count: int = 0
        self._current_model: SelfModelObject | None = None

    @property
    def current_model(self) -> SelfModelObject | None:
        """Return the current self-model."""
        return self._current_model

    @property
    def revision_count(self) -> int:
        """Return the number of revisions made."""
        return self._revision_count

    def build(
        self,
        available_modules: tuple[str, ...] | None = None,
        module_status: dict[str, str] | None = None,
        architecture_version: str = '1.0.0',
    ) -> SelfModelObject:
        """Run the full 7-phase self-model pipeline."""
        logger.info('self01_pipeline_start', architecture_version=architecture_version)

        # Phase 1 — ArchitectureState
        arch_state = self._phase_architecture_state(architecture_version)

        # Phase 2 — ModuleDiscovery
        modules, status = self._phase_module_discovery(
            available_modules, module_status,
        )

        # Phase 3 — CapabilityAssessment
        capabilities, limitations = self._phase_capability_assessment(modules)

        # Phase 4 — ConstraintIdentification
        constraints = self._phase_constraint_identification(modules)

        # Phase 5 — ResourceAssessment
        resources = self._phase_resource_assessment()

        # Phase 6 — SelfModelConstruction
        model = self._phase_self_model_construction(
            arch_state, modules, status, capabilities,
            limitations, constraints, resources,
        )

        # Phase 7 — VersionUpdate
        model = self._phase_version_update(model)

        self._current_model = model
        logger.info(
            'self01_pipeline_end',
            model_id=model.model_id,
            confidence=model.confidence,
        )
        return model

    # ------------------------------------------------------------------
    # Phase 1 — ArchitectureState
    # ------------------------------------------------------------------

    def _phase_architecture_state(
        self, architecture_version: str,
    ) -> dict[str, Any]:
        """Determine the current architecture version and state."""
        logger.debug('phase_1_architecture_state', version=architecture_version)
        return {
            'version': architecture_version,
            'state': 'operational',
            'timestamp': datetime.now(UTC).isoformat(),
        }

    # ------------------------------------------------------------------
    # Phase 2 — ModuleDiscovery
    # ------------------------------------------------------------------

    def _phase_module_discovery(
        self,
        available_modules: tuple[str, ...] | None,
        module_status: dict[str, str] | None,
    ) -> tuple[tuple[str, ...], dict[str, str]]:
        """Discover and catalogue available modules."""
        modules = available_modules if available_modules is not None else _DEFAULT_MODULES
        status = module_status if module_status is not None else dict(_DEFAULT_MODULE_STATUS)

        # Ensure all modules have a status entry
        for mod in modules:
            if mod not in status:
                status[mod] = 'unknown'

        logger.debug(
            'phase_2_module_discovery',
            module_count=len(modules),
            active_count=sum(1 for s in status.values() if s == 'active'),
        )
        return tuple(modules), status

    # ------------------------------------------------------------------
    # Phase 3 — CapabilityAssessment
    # ------------------------------------------------------------------

    def _phase_capability_assessment(
        self, modules: tuple[str, ...],
    ) -> tuple[tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
        """Assess system capabilities and limitations from module data."""
        capabilities = list(_DEFAULT_CAPABILITIES)
        limitations = list(_DEFAULT_LIMITATIONS)

        # Adjust capabilities based on available modules
        active_modules = set(modules)
        filtered_capabilities = [
            cap for cap in capabilities
            if self._capability_module_check(cap, active_modules)
        ]

        logger.debug(
            'phase_3_capability_assessment',
            capability_count=len(filtered_capabilities),
            limitation_count=len(limitations),
        )
        return tuple(filtered_capabilities), tuple(limitations)

    def _capability_module_check(
        self, capability: dict[str, Any], active_modules: set[str],
    ) -> bool:
        """Check if a capability's required modules are available."""
        name = capability.get('name', '')
        module_map: dict[str, str] = {
            'dialogue_management': 'dlg',
            'inference_engine': 'inf',
            'memory_system': 'memo',
            'cognitive_modeling': 'cog',
            'self_architecture': 'self_arch',
        }
        required = module_map.get(name, '')
        return not required or required in active_modules

    # ------------------------------------------------------------------
    # Phase 4 — ConstraintIdentification
    # ------------------------------------------------------------------

    def _phase_constraint_identification(
        self, modules: tuple[str, ...],
    ) -> tuple[dict[str, Any], ...]:
        """Identify active constraints on the system."""
        constraints: list[dict[str, Any]] = list(_DEFAULT_CONSTRAINTS)

        # Add module-specific constraints
        if 'self_arch' not in modules:
            constraints.append({
                'type': 'capability',
                'description': 'Self-architecture module not available',
                'is_active': True,
            })

        logger.debug(
            'phase_4_constraint_identification',
            constraint_count=len(constraints),
        )
        return tuple(constraints)

    # ------------------------------------------------------------------
    # Phase 5 — ResourceAssessment
    # ------------------------------------------------------------------

    def _phase_resource_assessment(self) -> dict[str, float]:
        """Assess available resources and their utilization."""
        logger.debug('phase_5_resource_assessment')
        return dict(_DEFAULT_RESOURCES)

    # ------------------------------------------------------------------
    # Phase 6 — SelfModelConstruction
    # ------------------------------------------------------------------

    def _phase_self_model_construction(
        self,
        arch_state: dict[str, Any],
        modules: tuple[str, ...],
        status: dict[str, str],
        capabilities: tuple[dict[str, Any], ...],
        limitations: tuple[dict[str, Any], ...],
        constraints: tuple[dict[str, Any], ...],
        resources: dict[str, float],
    ) -> SelfModelObject:
        """Assemble the SelfModelObject from all phase outputs."""
        confidence = self._compute_confidence(
            modules, status, capabilities, resources,
        )

        model = SelfModelObject(
            model_id=str(uuid.uuid4()),
            architecture_version=arch_state.get('version', ''),
            available_modules=modules,
            module_status=status,
            capabilities=capabilities,
            known_limitations=limitations,
            active_constraints=constraints,
            available_resources=resources,
            confidence=confidence,
        )

        logger.debug(
            'phase_6_self_model_construction',
            model_id=model.model_id,
            confidence=confidence,
        )
        return model

    def _compute_confidence(
        self,
        modules: tuple[str, ...],
        status: dict[str, str],
        capabilities: tuple[dict[str, Any], ...],
        resources: dict[str, float],
    ) -> float:
        """Compute overall confidence for the self-model."""
        # Module health factor
        if not modules:
            module_factor = 0.0
        else:
            active_count = sum(1 for m in modules if status.get(m) == 'active')
            module_factor = active_count / len(modules)

        # Capability factor
        if not capabilities:
            capability_factor = 0.0
        else:
            cap_confidences = [c.get('confidence', 0.0) for c in capabilities]
            capability_factor = sum(cap_confidences) / len(cap_confidences)

        # Resource factor
        if not resources:
            resource_factor = 0.0
        else:
            resource_factor = sum(resources.values()) / len(resources)

        overall = (module_factor + capability_factor + resource_factor) / 3.0
        return round(min(1.0, max(0.0, overall)), 4)

    # ------------------------------------------------------------------
    # Phase 7 — VersionUpdate
    # ------------------------------------------------------------------

    def _phase_version_update(self, model: SelfModelObject) -> SelfModelObject:
        """Record revision history and update version metadata."""
        self._revision_count += 1

        revision_entry = {
            'version': f'1.0.{self._revision_count}',
            'timestamp': datetime.now(UTC).isoformat(),
            'change_description': f'Revision {self._revision_count}',
            'change_type': 'initial' if self._revision_count == 1 else 'update',
        }

        version_metadata = {
            'schema_version': '1.0.0',
            'engine_version': '1.0.0',
            'revision_number': self._revision_count,
            'last_updated': datetime.now(UTC).isoformat(),
        }

        explainability = {
            'reasoning_chain': [
                f'Architecture version: {model.architecture_version}',
                f'Modules discovered: {len(model.available_modules)}',
                f'Capabilities assessed: {len(model.capabilities)}',
                f'Constraints identified: {len(model.active_constraints)}',
                f'Resources evaluated: {len(model.available_resources)}',
            ],
            'evidence_summary': (
                f'Self-model built from {len(model.available_modules)} modules '
                f'with {len(model.capabilities)} capabilities'
            ),
            'uncertainty_disclosures': [
                f'Confidence level: {model.confidence:.2f}',
            ],
        }

        updated = SelfModelObject(
            model_id=model.model_id,
            architecture_version=model.architecture_version,
            available_modules=model.available_modules,
            module_status=model.module_status,
            capabilities=model.capabilities,
            known_limitations=model.known_limitations,
            active_constraints=model.active_constraints,
            available_resources=model.available_resources,
            confidence=model.confidence,
            revision_history=model.revision_history + (revision_entry,),
            version_metadata=version_metadata,
            creation_timestamp=model.creation_timestamp,
            explainability_metadata=explainability,
        )

        logger.debug(
            'phase_7_version_update',
            revision=self._revision_count,
        )
        return updated
