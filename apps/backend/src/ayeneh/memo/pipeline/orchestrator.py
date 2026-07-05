"""MEMO memory pipeline orchestrator."""

from __future__ import annotations

from typing import Any


class MEMOPipelineOrchestrator:
    """Orchestrates the MEMO memory pipeline across all 10 modules."""

    def __init__(self) -> None:
        self._engines: dict[str, Any] = {}

    def _get_engine(self, module: str) -> Any:
        if module not in self._engines:
            self._engines[module] = self._create_engine(module)
        return self._engines[module]

    @staticmethod
    def _create_engine(module: str) -> Any:
        if module == "episodic":
            from ayeneh.memo.episodic.engine import EpisodicMemoryEngine
            return EpisodicMemoryEngine()
        if module == "semantic":
            from ayeneh.memo.semantic.engine import SemanticMemoryEngine
            return SemanticMemoryEngine()
        if module == "working":
            from ayeneh.memo.working.engine import WorkingMemoryEngine
            return WorkingMemoryEngine()
        if module == "consolidation":
            from ayeneh.memo.consolidation.engine import ConsolidationEngine
            return ConsolidationEngine()
        if module == "retrieval":
            from ayeneh.memo.retrieval.engine import RetrievalEngine
            return RetrievalEngine()
        if module == "ranking":
            from ayeneh.memo.ranking.engine import RankingEngine
            return RankingEngine()
        if module == "forgetting":
            from ayeneh.memo.forgetting.engine import ForgettingEngine
            return ForgettingEngine()
        if module == "knowledge_graph":
            from ayeneh.memo.knowledge_graph.graph import KnowledgeGraphModule
            return KnowledgeGraphModule()
        if module == "versioning":
            from ayeneh.memo.versioning.engine import VersioningEngine
            return VersioningEngine()
        return None

    async def run_pipeline(self, module: str, data: dict[str, Any]) -> dict[str, Any]:
        engine = self._get_engine(module)
        if engine and hasattr(engine, "run_pipeline"):
            result = engine.run_pipeline(data)
            if hasattr(result, "__dict__"):
                return result.__dict__
            return result if isinstance(result, dict) else {"result": result}
        return {"status": "engine_not_available", "module": module}
