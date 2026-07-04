"""Tests for version tracking per SPEC-01A RP-06."""

import pytest
from ayeneh.runtime.versioning import (
    VersionTracker,
    RuntimeVersions,
    ENGINE_VERSIONS,
)


class TestRuntimeVersions:
    def test_default_versions(self):
        v = RuntimeVersions()
        assert v.graph_version == "0.0.0"
        assert v.knowledge_version == "0.0.0"
        assert v.policy_version == "0.0.0"
        assert v.provider_version == "0.0.0"
        assert v.interpretation_version == "0.0.0"
        assert v.reasoning_version == "1.0.0"
        assert v.router_version == "0.0.0"

    def test_to_dict(self):
        v = RuntimeVersions()
        d = v.to_dict()
        assert "graph_version" in d
        assert "knowledge_version" in d
        assert "policy_version" in d
        assert "provider_version" in d
        assert "interpretation_version" in d
        assert "reasoning_version" in d
        assert "router_version" in d


class TestVersionTracker:
    def test_creates_with_defaults(self):
        t = VersionTracker()
        v = t.get_versions()
        assert v.graph_version == "0.0.0"

    def test_update_graph_version(self):
        t = VersionTracker()
        t.update_graph_version("2.0.0")
        assert t.get_versions().graph_version == "2.0.0"

    def test_update_knowledge_version(self):
        t = VersionTracker()
        t.update_knowledge_version("3.1.0")
        assert t.get_versions().knowledge_version == "3.1.0"

    def test_update_all_versions(self):
        t = VersionTracker()
        t.update_graph_version("1.0.0")
        t.update_knowledge_version("2.0.0")
        t.update_policy_version("3.0.0")
        t.update_provider_version("4.0.0")
        t.update_interpretation_version("5.0.0")
        t.update_reasoning_version("6.0.0")
        t.update_router_version("7.0.0")
        v = t.get_versions()
        assert v.graph_version == "1.0.0"
        assert v.knowledge_version == "2.0.0"
        assert v.policy_version == "3.0.0"
        assert v.provider_version == "4.0.0"
        assert v.interpretation_version == "5.0.0"
        assert v.reasoning_version == "6.0.0"
        assert v.router_version == "7.0.0"

    def test_get_engine_version(self):
        t = VersionTracker()
        assert t.get_engine_version("pipeline") == "1.0.0"
        assert t.get_engine_version("dialogue") == "1.0.0"
        assert t.get_engine_version("nonexistent") == "0.0.0"

    def test_record_execution(self):
        t = VersionTracker()
        t.update_graph_version("1.0.0")
        record = t.record_execution("exec-123", t.get_versions())
        assert record["execution_id"] == "exec-123"
        assert "versions" in record
        assert "engine_versions" in record


class TestEngineVersions:
    def test_all_engines_have_versions(self):
        expected = [
            "pipeline", "dialogue", "graph_reasoning", "interpretation",
            "epistemic_safety", "knowledge_concepts", "cross_book_linking",
            "knowledge_curation", "profile_generator", "hierarchical_profile",
            "ai_router", "query_concept_resolver",
        ]
        for engine in expected:
            assert engine in ENGINE_VERSIONS
            assert ENGINE_VERSIONS[engine] == "1.0.0"
