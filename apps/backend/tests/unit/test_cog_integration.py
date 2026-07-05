"""Integration tests for the COG cognitive architecture pipeline."""

from __future__ import annotations

import pytest

from ayeneh.cog.pipeline.orchestrator import CognitivePipelineOrchestrator, PIPELINE_PHASES
from ayeneh.cog.pipeline.graph import CognitiveGraph


class TestPipelineOrchestrator:
    def test_pipeline_phases_defined(self) -> None:
        assert len(PIPELINE_PHASES) == 15
        assert PIPELINE_PHASES[0] == "conversation_understanding"
        assert PIPELINE_PHASES[-1] == "meta_cognition"

    def test_orchestrator_creation(self) -> None:
        orch = CognitivePipelineOrchestrator()
        assert orch.has_module("conversation_understanding") is False

    def test_register_module(self) -> None:
        orch = CognitivePipelineOrchestrator()

        class FakeModule:
            async def process(self, data):
                return data

        orch.register("conversation_understanding", FakeModule())
        assert orch.has_module("conversation_understanding") is True

    @pytest.mark.asyncio
    async def test_process_empty_pipeline(self) -> None:
        orch = CognitivePipelineOrchestrator()
        result = await orch.process({"messages": []})
        assert isinstance(result, dict)
        assert "messages" in result

    @pytest.mark.asyncio
    async def test_process_with_single_module(self) -> None:
        orch = CognitivePipelineOrchestrator()

        class PassThrough:
            async def process(self, data):
                data["processed"] = True
                return data

        orch.register("conversation_understanding", PassThrough())
        result = await orch.process({"messages": []})
        assert result.get("processed") is True

    @pytest.mark.asyncio
    async def test_process_chains_modules(self) -> None:
        orch = CognitivePipelineOrchestrator()

        class AddStep1:
            async def process(self, data):
                data["steps"] = data.get("steps", []) + ["step1"]
                return data

        class AddStep2:
            async def process(self, data):
                data["steps"] = data.get("steps", []) + ["step2"]
                return data

        orch.register("conversation_understanding", AddStep1())
        orch.register("evidence_extraction", AddStep2())
        result = await orch.process({})
        assert result["steps"] == ["step1", "step2"]

    @pytest.mark.asyncio
    async def test_process_skips_unregistered(self) -> None:
        orch = CognitivePipelineOrchestrator()

        class AddStep:
            async def process(self, data):
                data["steps"] = data.get("steps", []) + ["evidence"]
                return data

        orch.register("evidence_extraction", AddStep())
        result = await orch.process({})
        assert result["steps"] == ["evidence"]

    @pytest.mark.asyncio
    async def test_process_raises_on_failure(self) -> None:
        orch = CognitivePipelineOrchestrator()

        class FailingModule:
            async def process(self, data):
                raise ValueError("test error")

        orch.register("conversation_understanding", FailingModule())
        with pytest.raises(ValueError, match="test error"):
            await orch.process({})


class TestCognitiveGraph:
    def test_creation(self) -> None:
        g = CognitiveGraph()
        assert g is not None

    def test_add_and_get_node(self) -> None:
        from ayeneh.cog.base import CognitiveObject
        g = CognitiveGraph()
        obj = CognitiveObject(identifier="test-1", object_type="belief", creation_timestamp=None)
        g.add_node(obj)
        assert g.get_node("test-1") is not None

    def test_get_nonexistent_node(self) -> None:
        g = CognitiveGraph()
        assert g.get_node("nonexistent") is None

    def test_add_edge(self) -> None:
        from ayeneh.cog.base import CognitiveObject
        from ayeneh.cog.pipeline.graph import GraphEdge
        g = CognitiveGraph()
        obj1 = CognitiveObject(identifier="n1", object_type="belief", creation_timestamp=None)
        obj2 = CognitiveObject(identifier="n2", object_type="narrative", creation_timestamp=None)
        g.add_node(obj1)
        g.add_node(obj2)
        edge = GraphEdge(source_id="n1", target_id="n2", relationship="supports", confidence=0.8)
        g.add_edge(edge)
        edges = g.get_edges_from("n1")
        assert len(edges) == 1
        assert edges[0].relationship == "supports"

    def test_traverse(self) -> None:
        from ayeneh.cog.base import CognitiveObject
        from ayeneh.cog.pipeline.graph import GraphEdge
        g = CognitiveGraph()
        for i in range(3):
            g.add_node(CognitiveObject(identifier=f"n{i}", object_type="belief", creation_timestamp=None))
        g.add_edge(GraphEdge(source_id="n0", target_id="n1", relationship="supports", confidence=0.9))
        g.add_edge(GraphEdge(source_id="n1", target_id="n2", relationship="supports", confidence=0.9))
        result = g.traverse("n0", "supports", max_depth=3)
        assert len(result) >= 2
