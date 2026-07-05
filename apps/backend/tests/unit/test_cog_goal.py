"""Tests for the COG-08 Goal Modeling pipeline."""

from __future__ import annotations

import pytest
from datetime import UTC, datetime

from ayeneh.cog.goal.types import (
    GOAL_CATEGORIES,
    GoalObject,
)
from ayeneh.cog.goal.modeling import GoalModelingEngine, GoalModelingResult
from ayeneh.cog.goal.planning import PlanningStructure


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def goal_engine():
    return GoalModelingEngine()


@pytest.fixture
def sample_evidence():
    return [
        {'identifier': 'ev-1', 'type': 'self_report', 'text': 'I want to learn Python.'},
        {'identifier': 'ev-2', 'type': 'behavioral_report', 'text': 'I plan to finish the project.'},
        {'identifier': 'ev-3', 'type': 'self_report', 'text': 'My goal is to run a marathon.'},
        {'identifier': 'ev-4', 'type': 'observation', 'text': 'The deadline is next week.'},
    ]


@pytest.fixture
def sample_goal():
    return GoalObject(
        identifier='goal-1',
        goal_statement='Learn Python',
        category='learning',
        confidence=0.8,
        priority=0.9,
        commitment_strength=0.7,
        progress=0.3,
    )


# ---------------------------------------------------------------------------
# GoalObject tests
# ---------------------------------------------------------------------------


class TestGoalObject:
    def test_creation(self):
        g = GoalObject(
            identifier='g1',
            goal_statement='Learn Python',
            category='learning',
        )
        assert g.identifier == 'g1'
        assert g.goal_statement == 'Learn Python'
        assert g.category == 'learning'

    def test_defaults(self):
        g = GoalObject(identifier='g2', goal_statement='test', category='career')
        assert g.confidence == 0.0
        assert g.priority == 0.0
        assert g.commitment_strength == 0.0
        assert g.progress == 0.0
        assert g.persistence == 0.0
        assert g.flexibility == 0.0
        assert g.lifecycle_state == 'candidate'
        assert g.specification_version == '1.0.0'

    def test_frozen(self):
        g = GoalObject(identifier='g3', goal_statement='test', category='career')
        with pytest.raises(AttributeError):
            g.progress = 0.5  # type: ignore[misc]

    def test_evidence_tuples(self):
        g = GoalObject(
            identifier='g4',
            goal_statement='test',
            category='career',
            supporting_evidence=('ev-1',),
            behavioural_evidence=('ev-2', 'ev-3'),
        )
        assert len(g.supporting_evidence) == 1
        assert len(g.behavioural_evidence) == 2

    def test_cross_module_associations(self):
        g = GoalObject(
            identifier='g5',
            goal_statement='test',
            category='career',
            associated_values=('v1',),
            associated_beliefs=('b1',),
            associated_narratives=('n1',),
        )
        assert 'v1' in g.associated_values
        assert 'b1' in g.associated_beliefs
        assert 'n1' in g.associated_narratives

    def test_dependencies_and_milestones(self):
        g = GoalObject(
            identifier='g6',
            goal_statement='test',
            category='project',
            dependencies=('g4', 'g5'),
            milestones=({'name': 'm1', 'done': True},),
        )
        assert len(g.dependencies) == 2
        assert len(g.milestones) == 1

    def test_categories_contain_expected_values(self):
        assert 'career' in GOAL_CATEGORIES
        assert 'creative' in GOAL_CATEGORIES
        assert 'spiritual' in GOAL_CATEGORIES
        assert len(GOAL_CATEGORIES) == 10


# ---------------------------------------------------------------------------
# GoalModelingEngine tests
# ---------------------------------------------------------------------------


