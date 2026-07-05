"""Tests for COG persistence and temporal versioning."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ayeneh.infrastructure.persistence.base import Base
from ayeneh.infrastructure.persistence.models.user import UserModel

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_USER_ID = uuid.uuid4()


@pytest_asyncio.fixture
async def async_session() -> AsyncGenerator[AsyncSession, None]:
    """Create an async in-memory SQLite session with all tables."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        # Seed a user so FK constraints pass
        user = UserModel(
            id=_USER_ID,
            email="test@example.com",
            display_name="Test User",
        )
        session.add(user)
        await session.commit()
        yield session
    await engine.dispose()


# ---------------------------------------------------------------------------
# Helper dataclass-like objects (plain classes to avoid domain imports)
# ---------------------------------------------------------------------------

class FakeBelief:
    def __init__(self, **kw):
        self.identifier = kw.get("identifier", "")
        self.belief_statement = kw.get("belief_statement", "")
        self.category = kw.get("category", "self")
        self.confidence = kw.get("confidence", 0.5)
        self.strength = kw.get("strength", 0.3)
        self.stability = kw.get("stability", 0.4)
        self.influence = kw.get("influence", 0.6)
        self.identity_coupling_score = kw.get("identity_coupling_score", 0.1)
        self.lifecycle_state = kw.get("lifecycle_state", "candidate")


class FakeNarrative:
    def __init__(self, **kw):
        self.identifier = kw.get("identifier", "")
        self.narrative_type = kw.get("narrative_type", "self")
        self.title = kw.get("title", "My Story")
        self.summary = kw.get("summary", "A summary")
        self.template = kw.get("template", "growth")
        self.confidence = kw.get("confidence", 0.7)
        self.influence_score = kw.get("influence_score", 0.5)
        self.core_assumptions = kw.get("core_assumptions", ("assumption1",))
        self.implicit_rules = kw.get("implicit_rules", ("rule1",))
        self.behavioral_consequences = kw.get("behavioral_consequences", ("consequence1",))
        self.lifecycle_state = kw.get("lifecycle_state", "candidate")


class FakeValue:
    def __init__(self, **kw):
        self.identifier = kw.get("identifier", "")
        self.value_statement = kw.get("value_statement", "Honesty matters")
        self.category = kw.get("category", "authenticity")
        self.confidence = kw.get("confidence", 0.8)
        self.stability = kw.get("stability", 0.6)
        self.priority = kw.get("priority", 0.9)
        self.influence = kw.get("influence", 0.7)
        self.declared_vs_observed = kw.get("declared_vs_observed", "aligned")
        self.lifecycle_state = kw.get("lifecycle_state", "candidate")


class FakeIdentity:
    def __init__(self, **kw):
        self.identifier = kw.get("identifier", "")
        self.identity_statement = kw.get("identity_statement", "I am a developer")
        self.confidence = kw.get("confidence", 0.6)
        self.stability = kw.get("stability", 0.5)
        self.centrality = kw.get("centrality", 0.8)
        self.influence = kw.get("influence", 0.7)
        self.observer_strength = kw.get("observer_strength", 0.3)
        self.narrative_identification_score = kw.get("narrative_identification_score", 0.4)
        self.lifecycle_state = kw.get("lifecycle_state", "candidate")


class FakeDecision:
    def __init__(self, **kw):
        self.identifier = kw.get("identifier", "")
        self.decision_statement = kw.get("decision_statement", "Chose path A")
        self.context = kw.get("context", "At a crossroads")
        self.chosen_alternative = kw.get("chosen_alternative", "A")
        self.rejected_alternatives = kw.get("rejected_alternatives", ("B", "C"))
        self.confidence = kw.get("confidence", 0.7)
        self.uncertainty = kw.get("uncertainty", 0.2)
        self.behavioral_outcome = kw.get("behavioral_outcome", "Took path A")
        self.decision_inertia = kw.get("decision_inertia", 0.5)
        self.lifecycle_state = kw.get("lifecycle_state", "candidate")


