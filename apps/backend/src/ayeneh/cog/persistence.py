"""COG persistence layer — saves and loads cognitive objects via DB models."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class COGRepository:
    """Unified persistence for all cognitive object types."""

    def __init__(self, session: AsyncSession):
        self._session = session

    # ------------------------------------------------------------------
    # Belief
    # ------------------------------------------------------------------

    async def save_belief(self, user_id: str, belief: Any) -> str:
        """Save a BeliefObject to DB. Returns the ID."""
        from ayeneh.infrastructure.persistence.models.cog_belief import (
            CognitiveBeliefModel,
        )

        model = CognitiveBeliefModel(
            id=uuid.UUID(belief.identifier) if belief.identifier else uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            belief_statement=belief.belief_statement,
            category=belief.category,
            confidence=belief.confidence,
            strength=belief.strength,
            stability=belief.stability,
            influence=belief.influence,
            identity_coupling_score=belief.identity_coupling_score,
            lifecycle_state=belief.lifecycle_state,
        )
        self._session.add(model)
        await self._session.flush()
        logger.info("cog.belief_saved", belief_id=str(model.id), user_id=user_id)
        return str(model.id)

    async def load_beliefs(
        self, user_id: str, lifecycle_state: str | None = None
    ) -> list[dict]:
        """Load all beliefs for a user."""
        from ayeneh.infrastructure.persistence.models.cog_belief import (
            CognitiveBeliefModel,
        )

        stmt = select(CognitiveBeliefModel).where(
            CognitiveBeliefModel.user_id == uuid.UUID(user_id)
        )
        if lifecycle_state:
            stmt = stmt.where(
                CognitiveBeliefModel.lifecycle_state == lifecycle_state
            )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._belief_to_dict(m) for m in models]

    # ------------------------------------------------------------------
    # Narrative
    # ------------------------------------------------------------------

    async def save_narrative(self, user_id: str, narrative: Any) -> str:
        """Save a NarrativeObject to DB. Returns the ID."""
        from ayeneh.infrastructure.persistence.models.cog_narrative import (
            CognitiveNarrativeModel,
        )

        model = CognitiveNarrativeModel(
            id=uuid.UUID(narrative.identifier) if narrative.identifier else uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            narrative_type=narrative.narrative_type,
            title=narrative.title,
            summary=narrative.summary or "",
            template=narrative.template or "",
            confidence=narrative.confidence,
            influence_score=narrative.influence_score,
            core_assumptions=json.dumps(list(narrative.core_assumptions)),
            implicit_rules=json.dumps(list(narrative.implicit_rules)),
            behavioral_consequences=json.dumps(list(narrative.behavioral_consequences)),
            lifecycle_state=narrative.lifecycle_state,
        )
        self._session.add(model)
        await self._session.flush()
        logger.info("cog.narrative_saved", narrative_id=str(model.id), user_id=user_id)
        return str(model.id)

    async def load_narratives(
        self, user_id: str, lifecycle_state: str | None = None
    ) -> list[dict]:
        """Load all narratives for a user."""
        from ayeneh.infrastructure.persistence.models.cog_narrative import (
            CognitiveNarrativeModel,
        )

        stmt = select(CognitiveNarrativeModel).where(
            CognitiveNarrativeModel.user_id == uuid.UUID(user_id)
        )
        if lifecycle_state:
            stmt = stmt.where(
                CognitiveNarrativeModel.lifecycle_state == lifecycle_state
            )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._narrative_to_dict(m) for m in models]

    # ------------------------------------------------------------------
    # Value
    # ------------------------------------------------------------------

    async def save_value(self, user_id: str, value: Any) -> str:
        """Save a ValueObject to DB. Returns the ID."""
        from ayeneh.infrastructure.persistence.models.cog_value import (
            CognitiveValueModel,
        )

        model = CognitiveValueModel(
            id=uuid.UUID(value.identifier) if value.identifier else uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            value_statement=value.value_statement,
            category=value.category,
            confidence=value.confidence,
            stability=value.stability,
            priority=value.priority,
            influence=value.influence,
            declared_vs_observed=value.declared_vs_observed,
            lifecycle_state=value.lifecycle_state,
        )
        self._session.add(model)
        await self._session.flush()
        logger.info("cog.value_saved", value_id=str(model.id), user_id=user_id)
        return str(model.id)

    async def load_values(
        self, user_id: str, lifecycle_state: str | None = None
    ) -> list[dict]:
        """Load all values for a user."""
        from ayeneh.infrastructure.persistence.models.cog_value import (
            CognitiveValueModel,
        )

        stmt = select(CognitiveValueModel).where(
            CognitiveValueModel.user_id == uuid.UUID(user_id)
        )
        if lifecycle_state:
            stmt = stmt.where(
                CognitiveValueModel.lifecycle_state == lifecycle_state
            )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._value_to_dict(m) for m in models]

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    async def save_identity(self, user_id: str, component: Any) -> str:
        """Save an IdentityComponent to DB. Returns the ID."""
        from ayeneh.infrastructure.persistence.models.cog_identity import (
            CognitiveIdentityModel,
        )

        model = CognitiveIdentityModel(
            id=uuid.UUID(component.identifier) if component.identifier else uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            identity_statement=component.identity_statement,
            confidence=component.confidence,
            stability=component.stability,
            centrality=component.centrality,
            influence=component.influence,
            observer_strength=component.observer_strength,
            narrative_identification_score=component.narrative_identification_score,
            lifecycle_state=component.lifecycle_state,
        )
        self._session.add(model)
        await self._session.flush()
        logger.info("cog.identity_saved", identity_id=str(model.id), user_id=user_id)
        return str(model.id)

    async def load_identity_components(self, user_id: str) -> list[dict]:
        """Load all identity components for a user."""
        from ayeneh.infrastructure.persistence.models.cog_identity import (
            CognitiveIdentityModel,
        )

        stmt = select(CognitiveIdentityModel).where(
            CognitiveIdentityModel.user_id == uuid.UUID(user_id)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._identity_to_dict(m) for m in models]

    # ------------------------------------------------------------------
    # Decision
    # ------------------------------------------------------------------

    async def save_decision(self, user_id: str, decision: Any) -> str:
        """Save a DecisionObject to DB. Returns the ID."""
        from ayeneh.infrastructure.persistence.models.cog_decision import (
            CognitiveDecisionModel,
        )

        model = CognitiveDecisionModel(
            id=uuid.UUID(decision.identifier) if decision.identifier else uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            decision_statement=decision.decision_statement,
            context=decision.context or "",
            chosen_alternative=decision.chosen_alternative or "",
            rejected_alternatives=json.dumps(list(decision.rejected_alternatives)),
            confidence=decision.confidence,
            uncertainty=decision.uncertainty,
            behavioral_outcome=decision.behavioral_outcome or "",
            decision_inertia=decision.decision_inertia,
            lifecycle_state=decision.lifecycle_state,
        )
        self._session.add(model)
        await self._session.flush()
        logger.info("cog.decision_saved", decision_id=str(model.id), user_id=user_id)
        return str(model.id)

    async def load_decisions(self, user_id: str) -> list[dict]:
        """Load all decisions for a user."""
        from ayeneh.infrastructure.persistence.models.cog_decision import (
            CognitiveDecisionModel,
        )

        stmt = select(CognitiveDecisionModel).where(
            CognitiveDecisionModel.user_id == uuid.UUID(user_id)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._decision_to_dict(m) for m in models]

    # ------------------------------------------------------------------
    # Reflection
    # ------------------------------------------------------------------

    async def save_reflection(self, user_id: str, reflection: Any) -> str:
        """Save a ReflectionObject to DB. Returns the ID."""
        from ayeneh.infrastructure.persistence.models.cog_reflection import (
            CognitiveReflectionModel,
        )

        model = CognitiveReflectionModel(
            id=uuid.UUID(reflection.identifier) if reflection.identifier else uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            reflection_statement=reflection.reflection_statement,
            scope=reflection.scope or "",
            granularity=reflection.granularity,
            confidence=reflection.confidence,
            lifecycle_state=reflection.lifecycle_state,
        )
        self._session.add(model)
        await self._session.flush()
        logger.info(
            "cog.reflection_saved", reflection_id=str(model.id), user_id=user_id
        )
        return str(model.id)

    async def load_reflections(self, user_id: str) -> list[dict]:
        """Load all reflections for a user."""
        from ayeneh.infrastructure.persistence.models.cog_reflection import (
            CognitiveReflectionModel,
        )

        stmt = select(CognitiveReflectionModel).where(
            CognitiveReflectionModel.user_id == uuid.UUID(user_id)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._reflection_to_dict(m) for m in models]

    # ------------------------------------------------------------------
    # Trajectory
    # ------------------------------------------------------------------

    async def save_trajectory(self, user_id: str, trajectory: Any) -> str:
        """Save a TrajectoryObject to DB. Returns the ID."""
        from ayeneh.infrastructure.persistence.models.cog_trajectory import (
            CognitiveTrajectoryModel,
        )

        model = CognitiveTrajectoryModel(
            id=uuid.UUID(trajectory.identifier)
            if trajectory.identifier
            else uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            target_cognitive_object=trajectory.target_cognitive_object,
            target_type=trajectory.target_type,
            direction=trajectory.direction or "",
            rate_of_change=trajectory.rate_of_change,
            confidence=trajectory.confidence,
            historical_continuity=trajectory.historical_continuity,
            lifecycle_state=trajectory.lifecycle_state,
        )
        self._session.add(model)
        await self._session.flush()
        logger.info(
            "cog.trajectory_saved", trajectory_id=str(model.id), user_id=user_id
        )
        return str(model.id)

    async def load_trajectories(self, user_id: str) -> list[dict]:
        """Load all trajectories for a user."""
        from ayeneh.infrastructure.persistence.models.cog_trajectory import (
            CognitiveTrajectoryModel,
        )

        stmt = select(CognitiveTrajectoryModel).where(
            CognitiveTrajectoryModel.user_id == uuid.UUID(user_id)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._trajectory_to_dict(m) for m in models]

    # ------------------------------------------------------------------
    # Meta-Object
    # ------------------------------------------------------------------

    async def save_meta_object(self, user_id: str, meta: Any) -> str:
        """Save a MetaCognitiveObject to DB. Returns the ID."""
        from ayeneh.infrastructure.persistence.models.cog_meta import (
            CognitiveMetaObjectModel,
        )

        model = CognitiveMetaObjectModel(
            id=uuid.UUID(meta.identifier) if meta.identifier else uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            observed_process=meta.observed_cognitive_process,
            awareness_description=meta.awareness_description or "",
            awareness_level=meta.awareness_level,
            confidence=meta.confidence,
            stability=meta.stability,
            lifecycle_state=meta.lifecycle_state,
        )
        self._session.add(model)
        await self._session.flush()
        logger.info("cog.meta_saved", meta_id=str(model.id), user_id=user_id)
        return str(model.id)

    async def load_meta_objects(self, user_id: str) -> list[dict]:
        """Load all meta-cognitive objects for a user."""
        from ayeneh.infrastructure.persistence.models.cog_meta import (
            CognitiveMetaObjectModel,
        )

        stmt = select(CognitiveMetaObjectModel).where(
            CognitiveMetaObjectModel.user_id == uuid.UUID(user_id)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._meta_to_dict(m) for m in models]

    # ------------------------------------------------------------------
    # Domain → dict converters
    # ------------------------------------------------------------------

    @staticmethod
    def _belief_to_dict(model: Any) -> dict:
        return {
            "id": str(model.id),
            "user_id": str(model.user_id),
            "belief_statement": model.belief_statement,
            "category": model.category,
            "confidence": model.confidence,
            "strength": model.strength,
            "stability": model.stability,
            "influence": model.influence,
            "identity_coupling_score": model.identity_coupling_score,
            "lifecycle_state": model.lifecycle_state,
        }

    @staticmethod
    def _narrative_to_dict(model: Any) -> dict:
        return {
            "id": str(model.id),
            "user_id": str(model.user_id),
            "narrative_type": model.narrative_type,
            "title": model.title,
            "summary": model.summary,
            "template": model.template,
            "confidence": model.confidence,
            "influence_score": model.influence_score,
            "core_assumptions": json.loads(model.core_assumptions),
            "implicit_rules": json.loads(model.implicit_rules),
            "behavioral_consequences": json.loads(model.behavioral_consequences),
            "lifecycle_state": model.lifecycle_state,
        }

    @staticmethod
    def _value_to_dict(model: Any) -> dict:
        return {
            "id": str(model.id),
            "user_id": str(model.user_id),
            "value_statement": model.value_statement,
            "category": model.category,
            "confidence": model.confidence,
            "stability": model.stability,
            "priority": model.priority,
            "influence": model.influence,
            "declared_vs_observed": model.declared_vs_observed,
            "lifecycle_state": model.lifecycle_state,
        }

    @staticmethod
    def _identity_to_dict(model: Any) -> dict:
        return {
            "id": str(model.id),
            "user_id": str(model.user_id),
            "identity_statement": model.identity_statement,
            "confidence": model.confidence,
            "stability": model.stability,
            "centrality": model.centrality,
            "influence": model.influence,
            "observer_strength": model.observer_strength,
            "narrative_identification_score": model.narrative_identification_score,
            "lifecycle_state": model.lifecycle_state,
        }

    @staticmethod
    def _decision_to_dict(model: Any) -> dict:
        return {
            "id": str(model.id),
            "user_id": str(model.user_id),
            "decision_statement": model.decision_statement,
            "context": model.context,
            "chosen_alternative": model.chosen_alternative,
            "rejected_alternatives": json.loads(model.rejected_alternatives),
            "confidence": model.confidence,
            "uncertainty": model.uncertainty,
            "behavioral_outcome": model.behavioral_outcome,
            "decision_inertia": model.decision_inertia,
            "lifecycle_state": model.lifecycle_state,
        }

    @staticmethod
    def _reflection_to_dict(model: Any) -> dict:
        return {
            "id": str(model.id),
            "user_id": str(model.user_id),
            "reflection_statement": model.reflection_statement,
            "scope": model.scope,
            "granularity": model.granularity,
            "confidence": model.confidence,
            "lifecycle_state": model.lifecycle_state,
        }

    @staticmethod
    def _trajectory_to_dict(model: Any) -> dict:
        return {
            "id": str(model.id),
            "user_id": str(model.user_id),
            "target_cognitive_object": model.target_cognitive_object,
            "target_type": model.target_type,
            "direction": model.direction,
            "rate_of_change": model.rate_of_change,
            "confidence": model.confidence,
            "historical_continuity": model.historical_continuity,
            "lifecycle_state": model.lifecycle_state,
        }

    @staticmethod
    def _meta_to_dict(model: Any) -> dict:
        return {
            "id": str(model.id),
            "user_id": str(model.user_id),
            "observed_process": model.observed_process,
            "awareness_description": model.awareness_description,
            "awareness_level": model.awareness_level,
            "confidence": model.confidence,
            "stability": model.stability,
            "lifecycle_state": model.lifecycle_state,
        }