class TestGoalModelingEngine:
    def test_process_returns_result(self, goal_engine, sample_evidence):
        result = goal_engine.process(sample_evidence)
        assert isinstance(result, GoalModelingResult)

    def test_extracts_goals(self, goal_engine, sample_evidence):
        result = goal_engine.process(sample_evidence)
        assert result.total_extracted > 0

    def test_goals_have_identifiers(self, goal_engine, sample_evidence):
        result = goal_engine.process(sample_evidence)
        for g in result.goals:
            assert g.identifier
            assert isinstance(g.identifier, str)

    def test_goals_have_valid_categories(self, goal_engine, sample_evidence):
        result = goal_engine.process(sample_evidence)
        for g in result.goals:
            assert g.category in GOAL_CATEGORIES

    def test_goals_are_provisional(self, goal_engine, sample_evidence):
        result = goal_engine.process(sample_evidence)
        for g in result.goals:
            assert g.lifecycle_state == 'provisional'

    def test_metrics_computed(self, goal_engine, sample_evidence):
        result = goal_engine.process(sample_evidence)
        for g in result.goals:
            assert 0.0 <= g.confidence <= 1.0
            assert 0.0 <= g.priority <= 1.0
            assert 0.0 <= g.commitment_strength <= 1.0
            assert 0.0 <= g.persistence <= 1.0

    def test_network_built(self, goal_engine, sample_evidence):
        result = goal_engine.process(sample_evidence)
        assert isinstance(result.network, dict)
        assert 'nodes' in result.network
        assert 'edges' in result.network

    def test_by_category(self, goal_engine, sample_evidence):
        result = goal_engine.process(sample_evidence)
        assert isinstance(result.by_category, dict)
        total = sum(result.by_category.values())
        assert total == result.total_extracted

    def test_with_values(self, goal_engine, sample_evidence):
        values = [{'identifier': 'v1', 'statement': 'I want to grow.'}]
        result = goal_engine.process(sample_evidence, values=values)
        assert result.total_extracted > 0

    def test_with_beliefs(self, goal_engine, sample_evidence):
        beliefs = [{'identifier': 'b1', 'statement': 'I need to succeed.'}]
        result = goal_engine.process(sample_evidence, beliefs=beliefs)
        assert result.total_extracted > 0

    def test_empty_evidence(self, goal_engine):
        result = goal_engine.process([])
        assert result.total_extracted == 0

    def test_determinism(self, goal_engine, sample_evidence):
        """Same input → same output."""
        r1 = goal_engine.process(sample_evidence)
        r2 = goal_engine.process(sample_evidence)
        assert r1.total_extracted == r2.total_extracted
        for g1, g2 in zip(r1.goals, r2.goals):
            assert g1.goal_statement == g2.goal_statement

    def test_no_goal_keywords_filtered(self, goal_engine):
        evidence = [
            {'identifier': 'ev-1', 'type': 'observation', 'text': 'The sky is blue.'},
        ]
        result = goal_engine.process(evidence)
        assert result.total_extracted == 0


# ---------------------------------------------------------------------------
# PlanningStructure tests
# ---------------------------------------------------------------------------


class TestPlanningStructure:
    def test_creation(self):
        ps = PlanningStructure(goal_id='g1')
        assert ps.goal_id == 'g1'
        assert ps.milestones == ()
        assert ps.dependencies == ()
        assert ps.resources == ()
        assert ps.estimated_duration_days == 0
        assert ps.constraints == ()
        assert ps.alternative_pathways == ()

    def test_with_milestones(self):
        ps = PlanningStructure(
            goal_id='g2',
            milestones=(
                {'name': 'Research', 'done': True},
                {'name': 'Implementation', 'done': False},
            ),
            estimated_duration_days=30,
        )
        assert len(ps.milestones) == 2
        assert ps.estimated_duration_days == 30

    def test_frozen(self):
        ps = PlanningStructure(goal_id='g3')
        with pytest.raises(AttributeError):
            ps.goal_id = 'g4'  # type: ignore[misc]

    def test_with_all_fields(self):
        ps = PlanningStructure(
            goal_id='g5',
            milestones=({'name': 'm1', 'done': False},),
            dependencies=('g3', 'g4'),
            resources=('time', 'money'),
            estimated_duration_days=60,
            constraints=('budget',),
            alternative_pathways=('path-a', 'path-b'),
        )
        assert len(ps.milestones) == 1
        assert len(ps.dependencies) == 2
        assert len(ps.resources) == 2
        assert len(ps.constraints) == 1
        assert len(ps.alternative_pathways) == 2
        assert ps.specification_version == '1.0.0'
