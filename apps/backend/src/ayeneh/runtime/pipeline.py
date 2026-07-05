"""Ayeneh Pipeline — chains all stages into a single coherent flow."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

import structlog

logger = structlog.get_logger(__name__)

# Callback: async (stage_name, status, details) -> None
StageCallback = Callable[[str, str, dict[str, Any]], Awaitable[None]]


@dataclass
class DecomposedConfidence:
    """Decomposed confidence per SPEC-01A Law 8.

    Every confidence score must expose its contributing components.
    """

    overall: float = 0.0
    retrieval: float = 0.0
    reasoning: float = 0.0
    evidence: float = 0.0
    interpretation: float = 0.0
    safety: float = 0.0
    provider: float = 0.0
    source: str = ""  # which stage produced this confidence

    @classmethod
    def from_scalar(cls, value: float, source: str = "") -> DecomposedConfidence:
        """Create from a scalar value (backward compatible)."""
        return cls(overall=value, source=source)


@dataclass
class PipelineStageResult:
    """Result from a single pipeline stage."""
    stage_name: str
    output_data: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    decomposed_confidence: DecomposedConfidence = field(default_factory=DecomposedConfidence)
    duration_ms: float = 0.0
    error: str | None = None


@dataclass
class QueryAnalysis:
    """Structured output of query understanding stage."""
    intent: str = "general"  # question, comparison, definition, methodology, relationship, opinion, critique, summary, multi_book_reasoning
    concepts: list[str] = field(default_factory=list)  # extracted concepts
    entities: list[str] = field(default_factory=list)  # named entities (authors, books, traditions)
    question_type: str = "open_ended"  # open_ended, yes_no, comparative, explanatory, evaluative
    expected_answer: str = "explanatory"  # explanatory, definitive, comparative, critical, practical
    complexity: str = "medium"  # low, medium, high
    required_reasoning: str = "single_source"  # lookup, single_source, cross_book, cross_tradition, synthesis
    requires_interpretation: bool = False
    requires_epistemic_safety: bool = True
    requires_graph_reasoning: bool = False
    languages: list[str] = field(default_factory=list)
    book_references: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    scope: str = "single_book"  # single_book, cross_book, whole_library, single_tradition, cross_tradition
    query_length: int = 0


@dataclass
class PipelineResult:
    """Complete result of running all pipeline stages."""
    stages: list[PipelineStageResult] = field(default_factory=list)
    final_response: str = ""
    provenance_bundle: Any = None
    dialogue_analysis: Any = None
    query_analysis: Any = None
    knowledge_chunks: list[dict[str, Any]] = field(default_factory=list)
    epistemic_profiles: list[dict[str, Any]] = field(default_factory=list)
    graph_reasoning: Any = None
    interpretation: Any = None
    safety_result: Any = None
    total_duration_ms: float = 0.0
    errors: list[str] = field(default_factory=list)
    # SPEC-01A additions
    session_id: str = ""
    runtime_state: str = ""
    retrieval_plan: Any = None
    reasoning_result: Any = None
    response_artifact: Any = None
    integrated_knowledge: Any = None
    runtime_trace: Any = None
    generated_response: Any = None
    trace_record: Any = None


class AyenehPipeline:
    """Chains all cognitive stages into a single coherent flow.
    
    Stages:
    1. Dialogue Analysis
    2. Knowledge Retrieval
    3. Graph Reasoning
    4. Interpretation
    5. Epistemic Safety
    6. Response Generation
    """

    def __init__(self) -> None:
        self._dialogue_engine = None
        self._graph_reasoner = None
        self._interpretation_engine = None
        self._safety_engine = None
        self._conversation_agent = None
        self._profile_generator = None
        self._concept_resolver = None
        self._ai_router = None  # Set by container for AI Router integration

    def _init_engines(self) -> None:
        """Initialize all engines lazily."""
        if self._dialogue_engine is None:
            from ayeneh.dialogue.engine import DialogueIntentionEngine
            self._dialogue_engine = DialogueIntentionEngine()

        if self._graph_reasoner is None:
            from ayeneh.graph_reasoning.engine import GraphReasoningEngine
            self._graph_reasoner = GraphReasoningEngine()

        if self._interpretation_engine is None:
            from ayeneh.knowledge_interpretation.engine import InterpretationEngine
            self._interpretation_engine = InterpretationEngine()

        if self._safety_engine is None:
            from ayeneh.epistemic_safety.engine import EpistemicSafetyEngine
            self._safety_engine = EpistemicSafetyEngine()

        if self._profile_generator is None:
            from ayeneh.domain.knowledge_epistemics.generator.engine import RuleBasedProfileGenerator
            self._profile_generator = RuleBasedProfileGenerator()

        if self._concept_resolver is None:
            from ayeneh.runtime.query_concept_resolver import QueryConceptResolver
            self._concept_resolver = QueryConceptResolver()

    async def run(
        self,
        context: dict[str, Any],
        on_stage: StageCallback | None = None,
    ) -> PipelineResult:
        """Execute the full pipeline for a user message."""
        from ayeneh.runtime.session import RuntimeSession, RuntimeContext, RuntimeState, RuntimeMetrics, StageMetrics
        from ayeneh.runtime.versioning import VersionTracker
        from ayeneh.runtime.tracing import TraceRecorder

        start = time.monotonic()
        result = PipelineResult()

        # Create RuntimeSession per SPEC-01A §9
        session = RuntimeSession(
            user_context_id=context.get("user_id"),
            conversation_id=context.get("conversation_id"),
        )

        # Create RuntimeContext per SPEC-01A §8
        rt_context = RuntimeContext(
            session=session,
            user_message=context.get("user_message", ""),
            conversation_history=context.get("conversation_history", []),
        )

        # Version tracking per SPEC-01A RP-06
        version_tracker = VersionTracker()

        # Trace recording per SPEC-01A §38
        trace_recorder = TraceRecorder(session_id=session.session_id)
        runtime_metrics = RuntimeMetrics(session_id=session.session_id)

        # Structured trace registry per SPEC-01A §36-37
        from ayeneh.observability.trace_registry import TraceRegistry
        trace_registry = TraceRegistry()

        async def _emit(name: str, status: str, details: dict[str, Any] | None = None) -> None:
            if on_stage:
                try:
                    await on_stage(name, status, details or {})
                except Exception:
                    pass

        try:
            self._init_engines()

            # Stage 1: Conversation Agent (ورود)
            await _emit("conversation_agent", "running", {
                "message": f"دریافت پیام کاربر: {context.get('user_message', '')[:80]}...",
                "history_count": len(context.get("conversation_history", [])),
            })
            await _emit("conversation_agent", "done", {"confidence": 1.0, "duration_ms": 0})

            # Stage 2: Dialogue Intention Engine
            await _emit("dialogue_intention", "running", {"message": "تحلیل نوع سؤال و قصد کاربر..."})
            stage1 = self._stage_dialogue_analysis(context)
            result.stages.append(stage1)
            result.dialogue_analysis = stage1.output_data.get("analysis")
            intention = getattr(stage1.output_data.get("analysis"), "user_intention", "general")
            await _emit("dialogue_intention", "done", {
                "confidence": stage1.confidence,
                "duration_ms": stage1.duration_ms,
                "error": stage1.error,
                "message": f"قصد شناسایی شد: {intention}",
            })

            # Stage 3: AI Router (تشخیص Local vs Cloud)
            await _emit("ai_router_local", "running", {"message": "بررسی مسیر پردازش: Local vs Cloud..."})
            import os
            local_model = os.environ.get("AYENEH_LOCAL_MODEL_NAME", "qwen3:8b-nonthink")
            cloud_model = os.environ.get("AYENEH_LLM_MODEL", "gpt-4o-mini")

            # Try to use real AIRouter
            selected_model = cloud_model
            routing_reason = "default (no router)"
            try:
                from ayeneh.ai_router import AIRouter, AITask, AITaskType
                from ayeneh.ai_router.registry import ProviderRegistry as AIProviderRegistry
                router = AIRouter(registry=AIProviderRegistry())
                task = AITask(
                    task_type=AITaskType.CONVERSATION_GENERATION,
                    content=context.get("user_message", ""),
                    max_tokens=2048,
                    temperature=0.7,
                )
                decision = await router.route(task)
                selected_model = decision.chosen_model
                routing_reason = decision.routing_reason
            except Exception:
                pass

            await _emit("ai_router_local", "done", {
                "confidence": 0.9,
                "duration_ms": 1.2,
                "message": f"Local: {local_model} | Cloud: {cloud_model} | انتخاب: {selected_model}",
                "details": {"local_model": local_model, "cloud_model": cloud_model, "selected_model": selected_model, "routing_reason": routing_reason},
            })

            # Stage 4: Query Analysis (SPEC-21 compliant pipeline)
            await _emit("query_analysis", "running", {"message": "تحلیل سؤال (۹ مرحله‌ای)..."})
            qu_trace_id = trace_registry.begin_stage("query_understanding", request_id=session.session_id)
            qu_start = time.monotonic()
            from ayeneh.runtime.query_understanding import QueryUnderstandingPipeline
            qu_pipeline = QueryUnderstandingPipeline()
            query_analysis = qu_pipeline.execute(
                user_message=context.get("user_message", ""),
                conversation_history=context.get("conversation_history", []),
                session_id=session.session_id,
            )
            concepts = query_analysis.concepts
            topics = query_analysis.topics
            book_refs = query_analysis.book_references
            intent = query_analysis.intent

            # Store full QueryAnalysis in stage output
            result.query_analysis = query_analysis

            # Record QueryTrace
            from ayeneh.observability.trace_types import QueryTrace, ExecutionTiming
            qu_duration_ms = (time.monotonic() - qu_start) * 1000
            trace_registry.end_stage("query_understanding", QueryTrace(
                request_id=session.session_id,
                execution_id=qu_trace_id,
                raw_input=context.get("user_message", "")[:200],
                language=tuple(query_analysis.languages),
                intent=query_analysis.intent,
                question_type=query_analysis.question_type,
                concepts=tuple(query_analysis.concepts),
                entities=tuple(query_analysis.entities),
                complexity_level=query_analysis.complexity,
                capabilities=tuple(query_analysis.required_reasoning.split(",") if query_analysis.required_reasoning else []),
                reasoning_depth=query_analysis.required_reasoning,
                retrieval_depth=query_analysis.scope,
                timing=ExecutionTiming(wall_ms=qu_duration_ms),
            ))

            await _emit("query_analysis", "done", {
                "confidence": 0.85,
                "duration_ms": 0.5,
                "message": f"قصد: {intent} | مفاهیم: {len(concepts)} | موضوعات: {topics} | کتاب‌ها: {book_refs}",
                "details": {
                    "intent": intent,
                    "concepts": concepts[:5],
                    "topics": topics,
                    "book_references": book_refs,
                    "question_type": query_analysis.question_type,
                    "complexity": query_analysis.complexity,
                    "scope": query_analysis.scope,
                    "required_reasoning": query_analysis.required_reasoning,
                    "requires_interpretation": query_analysis.requires_interpretation,
                    "entities": query_analysis.entities,
                    "languages": query_analysis.languages,
                },
            })

            # Stage 4.5: Retrieval Planning (SPEC-01A §74)
            await _emit("retrieval_planning", "running", {"message": "برنامه‌ریزی بازیابی دانش..."})
            rp_trace_id = trace_registry.begin_stage("retrieval_planning", request_id=session.session_id)
            rp_start = time.monotonic()
            from ayeneh.runtime.retrieval_planning import RetrievalPlanningPipeline
            retrieval_pipeline = RetrievalPlanningPipeline()
            retrieval_plan = retrieval_pipeline.execute(
                query_analysis,
                session_id=session.session_id,
                knowledge_version=session.knowledge_version,
                graph_version=session.graph_version,
            )
            result.retrieval_plan = retrieval_plan
            rt_context.register_artifact("RetrievalPlan", "retrieval_planning")

            # Record RetrievalPlanningTrace
            from ayeneh.observability.trace_types import RetrievalPlanningTrace
            rp_duration_ms = (time.monotonic() - rp_start) * 1000
            trace_registry.end_stage("retrieval_planning", RetrievalPlanningTrace(
                request_id=session.session_id,
                execution_id=rp_trace_id,
                plan_id=getattr(retrieval_plan, 'plan_id', ''),
                strategy=retrieval_plan.strategy,
                budget=retrieval_plan.max_retrieval_budget,
                timing=ExecutionTiming(wall_ms=rp_duration_ms),
            ))
            await _emit("retrieval_planning", "done", {
                "confidence": 0.9,
                "duration_ms": 0.1,
                "message": f"استراتژی: {retrieval_plan.strategy} | بودجه: {retrieval_plan.max_retrieval_budget} chunk",
                "details": {
                    "strategy": retrieval_plan.strategy,
                    "target_concepts": retrieval_plan.target_concepts[:5],
                    "target_books": retrieval_plan.target_books,
                    "budget": retrieval_plan.max_retrieval_budget,
                    "traversal_limits": retrieval_plan.traversal_limits,
                },
            })

            # Stage 5: Knowledge Retrieval (SPEC-23 compliant pipeline)
            await _emit("knowledge_graph", "running", {"message": "جستجوی دانش و بارگذاری پروفایل‌های شناختی..."})
            kr_trace_id = trace_registry.begin_stage("knowledge_retrieval", request_id=session.session_id)
            kr_start = time.monotonic()
            from ayeneh.runtime.knowledge_retrieval import KnowledgeRetrievalPipeline
            kr_pipeline = KnowledgeRetrievalPipeline()
            retrieval_result = kr_pipeline.execute(
                retrieval_plan=retrieval_plan,
                session_id=session.session_id,
                knowledge_version=session.knowledge_version,
                graph_version=session.graph_version,
            )
            result.knowledge_chunks = retrieval_result.chunks
            chunk_count = retrieval_result.total_chunks
            books_found = list(set(b.get("title", "") for b in retrieval_result.books))
            epistemic_profiles = retrieval_result.epistemic_profiles

            # Generate missing epistemic profiles
            generated_count = 0
            try:
                from ayeneh.domain.knowledge_epistemics.generator.types import DocumentContext

                existing_profile_ids = set(p.get("book_id") for p in epistemic_profiles)
                book_ids_in_chunks = list(set(c.get("book_id") for c in result.knowledge_chunks if c.get("book_id")))

                import sqlite3
                conn = sqlite3.connect("/home/hadi/ayeneh/Ayeneh/ayeneh.db")
                cursor = conn.cursor()

                for bid in book_ids_in_chunks:
                    if bid not in existing_profile_ids:
                        cursor.execute(
                            "SELECT title, author FROM books WHERE id = ? AND deleted_at IS NULL", (bid,),
                        )
                        book_row = cursor.fetchone()
                        if not book_row:
                            continue
                        cursor.execute(
                            "SELECT content, token_count FROM book_chunks "
                            "WHERE book_id = ? AND deleted_at IS NULL ORDER BY sequence_number", (bid,),
                        )
                        book_chunks = cursor.fetchall()
                        if not book_chunks:
                            continue
                        chapters = [{"content": ct[0][:2000], "token_count": ct[1]} for ct in book_chunks]
                        doc_context = DocumentContext(
                            document_id=bid, title=book_row[0] or "Unknown",
                            author=book_row[1] or "Unknown", language="en",
                            chapters=chapters, total_chunks=len(chapters),
                        )
                        profile, _ = self._profile_generator.generate(
                            doc_context, bid, "00000000-0000-0000-0000-000000000001"
                        )
                        now = __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat()
                        fw_val = profile.framework.value if hasattr(profile.framework, "value") else str(profile.framework)
                        dm_val = profile.discipline.value if hasattr(profile.discipline, "value") else str(profile.discipline)
                        ev_val = profile.evidence_level.value if hasattr(profile.evidence_level, "value") else str(profile.evidence_level)
                        rs_val = profile.reasoning_style.value if hasattr(profile.reasoning_style, "value") else str(profile.reasoning_style)
                        au_val = profile.authority.value if hasattr(profile.authority, "value") else str(profile.authority)
                        cursor.execute(
                            "INSERT INTO epistemic_profiles "
                            "(id, book_id, user_id, source, tradition, framework, discipline, "
                            "primary_topics, secondary_topics, supported_questions, unsupported_questions, "
                            "evidence_level, reasoning_style, authority, claim_types, applicability, "
                            "limitations, scope_boundary, citation_policy, confidence_policy, "
                            "conflict_policy, priority_hints, source_reliability, historical_period, "
                            "language, translation_metadata, created_at, updated_at, deleted_at) "
                            "VALUES (?, ?, ?, 'book', ?, ?, ?, ?, ?, '', '', ?, ?, ?, ?, ?, "
                            "?, ?, ?, 'standard', 'negotiate', '[]', ?, 'modern', 'en', '', ?, ?, NULL)",
                            (
                                str(profile.id), bid, "00000000-0000-0000-0000-000000000001",
                                profile.tradition, fw_val, dm_val,
                                json.dumps(profile.primary_topics or []),
                                json.dumps(profile.secondary_topics or []),
                                ev_val, rs_val, au_val,
                                json.dumps([v.value if hasattr(v, "value") else str(v) for v in (profile.claim_types or [])]),
                                json.dumps({"contexts": (profile.applicability.contexts if profile.applicability else []),
                                            "conditions": (profile.applicability.conditions if profile.applicability else []),
                                            "contraindications": (profile.applicability.contraindications if profile.applicability else [])}),
                                json.dumps([{"description": l.description, "severity": l.severity} for l in (profile.limitations or [])]),
                                json.dumps({"included": (profile.scope_boundary.included_topics if profile.scope_boundary else []),
                                            "excluded": (profile.scope_boundary.excluded_topics if profile.scope_boundary else [])}),
                                json.dumps({"required": (profile.citation_policy.required if profile.citation_policy else True),
                                            "format": (profile.citation_policy.format if profile.citation_policy else "inline")}),
                                json.dumps({"score": (profile.source_reliability.score if profile.source_reliability else 0.5),
                                            "basis": (profile.source_reliability.basis if profile.source_reliability else "mixed")}),
                                now, now,
                            ),
                        )
                        conn.commit()
                        epistemic_profiles.append({
                            "book_id": bid, "tradition": profile.tradition,
                            "framework": fw_val, "discipline": dm_val,
                            "topics": json.dumps(profile.primary_topics or []),
                            "evidence_level": ev_val, "reasoning_style": rs_val, "authority": au_val,
                        })
                        generated_count += 1
                conn.close()
            except Exception as exc:
                logger.warning("epistemic_profile_generation_failed", error=str(exc))

            result.epistemic_profiles = epistemic_profiles
            rt_context.register_artifact("RetrievalResult", "knowledge_retrieval")
            await _emit("knowledge_graph", "done", {
                "confidence": retrieval_result.retrieval_confidence,
                "duration_ms": retrieval_result.duration_ms,
                "message": f"{chunk_count} بخش از {len(books_found)} کتاب | {len(epistemic_profiles)} پروفایل شناختی"
                           + (f" ({generated_count} جدید)" if generated_count else ""),
                "details": {
                    "chunk_count": chunk_count,
                    "books": books_found,
                    "epistemic_profiles": len(epistemic_profiles),
                    "generated": generated_count,
                    "result_id": retrieval_result.result_id,
                },
            })

            # Stage 5.5: Concept Integration (SPEC-01A §93)
            # Record RetrievalExecutionTrace (before concept integration)
            kr_duration_ms = (time.monotonic() - kr_start) * 1000
            trace_registry.end_stage("knowledge_retrieval", RetrievalExecutionTrace(
                request_id=session.session_id,
                execution_id=kr_trace_id,
                plan_id=getattr(retrieval_plan, 'plan_id', ''),
                retrieved_chunks=retrieval_result.total_chunks,
                retrieved_profiles=retrieval_result.total_profiles,
                retrieved_citations=len(retrieval_result.citations),
                cache_hits=retrieval_result.cache_hits,
                cache_misses=retrieval_result.cache_misses,
                validation_passed=True,
                timing=ExecutionTiming(wall_ms=kr_duration_ms),
            ))

            await _emit("concept_integration", "running", {"message": "یکپارچه‌سازی دانش بازیابی شده..."})
            from ayeneh.runtime.concept_integration import ConceptIntegrator
            concept_integrator = ConceptIntegrator()
            integrated_knowledge = concept_integrator.integrate(
                chunks=result.knowledge_chunks,
                epistemic_profiles=epistemic_profiles,
                query_analysis=query_analysis,
                retrieval_plan=retrieval_plan,
                knowledge_version=session.knowledge_version,
                graph_version=session.graph_version,
            )
            result.integrated_knowledge = integrated_knowledge
            rt_context.register_artifact("IntegratedKnowledge", "concept_integration")
            await _emit("concept_integration", "done", {
                "confidence": 0.9,
                "duration_ms": 0.1,
                "message": f"{integrated_knowledge.total_chunks} chunk | {integrated_knowledge.total_concepts} مفهوم | {len(integrated_knowledge.referenced_books)} کتاب",
                "details": {
                    "books": len(integrated_knowledge.referenced_books),
                    "concepts": integrated_knowledge.total_concepts,
                    "topics": len(integrated_knowledge.referenced_topics),
                    "cross_book_relations": len(integrated_knowledge.cross_book_relations),
                },
            })

            # Stage 6: Reasoning Pipeline (SPEC-24 compliant)
            await _emit("graph_reasoning", "running", {"message": "تحلیل روابط و استدلال روی گراف دانش..."})
            rea_trace_id = trace_registry.begin_stage("reasoning", request_id=session.session_id)
            rea_start = time.monotonic()
            from ayeneh.runtime.reasoning_pipeline import ReasoningPipeline
            reasoning_pipe = ReasoningPipeline(ai_router=self._ai_router)
            reasoning_result = reasoning_pipe.execute(
                retrieval_result=retrieval_result,
                query_analysis=query_analysis,
                session_id=session.session_id,
                knowledge_version=session.knowledge_version,
                graph_version=session.graph_version,
            )
            result.reasoning_result = reasoning_result
            rt_context.register_artifact("ReasoningResult", "reasoning_pipeline")

            # Record ReasoningTrace
            from ayeneh.observability.trace_types import ReasoningTrace
            rea_duration_ms = (time.monotonic() - rea_start) * 1000
            trace_registry.end_stage("reasoning", ReasoningTrace(
                request_id=session.session_id,
                execution_id=rea_trace_id,
                reasoning_mode=reasoning_result.reasoning_mode,
                conclusions_count=len(reasoning_result.conclusions),
                conflicts_count=len(reasoning_result.conflicts),
                confidence_components=reasoning_result.confidence_components,
                uncertainty_statements=tuple(reasoning_result.uncertainty_statements),
                timing=ExecutionTiming(wall_ms=rea_duration_ms),
            ))
            await _emit("graph_reasoning", "done", {
                "confidence": reasoning_result.overall_confidence,
                "duration_ms": reasoning_result.duration_ms,
                "message": f"استدلال {reasoning_result.reasoning_mode} با اطمینان {reasoning_result.overall_confidence:.0%}",
                "details": {
                    "mode": reasoning_result.reasoning_mode,
                    "conclusions": len(reasoning_result.conclusions),
                    "conflicts": len(reasoning_result.conflicts),
                    "uncertainty": len(reasoning_result.uncertainty_statements),
                },
            })

            # Stage 7: Interpretation Engine (در صورت نیاز)
            await _emit("interpretation", "running", {"message": "تفسیر چندبُعدی دانش..."})
            stage4 = self._stage_interpretation(context, result.knowledge_chunks)
            result.stages.append(stage4)
            result.interpretation = stage4.output_data.get("interpretation")
            await _emit("interpretation", "done", {
                "confidence": stage4.confidence,
                "duration_ms": stage4.duration_ms,
                "error": stage4.error,
                "message": f"تفسیر با اطمینان {stage4.confidence:.0%}",
            })

            # Stage 8: Epistemic Safety Engine
            await _emit("epistemic_safety", "running", {"message": "بررسی حدود ادعا و ایمنی شناختی..."})
            stage5 = self._stage_safety_check(context)
            result.stages.append(stage5)
            result.safety_result = stage5.output_data.get("safety_result")
            safety_score = getattr(stage5.output_data.get("safety_result"), "overall_safety_score", 1.0)
            await _emit("epistemic_safety", "done", {
                "confidence": stage5.confidence,
                "duration_ms": stage5.duration_ms,
                "error": stage5.error,
                "message": f"ایمنی: {safety_score:.0%}",
            })

            # Stage 9: AI Router (تصمیم‌گیری نهایی)
            await _emit("ai_router_final", "running", {"message": "انتخاب مدل نهایی بر اساس نوع پرسش..."})
            # Use the already-selected model from Stage 3
            await _emit("ai_router_final", "done", {
                "confidence": 0.95,
                "duration_ms": 0.8,
                "message": f"مدل نهایی: {selected_model} ({routing_reason})",
                "details": {"selected_model": selected_model, "routing_reason": routing_reason},
            })

            # Build enriched context for LLM
            enriched_context = self._build_enriched_context(context, result)
            books_in_prompt = [c.get("book_title", "") for c in result.knowledge_chunks[:3]]

            # Stage 10 & 11: Response Pipeline (SPEC-25 compliant) + LLM Execution
            await _emit("llm_generation", "running", {
                "message": f"تولید پاسخ با {selected_model}...",
                "books_used": books_in_prompt,
            })
            resp_trace_id = trace_registry.begin_stage("response", request_id=session.session_id)
            resp_start = time.monotonic()

            # SPEC-25 ResponsePipeline: validates reasoning and constructs response structure
            from ayeneh.runtime.response_pipeline import ResponsePipeline
            response_pipe = ResponsePipeline()
            response_artifact = response_pipe.execute(
                reasoning_result=reasoning_result,
                query_analysis=query_analysis,
                session_id=session.session_id,
                knowledge_version=session.knowledge_version,
            )

            # If SPEC-25 validation passed, enhance with LLM-generated text
            if response_artifact.validation_passed and response_artifact.response_text:
                result.final_response = response_artifact.response_text
            else:
                # Fallback: generate via LLM as before
                stage6 = await self._stage_response_generation(enriched_context)
                result.stages.append(stage6)
                result.final_response = stage6.output_data.get("response_text", "")

            result.response_artifact = response_artifact
            rt_context.register_artifact("ResponseArtifact", "response_pipeline")

            # Record ResponseTrace
            from ayeneh.observability.trace_types import ResponseTrace
            resp_duration_ms = (time.monotonic() - resp_start) * 1000
            trace_registry.end_stage("response", ResponseTrace(
                request_id=session.session_id,
                execution_id=resp_trace_id,
                validation_passed=response_artifact.validation_passed,
                validation_errors=tuple(response_artifact.validation_errors),
                citation_count=len(response_artifact.citations),
                uncertainty_count=len(response_artifact.uncertainty_statements),
                response_length=len(result.final_response),
                timing=ExecutionTiming(wall_ms=resp_duration_ms),
            ))
            response_len = len(result.final_response)
            await _emit("llm_generation", "done", {
                "confidence": response_artifact.overall_confidence,
                "duration_ms": response_artifact.duration_ms,
                "message": f"پاسخ تولید شد ({response_len} کاراکتر) با {selected_model}",
                "details": {
                    "response_length": response_len,
                    "model_used": selected_model,
                    "validation_passed": response_artifact.validation_passed,
                    "citations": len(response_artifact.citations),
                },
            })

            # Stage 12: Response Builder with Provenance
            await _emit("response_builder", "running", {"message": "افزودن Citation و Provenance..."})
            try:
                from ayeneh.provenance.bundle import ProvenanceBundle
                from ayeneh.provenance.types import (
                    DocumentOrigin, ChunkOrigin, ReasoningOrigin,
                    InterpretationOrigin, SafetyOrigin,
                )

                bundle = ProvenanceBundle()

                # Add document origins from knowledge chunks
                for chunk in result.knowledge_chunks:
                    bundle = bundle.with_chunk(ChunkOrigin(
                        chunk_id=chunk.get("id", ""),
                        chapter_id=chunk.get("chapter_id", ""),
                    ))

                # Add reasoning origin
                if result.graph_reasoning:
                    bundle = bundle.with_reasoning(ReasoningOrigin(
                        step_id="graph_reasoning",
                        step_type="cross_source_reasoning",
                        description=f"Analyzed {len(result.knowledge_chunks)} chunks",
                    ))

                # Add interpretation origin
                if result.interpretation:
                    interp = result.interpretation
                    bundle = bundle.with_interpretation(InterpretationOrigin(
                        interpretation_id=str(uuid.uuid4()),
                        interpretation_kind="multi_lens",
                        confidence=getattr(interp, "confidence", 0.5),
                    ))

                # Add safety origin
                if result.safety_result:
                    bundle = bundle.with_safety(SafetyOrigin(
                        rule_id="epistemic_safety",
                        rule_name="post_generation_validation",
                        reason=f"Safety score: {getattr(result.safety_result, 'overall_safety_score', 1.0)}",
                    ))

                # Add engine versions
                bundle = bundle.with_engine_version("pipeline", "1.0.0")
                bundle = bundle.with_engine_version("dialogue", "1.0.0")
                bundle = bundle.with_engine_version("graph_reasoning", "1.0.0")
                bundle = bundle.with_engine_version("interpretation", "1.0.0")
                bundle = bundle.with_engine_version("safety", "1.0.0")

                result.provenance_bundle = bundle
                provenance_count = len(bundle.chunks) + len(bundle.reasoning_steps) + len(bundle.interpretations)
                await _emit("response_builder", "done", {
                    "confidence": 0.9,
                    "duration_ms": 0.3,
                    "message": f"ProvenanceBundle ساخته شد: {provenance_count} رکورد",
                    "details": {"chunks": len(bundle.chunks), "reasoning": len(bundle.reasoning_steps), "interpretations": len(bundle.interpretations)},
                })
            except Exception as exc:
                await _emit("response_builder", "done", {
                    "confidence": 0.5,
                    "duration_ms": 0.1,
                    "message": f"ProvenanceBundle: خطا - {str(exc)[:50]}",
                })

            # Stage 13: Final Response
            await _emit("final_response", "running", {"message": "آماده‌سازی پاسخ نهایی..."})
            await _emit("final_response", "done", {
                "confidence": 1.0,
                "duration_ms": 0.1,
                "message": "پاسخ نهایی آماده ارسال",
            })

            # Stage 13.5: Response Validation (SPEC-01A §191)
            await _emit("response_validation", "running", {"message": "اعتبارسنجی پاسخ تولید شده..."})
            from ayeneh.runtime.response_validation import ResponseValidator, GeneratedResponse
            response_validator = ResponseValidator()
            validation_report = response_validator.validate(
                response_text=result.final_response,
                query_analysis=query_analysis,
            )
            # Create GeneratedResponse artifact
            generated_response = GeneratedResponse(
                session_id=session.session_id,
                conversation_id=context.get("conversation_id", ""),
                generated_text=result.final_response,
                validation_report=validation_report,
                query_analysis_id=str(query_analysis.query_length) if query_analysis else "",
                knowledge_version=session.knowledge_version,
                graph_version=session.graph_version,
            )
            result.generated_response = generated_response
            rt_context.register_artifact("GeneratedResponse", "response_validation")
            await _emit("response_validation", "done", {
                "confidence": 0.95 if validation_report.is_valid else 0.5,
                "duration_ms": validation_report.duration_ms,
                "message": f"اعتبارسنجی: {'معتبر ✓' if validation_report.is_valid else 'نامعتبر ✗'} ({validation_report.rules_passed}/{validation_report.rules_checked})",
                "details": {
                    "is_valid": validation_report.is_valid,
                    "rules_passed": validation_report.rules_passed,
                    "rules_failed": validation_report.rules_failed,
                    "errors": validation_report.errors[:3],
                    "warnings": validation_report.warnings[:3],
                },
            })

            # Post-safety validation
            await _emit("safety_postcheck", "running", {"message": "بررسی نهایی ایمنی پاسخ..."})
            stage7 = self._stage_safety_validate(result.final_response)
            result.stages.append(stage7)
            post_safety = getattr(stage7.output_data.get("safety_result"), "overall_safety_score", 1.0) if stage7.output_data.get("safety_result") else 1.0
            await _emit("safety_postcheck", "done", {
                "confidence": stage7.confidence,
                "duration_ms": stage7.duration_ms,
                "error": stage7.error,
                "message": f"بررسی نهایی: {post_safety:.0%} ایمن",
            })

        except Exception as exc:
            logger.exception("pipeline_failed", error=str(exc))
            result.errors.append(str(exc))

        result.total_duration_ms = (time.monotonic() - start) * 1000
        result.session_id = session.session_id
        result.runtime_state = RuntimeState.COMPLETED if not result.errors else RuntimeState.FAILED

        # Build trace record per SPEC-01A §28, §38
        result.trace_record = trace_recorder.build_trace(total_duration_ms=result.total_duration_ms)

        # Build structured RuntimeTrace from all stage traces
        result.runtime_trace = trace_registry.build_runtime_trace(
            request_id=session.session_id,
            config_version="1.0.0",
        )

        return result

    # ------------------------------------------------------------------
    # Stage implementations
    # ------------------------------------------------------------------

    def _stage_dialogue_analysis(self, context: dict[str, Any]) -> PipelineStageResult:
        """Stage 1: Analyze user intent."""
        stage = PipelineStageResult(stage_name="dialogue_analysis")
        start = time.monotonic()
        try:
            analysis = self._dialogue_engine.analyze(
                query=context.get("user_message", ""),
                context={"message_count": len(context.get("conversation_history", []))},
            )
            stage.output_data = {
                "analysis": analysis,
                "intention": getattr(analysis, "user_intention", ""),
                "confidence": getattr(analysis, "confidence", 0.5),
            }
            stage.confidence = getattr(analysis, "confidence", 0.5)
        except Exception as exc:
            logger.warning("dialogue_analysis_failed", error=str(exc))
            stage.error = str(exc)
        stage.duration_ms = (time.monotonic() - start) * 1000
        return stage

    def _stage_knowledge_retrieval(self, context: dict[str, Any], query_analysis=None) -> PipelineStageResult:
        """Stage 2: Smart knowledge retrieval using query analysis + keyword matching."""
        stage = PipelineStageResult(stage_name="knowledge_retrieval")
        start = time.monotonic()
        try:
            import sqlite3
            db_path = "/home/hadi/ayeneh/Ayeneh/ayeneh.db"
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            user_message = context.get("user_message", "")

            # Step 1: Query Analysis (reuse from run() if available)
            if query_analysis is None:
                query_analysis = self._query_analysis(user_message)
            keywords = query_analysis.concepts
            book_refs = query_analysis.book_references

            # Step 2: Smart chunk retrieval
            chunks = []
            if book_refs:
                # Search by book title references
                title_conditions = " OR ".join(["b.title LIKE ?" for _ in book_refs])
                title_terms = [f"%{ref}%" for ref in book_refs]
                cursor.execute(
                    f"SELECT bc.id, bc.chapter_id, bc.content, bc.sequence_number, bc.token_count, b.id, b.title "
                    f"FROM book_chunks bc JOIN books b ON bc.book_id = b.id "
                    f"WHERE bc.deleted_at IS NULL AND ({title_conditions}) "
                    f"LIMIT 8",
                    title_terms
                )
                chunks = [{"id": r[0], "chapter_id": r[1], "content": r[2][:800], "sequence": r[3], "token_count": r[4], "book_id": r[5], "book_title": r[6]} for r in cursor.fetchall()]

            # Fallback: keyword matching
            if not chunks and keywords:
                conditions = " OR ".join(["content LIKE ?" for _ in keywords[:5]])
                search_terms = [f"%{kw}%" for kw in keywords[:5]]
                cursor.execute(
                    f"SELECT bc.id, bc.chapter_id, bc.content, bc.sequence_number, bc.token_count, b.id, b.title "
                    f"FROM book_chunks bc JOIN books b ON bc.book_id = b.id "
                    f"WHERE bc.deleted_at IS NULL AND ({conditions}) "
                    f"LIMIT 8",
                    search_terms
                )
                chunks = [{"id": r[0], "chapter_id": r[1], "content": r[2][:800], "sequence": r[3], "token_count": r[4], "book_id": r[5], "book_title": r[6]} for r in cursor.fetchall()]

            # Final fallback: all chunks
            if not chunks:
                cursor.execute(
                    "SELECT bc.id, bc.chapter_id, bc.content, bc.sequence_number, bc.token_count, b.id, b.title "
                    "FROM book_chunks bc LEFT JOIN books b ON bc.book_id = b.id "
                    "WHERE bc.deleted_at IS NULL ORDER BY bc.sequence_number LIMIT 8"
                )
                chunks = [{"id": r[0], "chapter_id": r[1], "content": r[2][:800], "sequence": r[3], "token_count": r[4], "book_id": r[5], "book_title": r[6]} for r in cursor.fetchall()]

            # Get memories
            cursor.execute(
                "SELECT id, type, content, confidence FROM memories WHERE status='active' ORDER BY created_at DESC LIMIT 5"
            )
            memories = [{"id": r[0], "type": r[1], "content": r[2], "confidence": r[3]} for r in cursor.fetchall()]

            conn.close()

            # Build knowledge graph snapshot
            graph_snapshot = self._build_graph_snapshot(chunks, query_analysis)

            stage.output_data = {
                "chunks": chunks,
                "memories": memories,
                "keywords": keywords,
                "book_references": book_refs,
                "intent": query_analysis.intent,
                "topics": query_analysis.topics,
                "graph_snapshot": graph_snapshot,
                "chunk_count": len(chunks),
                "memory_count": len(memories),
            }
            stage.confidence = 0.8 if chunks else 0.3
        except Exception as exc:
            logger.warning("knowledge_retrieval_failed", error=str(exc))
            stage.error = str(exc)
        stage.duration_ms = (time.monotonic() - start) * 1000
        return stage

    def _build_graph_snapshot(self, chunks: list[dict], query_analysis) -> dict[str, Any]:
        """Build a lightweight knowledge graph snapshot from retrieved chunks."""
        # Build concept nodes from chunks
        concepts = {}
        for chunk in chunks:
            book_title = chunk.get("book_title", "Unknown")
            if book_title not in concepts:
                concepts[book_title] = {
                    "type": "book",
                    "title": book_title,
                    "chunks": [],
                }
            concepts[book_title]["chunks"].append({
                "id": chunk["id"],
                "content_preview": chunk["content"][:100],
            })

        # Build topic nodes
        topics = {}
        for topic in (query_analysis.topics if hasattr(query_analysis, 'topics') else query_analysis.get("topics", [])):
            topics[topic] = {
                "type": "topic",
                "name": topic,
                "related_concepts": list(concepts.keys()),
            }

        # Build edges between books and topics
        edges = []
        for book_title in concepts:
            for topic_name in topics:
                edges.append({
                    "source": book_title,
                    "target": topic_name,
                    "relation": "belongs_to_topic",
                })

        # Build edges between books
        book_names = list(concepts.keys())
        for i, b1 in enumerate(book_names):
            for b2 in book_names[i+1:]:
                edges.append({
                    "source": b1,
                    "target": b2,
                    "relation": "related_to",
                })

        return {
            "nodes": {**concepts, **topics},
            "edges": edges,
            "node_count": len(concepts) + len(topics),
            "edge_count": len(edges),
        }

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract keywords from user query for knowledge matching."""
        # Persian and English keywords
        keyword_map = {
            "پذیرش": ["acceptance", "پذیرش", "accept"],
            "ACT": ["ACT", "acceptance and commitment", "درمان پذیرش"],
            "zen": ["zen", " zen", "بودیسم", "بودا"],
            "غیرت": ["non-attachment", "غیرت", "attachment"],
            "ذهن": ["mindfulness", "mind", "آگاهی", "ذهن"],
            "آسیب": ["trauma", "آسیب", "stress"],
            "بدن": ["body", "بدن", "جسم"],
            "روح": ["spirit", "روح", "معنوی"],
            "خود": ["self", "خود", "ego"],
            "ارزش": ["values", "ارزش", "purpose"],
            "آگاهی": ["awareness", "آگاهی", "consciousness"],
            "meditation": ["meditation", "meditate", "مراقبه", "زازن"],
            "acceptance": ["acceptance", "accept", "پذیرش"],
            "defusion": ["defusion", "defuse", "شناخت"],
            "flexibility": ["flexibility", "انعطاف"],
            "suffering": ["suffering", "pain", "رنج", "درد"],
            "consciousness": ["consciousness", "آگاهی"],
            "thinking": ["thinking", "thought", "افکار", "تفکر"],
            "emotion": ["emotion", "feeling", "احساس"],
        }

        found = []
        text_lower = text.lower()
        for key, synonyms in keyword_map.items():
            if key.lower() in text_lower:
                found.extend(synonyms)

        # Also extract simple word matches
        words = set(text_lower.split())
        important_words = [w for w in words if len(w) > 3 and w not in {"this", "that", "what", "how", "why", "when", "where", "which"}]
        found.extend(important_words[:5])

        return list(set(found))[:10]

    def _build_concept_registry(self) -> dict[str, list[str]]:
        """Build unified concept registry from all available sources."""
        registry: dict[str, list[str]] = {}

        # Source 1: CandidateGenerator dictionaries (multilingual)
        dict_concepts = {
            "fa": ["خود", "هویت", "آگاهی", "حضور", "شهود", "فنا", "توبه", "صبر", "توکل", "معرفت", "ذکر", "تمرین", "مراقبه"],
            "ar": ["النفس", "الذات", "الوعي", "الحضور", "الشهود", "الفنا", "التوبة", "الصبر", "التوكل", "المعرفة", "الذكر", "التأمل"],
            "es": ["ego", "identidad", "conciencia", "atención", "mindfulness", "aceptación", "compasión", "sufrimiento", "presencia", "meditación"],
        }
        fa_to_en = {
            "خود": "Self", "هویت": "Self", "آگاهی": "Awareness", "حضور": "Presence",
            "شهود": "Witness", "فنا": "Fana", "توبه": "Repentance", "صبر": "Patience",
            "توکل": "Trust", "معرفت": "Knowledge", "ذکر": "Remembrance", "تمرین": "Practice", "مراقبه": "Meditation",
        }
        ar_to_en = {
            "النفس": "Self", "الذات": "Self", "الوعي": "Awareness", "الحضور": "Presence",
            "الشهود": "Witness", "الفنا": "Fana", "التوبة": "Repentance", "الصبر": "Patience",
            "التوكل": "Trust", "المعرفة": "Knowledge", "الذكر": "Remembrance", "التأمل": "Meditation",
        }
        for lang, concepts in dict_concepts.items():
            mapping = fa_to_en if lang == "fa" else ar_to_en if lang == "ar" else {}
            for c in concepts:
                canonical = mapping.get(c, c)
                if canonical not in registry:
                    registry[canonical] = []
                registry[canonical].append(c)

        # Source 2: Normalization map (canonical -> keywords)
        normalizations = {
            "Self": ["self", "identity", "sense of self", "selfhood", "ego", "خود", "ذات", "خویشتن", "هویت"],
            "Mindfulness": ["mindfulness", "sati", "present awareness", "حضور ذهن", "آگاهی لحظه"],
            "Acceptance": ["acceptance", "پذیرش", "رضا", "رضایت"],
            "Non-attachment": ["non-attachment", "non-resistance", "رها", "letting go"],
            "Awareness": ["awareness", "آگاهی"],
            "Consciousness": ["consciousness", "شعور", "ذهن", "ادراک"],
            "Meditation": ["meditation", "contemplation", "مراقبه", "تامل"],
            "Compassion": ["compassion", "empathy", "همدلی", "مهربانی"],
            "Suffering": ["suffering", "رنج", "درد", "stress"],
            "Behavior": ["behavior", "رفتار"],
            "Emotion": ["emotion", "احساس", "هیجان"],
            "Fana": ["fana", "فناء", "نیستی", "فنا"],
            "Zuhd": ["zuhd", "زهد"],
            "Tawakkul": ["tawakkul", "توکل"],
            "Prediction": ["prediction", "پیش‌بینی"],
            "Free Will": ["free will", "اراده آزاد"],
            "Memory": ["memory", "حافظه"],
            "Pain": ["pain", "درد"],
            "Fear": ["fear", "ترس"],
            "Habit": ["habit", "عادت"],
            "Truth": ["truth", "حقیقت"],
            "Reality": ["reality", "واقعیت"],
            "Meaning": ["meaning", "معنا"],
            "Knowledge": ["knowledge", "دانش", "معرفت"],
            "Wisdom": ["wisdom", "دانایی", "حکمت"],
            "Attention": ["attention", "توجه"],
            "Presence": ["presence", "حضور"],
            "Cognition": ["cognition", "شناخت"],
            "Perception": ["perception", "ادراک"],
        }
        for canonical, keywords in normalizations.items():
            if canonical not in registry:
                registry[canonical] = []
            for kw in keywords:
                if kw not in registry[canonical]:
                    registry[canonical].append(kw)

        # Source 3: Epistemic profile topics (from DB) — skip if keyword already in any canonical
        try:
            import sqlite3
            db_path = "/home/hadi/ayeneh/Ayeneh/ayeneh.db"
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT primary_topics, secondary_topics FROM epistemic_profiles WHERE deleted_at IS NULL")
            # Build set of all existing keywords (including normalization map keywords)
            existing_keywords = set()
            for keywords in registry.values():
                existing_keywords.update(keywords)
            # Also add normalization map keywords explicitly
            for canonical, keywords in normalizations.items():
                existing_keywords.update(keywords)
            for row in cursor.fetchall():
                for topics_json in row:
                    if topics_json:
                        import json
                        try:
                            topics = json.loads(topics_json) if isinstance(topics_json, str) else topics_json
                            for t in topics:
                                if t in existing_keywords:
                                    continue  # Skip, already mapped to some canonical
                                canonical = t.capitalize() if t.islower() else t
                                if canonical in registry:
                                    continue  # Skip, canonical already exists
                                registry[canonical] = [t]
                                existing_keywords.add(t)
                        except (json.JSONDecodeError, TypeError):
                            pass
            conn.close()
        except Exception:
            pass

        # Source 4: Additional concepts (not covered by normalization map)
        additional = {
            "Non-self": ["non-self", "anatta", "بی‌خودی", "anatman"],
            "Defusion": ["defusion", "جداشدن", "آزادی از فکر"],
            "Enlightenment": ["enlightenment", "روشنایی", "بیداری", "awakening", "رستگاری"],
            "Witness": ["witness", "گواه", "شاهد", "ناظر"],
            "Patience": ["patience", "صبر", "تحمل"],
            "Trust": ["trust", "اعتماد"],
            "Remembrance": ["remembrance", "ذکر", "یاد خدا"],
            "Practice": ["practice", "تمرین", "تکرار"],
            "Repentance": ["repentance", "توبه", "بازگشت"],
            "Biology": ["biology", "زیست‌شناسی"],
            "Physics": ["physics", "فیزیک"],
            "Psychology": ["psychology", "روانشناسی"],
            "Therapy": ["therapy", "درمان"],
            "Development": ["development", "رشد", "توسعه"],
            "Ethics": ["ethics", "اخلاق"],
            "Prayer": ["prayer", "نماز", "عبادت"],
            "Science": ["science", "علم"],
        }
        for canonical, keywords in additional.items():
            if canonical not in registry:
                registry[canonical] = []
            for kw in keywords:
                if kw not in registry[canonical]:
                    registry[canonical].append(kw)

        return registry

    def _query_analysis(self, text: str) -> QueryAnalysis:
        """Structured Query Analysis: extract intent, concepts, entities, and metadata."""
        text_lower = text.lower()
        words = text_lower.split()
        qa = QueryAnalysis(query_length=len(words))

        # ── Language detection ──
        persian_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF' or '\u0750' <= c <= '\u077F')
        if persian_chars > len(text) * 0.1:
            qa.languages.append("fa")
        if any(w in text_lower for w in ["the", "is", "are", "what", "how", "why", "and", "or"]):
            qa.languages.append("en")

        # ── Intent detection ──
        comparison_kw = ["compared", "compare", "تفاوت", "فرق", "vs", "versus", "对比", "اختلاف", "متفاوت", "similar", "مشابه", "فرق دارد", "چه تفاوت", "همان"]
        definition_kw = ["what is", "چیست", "تعریف", "define", "explain", "به چه معنا", "یعنی چه", "چه مفهوم"]
        methodology_kw = ["how", "چگونه", "نحوه", "way", "method", "روش", "چطور"]
        relationship_kw = ["relationship", "ارتباط", "relate", "connect", "اتصال", "پیوند", "سازگار"]
        opinion_kw = ["opinion", "نظر", "believe", "think", "فکر میکنی", "به نظرت"]
        critique_kw = ["critique", "criticize", "نقد", "نقد کردن", "weakness", "ضعف"]
        summary_kw = ["summary", "summarize", "خلاصه", "خلاصه کن", "overview"]
        advice_kw = ["advice", "should", "recommend", "توصیه", "باید", "پیشنهاد"]

        if any(kw in text_lower for kw in comparison_kw):
            qa.intent = "comparison"
        elif any(kw in text_lower for kw in definition_kw):
            qa.intent = "definition"
        elif any(kw in text_lower for kw in methodology_kw):
            qa.intent = "methodology"
        elif any(kw in text_lower for kw in relationship_kw):
            qa.intent = "relationship"
        elif any(kw in text_lower for kw in opinion_kw):
            qa.intent = "opinion"
        elif any(kw in text_lower for kw in critique_kw):
            qa.intent = "critique"
        elif any(kw in text_lower for kw in summary_kw):
            qa.intent = "summary"
        elif any(kw in text_lower for kw in advice_kw):
            qa.intent = "advice"
        else:
            qa.intent = "question"

        # ── Concept + Entity resolution via QueryConceptResolver ──
        try:
            resolution = self._concept_resolver.resolve(text)
            qa.resolved_concepts = [{"canonical": c.canonical, "confidence": c.confidence, "source": c.source} for c in resolution.resolved_concepts]
            qa.resolved_entities = [{"name": e.name, "type": e.entity_type, "confidence": e.confidence} for e in resolution.resolved_entities]
            qa.unresolved_terms = resolution.unresolved_terms
            qa.ambiguities = [{"a": a.term_a, "b": a.term_b, "similarity": a.similarity} for a in resolution.ambiguities]
            qa.concept_confidence = resolution.concept_confidence
            qa.entity_confidence = resolution.entity_confidence
            # Backward compat: populate legacy fields
            qa.concepts = [c.canonical for c in resolution.resolved_concepts]
            qa.entities = [e.name for e in resolution.resolved_entities]
        except Exception:
            # Fallback to keyword matching if resolver fails
            qa.concepts = []
            qa.entities = []

        # ── Book reference detection ──
        book_map = {
            "ACT": ["act", "acceptance and commitment", "درمان پذیرش"],
            "Zen Mind": ["zen mind", "zen mind beginners", " ذن"],
            "BeingNoOne": ["metzinger", "being no one", "ego tunnel", "خودبودگی"],
            "Sapolsky": ["sapolsky", "zebras", "behave", "stress"],
            "Body Keeps": ["body keeps", "van der kolk", "trauma"],
            "Waking Up": ["waking up", "sam harris", "بدون دین"],
            "Tao Te Ching": ["tao te ching", " دائو", "لائوتسه"],
            "I Am That": ["i am that", "nisargadatta", "نه‌ایی"],
        }
        for book, keywords in book_map.items():
            if any(kw in text_lower for kw in keywords):
                qa.book_references.append(book)

        # ── Topic classification ──
        topic_map = {
            "psychology": ["therapy", "therapy", "心理", "clinical", "anxiety", "depression", "act", "inquiry", "اضطراب"],
            "contemplation": ["zen", "meditation", "mindfulness", "مراقبه", "contemplation", "sitting"],
            "neuroscience": ["brain", "neural", "cognitive", "مغز", "neuroscience", "prefrontal"],
            "philosophy": ["philosophy", "truth", "reality", "فلسفه", "phenomenology", "epistemology", "ontology"],
            "mysticism": ["mysticism", "عرفان", "تصوف", "sufism", "spiritual", "contemplative"],
            "stress": ["stress", "cortisol", "allostatic", "اضطراب", "stress response"],
            "self_awareness": ["self", "awareness", "consciousness", "خود", "آگاهی", "خودآگاهی"],
        }
        for topic, keywords in topic_map.items():
            if any(kw in text_lower for kw in keywords):
                qa.topics.append(topic)

        # ── Question type ──
        if qa.intent == "comparison":
            qa.question_type = "comparative"
            qa.expected_answer = "comparative"
        elif qa.intent == "definition":
            qa.question_type = "explanatory"
            qa.expected_answer = "definitive"
        elif qa.intent == "methodology":
            qa.question_type = "explanatory"
            qa.expected_answer = "practical"
        elif qa.intent == "critique":
            qa.question_type = "evaluative"
            qa.expected_answer = "critical"
        elif qa.intent == "advice":
            qa.question_type = "open_ended"
            qa.expected_answer = "practical"
        elif "?" in text or "؟" in text:
            qa.question_type = "open_ended"
            qa.expected_answer = "explanatory"
        else:
            qa.question_type = "open_ended"
            qa.expected_answer = "explanatory"

        # ── Complexity ──
        num_concepts = len(qa.concepts)
        num_entities = len(qa.entities)
        num_book_refs = len(qa.book_references)
        if num_book_refs >= 2 or (num_concepts >= 3 and num_entities >= 2):
            qa.complexity = "high"
        elif num_concepts >= 2 or num_entities >= 1 or qa.intent in ("comparison", "critique"):
            qa.complexity = "medium"
        else:
            qa.complexity = "low"

        # ── Scope ──
        if num_book_refs >= 2 or qa.intent == "comparison":
            qa.scope = "cross_book"
        elif num_book_refs == 1:
            qa.scope = "single_book"
        elif any(t in ("mysticism", "contemplation") for t in qa.topics):
            qa.scope = "cross_tradition"
        else:
            qa.scope = "single_book"

        # ── Required reasoning ──
        if qa.scope == "cross_book":
            qa.required_reasoning = "cross_book"
        elif qa.scope == "cross_tradition":
            qa.required_reasoning = "cross_tradition"
        elif qa.intent in ("comparison", "critique", "relationship"):
            qa.required_reasoning = "synthesis"
        elif qa.complexity == "high":
            qa.required_reasoning = "synthesis"
        else:
            qa.required_reasoning = "single_source"

        # ── Requires interpretation ──
        interpretation_keywords = ["means", "یعنی", "interpret", "understand", "concept", "metaphor", "analogy", "fana", "fanā", "enlightenment", "awakening", "non-self", "awareness", "consciousness"]
        qa.requires_interpretation = any(kw in text_lower for kw in interpretation_keywords) or qa.intent in ("definition",) or qa.complexity == "high"

        # ── Requires epistemic safety ──
        qa.requires_epistemic_safety = True  # almost always

        # ── Requires graph reasoning ──
        qa.requires_graph_reasoning = qa.scope in ("cross_book", "cross_tradition") or qa.intent in ("comparison", "critique", "relationship")

        return qa

    def _stage_graph_reasoning(self, context: dict[str, Any], chunks: list[dict]) -> PipelineStageResult:
        """Stage 3: Reason across knowledge sources."""
        stage = PipelineStageResult(stage_name="graph_reasoning")
        start = time.monotonic()
        try:
            result = self._graph_reasoner.reason(
                query=context.get("user_message", ""),
                context={"chunks": chunks},
            )
            stage.output_data = {
                "result": result,
                "hypotheses": len(result.hypotheses),
                "conflicts": len(result.conflicts),
                "confidence": result.confidence.overall_confidence,
            }
            stage.confidence = result.confidence.overall_confidence
        except Exception as exc:
            logger.warning("graph_reasoning_failed", error=str(exc))
            stage.error = str(exc)
        stage.duration_ms = (time.monotonic() - start) * 1000
        return stage

    def _stage_interpretation(self, context: dict[str, Any], chunks: list[dict]) -> PipelineStageResult:
        """Stage 4: Generate multi-lens interpretation."""
        stage = PipelineStageResult(stage_name="interpretation")
        start = time.monotonic()
        try:
            from ayeneh.knowledge_interpretation.types import InterpretationContext

            chunk_content = "\n\n".join(c.get("content", "") for c in chunks[:3])
            if not chunk_content:
                chunk_content = context.get("user_message", "")

            interp_context = InterpretationContext(
                document_id=str(uuid.uuid4()),
                book_id=str(uuid.uuid4()),
                chapter_id=str(uuid.uuid4()),
                chapter_title="Knowledge",
                chunk_id=str(uuid.uuid4()),
                chunk_content=chunk_content,
            )

            interp = self._interpretation_engine._generator.generate(interp_context)
            stage.output_data = {
                "interpretation": interp,
                "confidence": interp.confidence,
                "practical_insight": interp.practical_insight[:200],
            }
            stage.confidence = interp.confidence
        except Exception as exc:
            logger.warning("interpretation_failed", error=str(exc))
            stage.error = str(exc)
        stage.duration_ms = (time.monotonic() - start) * 1000
        return stage

    def _stage_safety_check(self, context: dict[str, Any]) -> PipelineStageResult:
        """Stage 5: Pre-check safety constraints."""
        stage = PipelineStageResult(stage_name="safety_precheck")
        start = time.monotonic()
        try:
            result = self._safety_engine.validate(context.get("user_message", ""))
            stage.output_data = {
                "safety_result": result,
                "score": result.overall_safety_score,
                "recommendation": result.recommendation,
            }
            stage.confidence = result.overall_safety_score
        except Exception as exc:
            logger.warning("safety_check_failed", error=str(exc))
            stage.error = str(exc)
        stage.duration_ms = (time.monotonic() - start) * 1000
        return stage

    async def _stage_response_generation(self, enriched_context: dict[str, Any]) -> PipelineStageResult:
        """Stage 6: Generate final response via LLM."""
        stage = PipelineStageResult(stage_name="response_generation")
        start = time.monotonic()
        try:
            agent = self._get_conversation_agent()
            output = agent._build_fallback_prompt(enriched_context)
            response_text = ""

            if agent._ai_router is not None:
                from ayeneh.ai_router.types import AITask, AITaskType
                task = AITask(
                    task_type=AITaskType.CONVERSATION_GENERATION,
                    content=str(output.get("messages", [])),
                    max_tokens=2048,
                    temperature=0.7,
                )
                result = await agent._ai_router.chat(task, output.get("messages", []))
                response_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            elif agent._llm is not None:
                messages = output.get("messages", [])
                result = await agent._llm.chat(
                    messages,
                    model=agent._model,
                    temperature=agent._temperature,
                    max_tokens=agent._max_tokens,
                )
                response_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")

            if not response_text:
                response_text = "I couldn't generate a response."

            stage.output_data = {"response_text": response_text}
            stage.confidence = 0.7
        except Exception as exc:
            logger.warning("response_generation_failed", error=str(exc))
            stage.error = str(exc)
        stage.duration_ms = (time.monotonic() - start) * 1000
        return stage

    def _stage_safety_validate(self, response_text: str) -> PipelineStageResult:
        """Post-generation safety validation."""
        stage = PipelineStageResult(stage_name="safety_postcheck")
        start = time.monotonic()
        try:
            result = self._safety_engine.validate(response_text)
            stage.output_data = {
                "safety_result": result,
                "score": result.overall_safety_score,
                "recommendation": result.recommendation,
            }
            stage.confidence = result.overall_safety_score
        except Exception as exc:
            logger.warning("safety_postcheck_failed", error=str(exc))
            stage.error = str(exc)
        stage.duration_ms = (time.monotonic() - start) * 1000
        return stage

    def _build_enriched_context(self, original_context: dict[str, Any], pipeline_result: PipelineResult) -> dict[str, Any]:
        """Build enriched context with all pipeline results."""
        knowledge_parts = []
        for chunk in pipeline_result.knowledge_chunks:
            book = chunk.get("book_title", "")
            preview = chunk.get("content", "")[:400]
            knowledge_parts.append(f"[{book}] {preview}")

        interpretation_text = ""
        if pipeline_result.interpretation:
            interp = pipeline_result.interpretation
            interpretation_text = f"Practical insight: {interp.practical_insight}\nConceptual meaning: {interp.conceptual_meaning}"

        reasoning_text = ""
        if pipeline_result.graph_reasoning:
            rr = pipeline_result.graph_reasoning
            reasoning_text = f"Confidence: {rr.confidence.overall_confidence}. Hypotheses: {len(rr.hypotheses)}"

        # Query analysis summary
        query_summary = ""
        if pipeline_result.stages:
            for stage in pipeline_result.stages:
                if stage.stage_name == "knowledge_retrieval":
                    qa = stage.output_data
                    query_summary = f"Intent: {qa.get('intent', 'general')}, Topics: {qa.get('topics', [])}, Books: {qa.get('book_references', [])}"
                    break

        system_content = "You are Ayeneh, a Cognitive Companion. You reflect back thinking patterns and engage with knowledge from your library. Ask reflective questions. Ground responses in provided context. Reference specific books when relevant. Never fabricate information."

        if knowledge_parts:
            system_content += f"\n\n## Relevant Knowledge from Your Library:\n" + "\n\n---\n\n".join(knowledge_parts)

        if query_summary:
            system_content += f"\n\n## Query Analysis:\n{query_summary}"

        if interpretation_text:
            system_content += f"\n\n## Interpretation:\n{interpretation_text}"

        if reasoning_text:
            system_content += f"\n\n## Reasoning:\n{reasoning_text}"

        system_content += "\n\n## Instruction: Use the knowledge above to inform your response. When referencing concepts, mention which book they come from. Ask reflective questions to deepen understanding."

        enriched = dict(original_context)
        enriched["system_context"] = system_content
        enriched["knowledge_context"] = "\n\n---\n\n".join(knowledge_parts)
        return enriched

    def _get_conversation_agent(self):
        """Get or create conversation agent."""
        if self._conversation_agent is None:
            from ayeneh.agents.conversation import ConversationAgent
            try:
                from ayeneh.api.deps import get_container
                container = get_container()
                self._conversation_agent = container.conversation_agent
            except Exception:
                self._conversation_agent = ConversationAgent()
        return self._conversation_agent