class FakeReflection:
    def __init__(self, **kw):
        self.identifier = kw.get("identifier", "")
        self.reflection_statement = kw.get("reflection_statement", "I notice a pattern")
        self.scope = kw.get("scope", "identity")
        self.granularity = kw.get("granularity", "session")
        self.confidence = kw.get("confidence", 0.6)
        self.lifecycle_state = kw.get("lifecycle_state", "candidate")


class FakeTrajectory:
    def __init__(self, **kw):
        self.identifier = kw.get("identifier", "")
        self.target_cognitive_object = kw.get("target_cognitive_object", "belief-1")
        self.target_type = kw.get("target_type", "belief")
        self.direction = kw.get("direction", "strengthening")
        self.rate_of_change = kw.get("rate_of_change", 0.3)
        self.confidence = kw.get("confidence", 0.7)
        self.historical_continuity = kw.get("historical_continuity", 0.8)
        self.lifecycle_state = kw.get("lifecycle_state", "candidate")


class FakeMeta:
    def __init__(self, **kw):
        self.identifier = kw.get("identifier", "")
        self.observed_cognitive_process = kw.get("observed_cognitive_process", "attention bias")
        self.awareness_description = kw.get("awareness_description", "I notice I focus on threats")
        self.awareness_level = kw.get("awareness_level", 2)
        self.confidence = kw.get("confidence", 0.5)
        self.stability = kw.get("stability", 0.4)
        self.lifecycle_state = kw.get("lifecycle_state", "candidate")


# ---------------------------------------------------------------------------
# COGRepository — Belief tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestBeliefPersistence:
    async def test_save_and_load_belief(self, async_session: AsyncSession):
        from ayeneh.cog.persistence import COGRepository

        repo = COGRepository(async_session)
        belief = FakeBelief(
            identifier=str(uuid.uuid4()),
            belief_statement="Hard work pays off",
            category="competence",
            confidence=0.8,
            strength=0.7,
            stability=0.6,
            influence=0.9,
            identity_coupling_score=0.5,
            lifecycle_state="candidate",
        )
        belief_id = await repo.save_belief(str(_USER_ID), belief)
        assert belief_id

        beliefs = await repo.load_beliefs(str(_USER_ID))
        assert len(beliefs) == 1
        assert beliefs[0]["id"] == belief_id
        assert beliefs[0]["belief_statement"] == "Hard work pays off"
        assert beliefs[0]["category"] == "competence"
        assert beliefs[0]["confidence"] == 0.8

    async def test_load_beliefs_with_lifecycle_filter(self, async_session: AsyncSession):
        from ayeneh.cog.persistence import COGRepository

        repo = COGRepository(async_session)
        b1 = FakeBelief(identifier=str(uuid.uuid4()), lifecycle_state="candidate")
        b2 = FakeBelief(identifier=str(uuid.uuid4()), lifecycle_state="canonical")
        await repo.save_belief(str(_USER_ID), b1)
        await repo.save_belief(str(_USER_ID), b2)

        candidates = await repo.load_beliefs(str(_USER_ID), lifecycle_state="candidate")
        assert len(candidates) == 1
        assert candidates[0]["lifecycle_state"] == "candidate"

        canonicals = await repo.load_beliefs(str(_USER_ID), lifecycle_state="canonical")
        assert len(canonicals) == 1
        assert canonicals[0]["lifecycle_state"] == "canonical"


# ---------------------------------------------------------------------------
# COGRepository — Narrative tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestNarrativePersistence:
    async def test_save_and_load_narrative(self, async_session: AsyncSession):
        from ayeneh.cog.persistence import COGRepository

        repo = COGRepository(async_session)
        narrative = FakeNarrative(
            identifier=str(uuid.uuid4()),
            title="Growth Mindset",
            summary="I embrace challenges",
            core_assumptions=("challenges build character",),
            implicit_rules=("always try new things",),
            behavioral_consequences=("takes on hard projects",),
        )
        nid = await repo.save_narrative(str(_USER_ID), narrative)
        assert nid

        narratives = await repo.load_narratives(str(_USER_ID))
        assert len(narratives) == 1
        assert narratives[0]["title"] == "Growth Mindset"
        assert narratives[0]["core_assumptions"] == ["challenges build character"]
        assert narratives[0]["implicit_rules"] == ["always try new things"]
        assert narratives[0]["behavioral_consequences"] == ["takes on hard projects"]

    async def test_load_narratives_with_lifecycle_filter(self, async_session: AsyncSession):
        from ayeneh.cog.persistence import COGRepository

        repo = COGRepository(async_session)
        n1 = FakeNarrative(identifier=str(uuid.uuid4()), lifecycle_state="provisional")
        n2 = FakeNarrative(identifier=str(uuid.uuid4()), lifecycle_state="canonical")
        await repo.save_narrative(str(_USER_ID), n1)
        await repo.save_narrative(str(_USER_ID), n2)

        provisional = await repo.load_narratives(str(_USER_ID), lifecycle_state="provisional")
        assert len(provisional) == 1


# ---------------------------------------------------------------------------
# COGRepository — Value tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestValuePersistence:
    async def test_save_and_load_value(self, async_session: AsyncSession):
        from ayeneh.cog.persistence import COGRepository

        repo = COGRepository(async_session)
        value = FakeValue(
            identifier=str(uuid.uuid4()),
            value_statement="Honesty is paramount",
            category="authenticity",
            confidence=0.9,
            declared_vs_observed="aligned",
        )
        vid = await repo.save_value(str(_USER_ID), value)
        assert vid

        values = await repo.load_values(str(_USER_ID))
        assert len(values) == 1
        assert values[0]["value_statement"] == "Honesty is paramount"
        assert values[0]["declared_vs_observed"] == "aligned"

    async def test_load_values_with_lifecycle_filter(self, async_session: AsyncSession):
        from ayeneh.cog.persistence import COGRepository

        repo = COGRepository(async_session)
        v1 = FakeValue(identifier=str(uuid.uuid4()), lifecycle_state="candidate")
        v2 = FakeValue(identifier=str(uuid.uuid4()), lifecycle_state="canonical")
        await repo.save_value(str(_USER_ID), v1)
        await repo.save_value(str(_USER_ID), v2)

        candidates = await repo.load_values(str(_USER_ID), lifecycle_state="candidate")
        assert len(candidates) == 1


# ---------------------------------------------------------------------------
# COGRepository — Identity tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestIdentityPersistence:
    async def test_save_and_load_identity(self, async_session: AsyncSession):
        from ayeneh.cog.persistence import COGRepository

        repo = COGRepository(async_session)
        component = FakeIdentity(
            identifier=str(uuid.uuid4()),
            identity_statement="I am a thoughtful person",
            confidence=0.7,
            centrality=0.8,
            observer_strength=0.6,
        )
        iid = await repo.save_identity(str(_USER_ID), component)
        assert iid

        components = await repo.load_identity_components(str(_USER_ID))
        assert len(components) == 1
        assert components[0]["identity_statement"] == "I am a thoughtful person"
        assert components[0]["centrality"] == 0.8
        assert components[0]["observer_strength"] == 0.6


# ---------------------------------------------------------------------------
# COGRepository — Decision tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestDecisionPersistence:
    async def test_save_and_load_decision(self, async_session: AsyncSession):
        from ayeneh.cog.persistence import COGRepository

        repo = COGRepository(async_session)
        decision = FakeDecision(
            identifier=str(uuid.uuid4()),
            decision_statement="Moved to new city",
            context="Career opportunity",
            chosen_alternative="Move",
            rejected_alternatives=("Stay", "Remote work"),
            confidence=0.8,
            behavioral_outcome="Relocated successfully",
        )
        did = await repo.save_decision(str(_USER_ID), decision)
        assert did

        decisions = await repo.load_decisions(str(_USER_ID))
        assert len(decisions) == 1
        assert decisions[0]["decision_statement"] == "Moved to new city"
        assert decisions[0]["rejected_alternatives"] == ["Stay", "Remote work"]
        assert decisions[0]["behavioral_outcome"] == "Relocated successfully"


# ---------------------------------------------------------------------------
# COGRepository — Reflection tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestReflectionPersistence:
    async def test_save_and_load_reflection(self, async_session: AsyncSession):
        from ayeneh.cog.persistence import COGRepository

        repo = COGRepository(async_session)
        reflection = FakeReflection(
            identifier=str(uuid.uuid4()),
            reflection_statement="I tend to avoid conflict",
            scope="relationships",
            granularity="session",
            confidence=0.6,
        )
        rid = await repo.save_reflection(str(_USER_ID), reflection)
        assert rid

        reflections = await repo.load_reflections(str(_USER_ID))
        assert len(reflections) == 1
        assert reflections[0]["reflection_statement"] == "I tend to avoid conflict"
        assert reflections[0]["scope"] == "relationships"
        assert reflections[0]["granularity"] == "session"


# ---------------------------------------------------------------------------
# COGRepository — Trajectory tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestTrajectoryPersistence:
    async def test_save_and_load_trajectory(self, async_session: AsyncSession):
        from ayeneh.cog.persistence import COGRepository

        repo = COGRepository(async_session)
        trajectory = FakeTrajectory(
            identifier=str(uuid.uuid4()),
            target_cognitive_object="belief-abc",
            target_type="belief",
            direction="strengthening",
            rate_of_change=0.3,
            confidence=0.7,
        )
        tid = await repo.save_trajectory(str(_USER_ID), trajectory)
        assert tid

        trajectories = await repo.load_trajectories(str(_USER_ID))
        assert len(trajectories) == 1
        assert trajectories[0]["target_type"] == "belief"
        assert trajectories[0]["direction"] == "strengthening"
        assert trajectories[0]["rate_of_change"] == 0.3


# ---------------------------------------------------------------------------
# COGRepository — Meta-Object tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestMetaPersistence:
    async def test_save_and_load_meta_object(self, async_session: AsyncSession):
        from ayeneh.cog.persistence import COGRepository

        repo = COGRepository(async_session)
        meta = FakeMeta(
            identifier=str(uuid.uuid4()),
            observed_cognitive_process="attention bias",
            awareness_description="I notice I focus on threats",
            awareness_level=2,
            confidence=0.5,
        )
        mid = await repo.save_meta_object(str(_USER_ID), meta)
        assert mid

        metas = await repo.load_meta_objects(str(_USER_ID))
        assert len(metas) == 1
        assert metas[0]["observed_process"] == "attention bias"
        assert metas[0]["awareness_level"] == 2


# ---------------------------------------------------------------------------
# CognitiveVersionManager tests
# ---------------------------------------------------------------------------


class TestCognitiveVersionManager:
    def test_create_version(self):
        from ayeneh.cog.versioning import CognitiveVersionManager

        mgr = CognitiveVersionManager()
        obj = FakeBelief(identifier="belief-v1", belief_statement="test")
        v = mgr.create_version(obj, change_reason="initial")
        assert "version_id" in v
        assert v["change_reason"] == "initial"
        assert "state" in v
        assert v["state"]["belief_statement"] == "test"

    def test_version_history(self):
        from ayeneh.cog.versioning import CognitiveVersionManager

        mgr = CognitiveVersionManager()
        obj = FakeBelief(identifier="belief-v2", belief_statement="v1")
        mgr.create_version(obj)
        v2 = mgr.create_version(obj, change_reason="updated")

        versions = mgr.get_versions("belief-v2")
        assert len(versions) == 2
        assert v2["change_reason"] == "updated"

    def test_get_latest_version(self):
        from ayeneh.cog.versioning import CognitiveVersionManager

        mgr = CognitiveVersionManager()
        obj = FakeBelief(identifier="belief-v3", belief_statement="latest")
        mgr.create_version(obj, change_reason="first")
        latest = mgr.create_version(obj, change_reason="second")

        result = mgr.get_latest_version("belief-v3")
        assert result is not None
        assert result["version_id"] == latest["version_id"]

    def test_get_latest_version_empty(self):
        from ayeneh.cog.versioning import CognitiveVersionManager

        mgr = CognitiveVersionManager()
        assert mgr.get_latest_version("nonexistent") is None

    def test_get_version_at_timestamp(self):
        from ayeneh.cog.versioning import CognitiveVersionManager

        mgr = CognitiveVersionManager()
        obj = FakeBelief(identifier="belief-v4", belief_statement="ts test")

        v1 = mgr.create_version(obj, change_reason="first")
        v2 = mgr.create_version(obj, change_reason="second")

        ts = datetime.fromisoformat(v1["timestamp"])
        result = mgr.get_version_at("belief-v4", ts)
        assert result is not None
        assert result["version_id"] == v1["version_id"]

    def test_get_version_at_returns_none_for_empty(self):
        from ayeneh.cog.versioning import CognitiveVersionManager

        mgr = CognitiveVersionManager()
        assert mgr.get_version_at("nonexistent", datetime.now(UTC)) is None

    def test_compute_change_rate(self):
        from ayeneh.cog.versioning import CognitiveVersionManager

        mgr = CognitiveVersionManager()
        obj = FakeBelief(identifier="belief-cr", belief_statement="rate test")
        mgr.create_version(obj)
        mgr.create_version(obj)

        rate = mgr.compute_change_rate("belief-cr")
        # 2 versions over ~0 days → should be >= 2.0 (clamped day span to 1.0)
        assert rate >= 2.0

    def test_compute_change_rate_single_version(self):
        from ayeneh.cog.versioning import CognitiveVersionManager

        mgr = CognitiveVersionManager()
        obj = FakeBelief(identifier="belief-cr1", belief_statement="single")
        mgr.create_version(obj)

        assert mgr.compute_change_rate("belief-cr1") == 0.0

    def test_compute_change_rate_empty(self):
        from ayeneh.cog.versioning import CognitiveVersionManager

        mgr = CognitiveVersionManager()
        assert mgr.compute_change_rate("nonexistent") == 0.0

    def test_snapshot_state(self):
        from ayeneh.cog.versioning import CognitiveVersionManager

        obj = FakeBelief(identifier="snap-test", belief_statement="snapshot")
        state = CognitiveVersionManager._snapshot_state(obj)
        assert state["identifier"] == "snap-test"
        assert state["belief_statement"] == "snapshot"
        assert "lifecycle_state" in state

    def test_snapshot_state_empty_object(self):
        from ayeneh.cog.versioning import CognitiveVersionManager

        class Plain:
            __slots__ = ()  # no __dict__

        obj = Plain()
        state = CognitiveVersionManager._snapshot_state(obj)
        assert state == {"value": str(obj)}

    def test_multiple_objects_independent(self):
        from ayeneh.cog.versioning import CognitiveVersionManager

        mgr = CognitiveVersionManager()
        a = FakeBelief(identifier="obj-a", belief_statement="a")
        b = FakeBelief(identifier="obj-b", belief_statement="b")
        mgr.create_version(a)
        mgr.create_version(b)
        mgr.create_version(a)

        assert len(mgr.get_versions("obj-a")) == 2
        assert len(mgr.get_versions("obj-b")) == 1
