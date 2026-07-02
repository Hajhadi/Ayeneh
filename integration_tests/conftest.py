"""Shared test fixtures, test doubles, and seeded data for integration tests."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any

import pytest


# ---------------------------------------------------------------------------
# Fake LLM Gateway
# ---------------------------------------------------------------------------


class FakeLLMGateway:
    """Deterministic LLM for testing — returns structured responses."""

    def __init__(self, response_text: str = "") -> None:
        self._response = response_text or (
            '{"response": "I notice you are exploring a deep question. '
            "What patterns do you observe in your own thinking about this? "
            'This might connect to themes explored across multiple traditions.", '
            '"observations": [{"type": "reflective", "content": "User is exploring cross-tradition concepts", '
            '"confidence": 0.7}], "tone": "curious", "confidence": 0.65}'
        )
        self.call_count = 0
        self.last_messages: list[dict[str, str]] = []

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
    ) -> dict[str, Any]:
        self.call_count += 1
        self.last_messages = messages
        return {
            "choices": [{"message": {"content": self._response}}],
            "usage": {
                "prompt_tokens": 150,
                "completion_tokens": 80,
                "total_tokens": 230,
            },
        }

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        *,
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ):
        chunks = [
            '{"response": "I notice',
            ' you are exploring',
            " a deep question.",
            ' What patterns do you observe?"}',
        ]
        for chunk in chunks:
            yield {"choices": [{"delta": {"content": chunk}}]}


# ---------------------------------------------------------------------------
# Fake Vector Store
# ---------------------------------------------------------------------------


@dataclass
class FakeVectorRecord:
    id: str = ""
    entity_id: str = ""
    entity_type: str = ""
    embedding: list[float] = field(default_factory=list)


@dataclass
class FakeSearchResult:
    record: FakeVectorRecord
    score: float = 0.0


class FakeVectorStore:
    """In-memory vector store for testing."""

    def __init__(self) -> None:
        self.records: dict[str, FakeVectorRecord] = {}
        self.search_calls = 0

    async def search_by_embedding(
        self,
        query_embedding: list[float],
        *,
        user_id: str = "",
        entity_type: str = "book_chunk",
        limit: int = 20,
        score_threshold: float = 0.0,
    ) -> list[FakeSearchResult]:
        self.search_calls += 1
        results = []
        for rec in self.records.values():
            if rec.entity_type == entity_type:
                results.append(FakeSearchResult(record=rec, score=0.75))
        return results[:limit]

    async def keyword_search(
        self, query: str, *, user_id: str = "", limit: int = 20
    ) -> list[FakeSearchResult]:
        self.search_calls += 1
        results = []
        for rec in self.records.values():
            results.append(FakeSearchResult(record=rec, score=0.6))
        return results[:limit]

    async def upsert(self, record: FakeVectorRecord) -> None:
        self.records[record.id] = record

    async def delete(self, record_id: str) -> None:
        self.records.pop(record_id, None)


# ---------------------------------------------------------------------------
# Fake Book Repository
# ---------------------------------------------------------------------------


class FakeBookRepository:
    """In-memory book/chapter/chunk storage."""

    def __init__(self) -> None:
        self.books: dict[str, dict[str, Any]] = {}
        self.chapters: dict[str, list[dict[str, Any]]] = {}
        self.chunks: dict[str, list[dict[str, Any]]] = {}

    async def get_by_id(self, book_id: str) -> dict | None:
        return self.books.get(book_id)

    async def get_by_user(self, user_id: str) -> list[dict]:
        return [b for b in self.books.values() if b.get("user_id") == user_id]

    async def update_status(self, book_id: str, status: str, **kwargs: Any) -> None:
        if book_id in self.books:
            self.books[book_id]["status"] = status
            self.books[book_id].update(kwargs)

    async def create_chapter(
        self, book_id: str, title: str, sequence: int, **kwargs: Any
    ) -> dict:
        ch = {"id": str(uuid.uuid4()), "title": title, "sequence_number": sequence, **kwargs}
        self.chapters.setdefault(book_id, []).append(ch)
        return ch

    async def create_chunk(
        self,
        book_id: str,
        chapter_id: str,
        content: str,
        sequence: int,
        token_count: int,
        **kwargs: Any,
    ) -> dict:
        ck = {
            "id": str(uuid.uuid4()),
            "chapter_id": chapter_id,
            "content": content,
            "sequence_number": sequence,
            "token_count": token_count,
            **kwargs,
        }
        self.chunks.setdefault(book_id, []).append(ck)
        return ck

    async def get_chunks_by_book(self, book_id: str) -> list[dict]:
        return self.chunks.get(book_id, [])

    async def get_chunks_by_ids(self, chunk_ids: list[str]) -> list[dict]:
        all_chunks = []
        for chunks in self.chunks.values():
            all_chunks.extend(chunks)
        return [c for c in all_chunks if c["id"] in chunk_ids]

    async def count_chunks(self, book_id: str) -> int:
        return len(self.chunks.get(book_id, []))


# ---------------------------------------------------------------------------
# Fake Event Bus
# ---------------------------------------------------------------------------


class FakeEventBus:
    """Captures published events for verification."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        self.events.append({"type": event_type, **payload})

    def get_events(self, event_type: str) -> list[dict[str, Any]]:
        return [e for e in self.events if e.get("type") == event_type]


# ---------------------------------------------------------------------------
# Fake Embedding Gateway
# ---------------------------------------------------------------------------


class FakeEmbeddingGateway:
    """Returns deterministic embeddings."""

    def __init__(self, dimensions: int = 128) -> None:
        self.dimensions = dimensions
        self.embed_calls = 0

    async def embed(self, text: str) -> list[float]:
        self.embed_calls += 1
        return [0.1] * self.dimensions

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self.embed_calls += 1
        return [[0.1] * self.dimensions for _ in texts]

    async def upsert(self, entity_id: str, entity_type: str, text: str) -> None:
        pass

    async def delete_by_entity(self, entity_id: str, entity_type: str) -> None:
        pass


# ---------------------------------------------------------------------------
# In-Memory Knowledge Graph
# ---------------------------------------------------------------------------


class InMemoryKnowledgeGraph:
    """Dict-backed knowledge graph for testing."""

    def __init__(self) -> None:
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: dict[str, dict[str, Any]] = {}
        self.version: int = 0

    def add_node(self, node_id: str, node_type: str, title: str, **kwargs: Any) -> None:
        self.nodes[node_id] = {"id": node_id, "node_type": node_type, "title": title, **kwargs}

    def add_edge(
        self,
        edge_id: str,
        source_id: str,
        target_id: str,
        relation_type: str,
        **kwargs: Any,
    ) -> None:
        self.edges[edge_id] = {
            "id": edge_id,
            "source_id": source_id,
            "target_id": target_id,
            "relation_type": relation_type,
            **kwargs,
        }

    def find_concept(self, concept: str) -> list[Any]:
        results = []
        for node in self.nodes.values():
            if concept.lower() in node.get("title", "").lower():
                results.append(type("Node", (), node)())
        return results

    def find_topic(self, topic: str) -> list[Any]:
        return self.find_concept(topic)

    def get_edges_from_node(self, node_id: str) -> list[Any]:
        results = []
        for edge in self.edges.values():
            if edge["source_id"] == node_id or edge["target_id"] == node_id:
                results.append(type("Edge", (), edge)())
        return results

    def find_all_paths(self, start: str, end: str, max_depth: int = 5) -> list[list[str]]:
        paths: list[list[str]] = []

        def dfs(current: str, path: list[str], depth: int) -> None:
            if depth > max_depth:
                return
            if current == end:
                paths.append(list(path))
                return
            for edge in self.edges.values():
                next_node = None
                if edge["source_id"] == current:
                    next_node = edge["target_id"]
                elif edge["target_id"] == current:
                    next_node = edge["source_id"]
                if next_node and next_node not in path:
                    path.append(next_node)
                    dfs(next_node, path, depth + 1)
                    path.pop()

        dfs(start, [start], 0)
        return paths

    def increment_version(self) -> int:
        self.version += 1
        return self.version

    def get_all_concepts(self) -> list[str]:
        return [
            n["title"]
            for n in self.nodes.values()
            if n.get("node_type") == "concept"
        ]


# ---------------------------------------------------------------------------
# In-Memory Provenance Store
# ---------------------------------------------------------------------------


class InMemoryProvenanceStore:
    """Stores provenance bundles for verification."""

    def __init__(self) -> None:
        self.bundles: dict[str, Any] = {}

    def save(self, bundle: Any) -> None:
        self.bundles[bundle.id] = bundle

    def get(self, bundle_id: str) -> Any | None:
        return self.bundles.get(bundle_id)

    def get_all(self) -> list[Any]:
        return list(self.bundles.values())


# ---------------------------------------------------------------------------
# Seeded Data Factory
# ---------------------------------------------------------------------------


def create_seeded_books(book_repo: FakeBookRepository) -> dict[str, str]:
    """Create 3 seeded books covering different traditions. Returns book_ids."""
    books = {
        "act": {
            "title": "ACT and Psychological Flexibility",
            "author": "Steven Hayes",
            "tradition": "Clinical Psychology",
            "framework": "ACT",
            "chapters": [
                {
                    "title": "Acceptance and Defusion",
                    "content": (
                        "Acceptance in ACT involves making room for difficult experiences "
                        "without trying to change them. Cognitive defusion creates distance "
                        "from thoughts, observing them as mental events rather than facts. "
                        "This process of psychological flexibility allows individuals to "
                        "pursue values-based action even in the presence of discomfort."
                    ),
                },
                {
                    "title": "Values and Committed Action",
                    "content": (
                        "Values in ACT represent what matters most to an individual — "
                        "chosen life directions rather than goals. Committed action "
                        "involves taking concrete steps aligned with these values. "
                        "The interplay between acceptance, defusion, and values "
                        "forms the core of psychological flexibility."
                    ),
                },
            ],
        },
        "zen": {
            "title": "Zen Mind, Beginner's Mind",
            "author": "Shunryu Suzuki",
            "tradition": "Zen Buddhism",
            "framework": "Zen",
            "chapters": [
                {
                    "title": "Beginner's Mind",
                    "content": (
                        "In the beginner's mind there are many possibilities, but in the "
                        "expert's mind there are few. Zen practice emphasizes direct "
                        "experience beyond conceptual thought. Sitting in zazen, we "
                        "practice present-moment awareness without attachment to outcomes."
                    ),
                },
                {
                    "title": "Non-Attachment",
                    "content": (
                        "Non-attachment in Zen does not mean indifference. Rather, it "
                        "involves holding experience lightly — being fully present without "
                        "clinging to pleasant states or resisting unpleasant ones. This "
                        "mirrors the middle way between indulgence and asceticism."
                    ),
                },
            ],
        },
        "neuroscience": {
            "title": "Behavioral Neuroscience of Stress",
            "author": "Robert Sapolsky",
            "tradition": "Neuroscience",
            "framework": "neuroscience",
            "chapters": [
                {
                    "title": "The Stress Response",
                    "content": (
                        "The stress response involves the hypothalamic-pituitary-adrenal "
                        "axis. Cortisol and adrenaline prepare the body for action. "
                        "Chronic stress damages the hippocampus and prefrontal cortex "
                        "while strengthening the amygdala, creating a bias toward "
                        "threat detection and rumination."
                    ),
                },
                {
                    "title": "Cognitive Appraisal",
                    "content": (
                        "Cognitive appraisal determines whether a situation is perceived "
                        "as stressful. The prefrontal cortex can regulate the amygdala's "
                        "threat response through reappraisal. This top-down regulation "
                        "is similar to what contemplative practices cultivate through "
                        "mindfulness meditation."
                    ),
                },
            ],
        },
    }

    book_ids: dict[str, str] = {}
    for key, book_data in books.items():
        book_id = str(uuid.uuid4())
        book_ids[key] = book_id
        book_repo.books[book_id] = {
            "id": book_id,
            "title": book_data["title"],
            "author": book_data["author"],
            "status": "ready",
            "tradition": book_data["tradition"],
            "framework": book_data["framework"],
        }
        for ch_data in book_data["chapters"]:
            ch_id = str(uuid.uuid4())
            book_repo.chapters.setdefault(book_id, []).append(
                {"id": ch_id, "title": ch_data["title"], "sequence_number": len(book_repo.chapters.get(book_id, []))}
            )
            book_repo.chunks.setdefault(book_id, []).append(
                {
                    "id": str(uuid.uuid4()),
                    "chapter_id": ch_id,
                    "content": ch_data["content"],
                    "sequence_number": len(book_repo.chunks.get(book_id, [])),
                    "token_count": len(ch_data["content"].split()),
                }
            )

    return book_ids


def create_seeded_graph(graph: InMemoryKnowledgeGraph, book_ids: dict[str, str]) -> None:
    """Populate the knowledge graph with concepts, edges, and cross-book links."""
    concepts = {
        "acceptance": {"title": "Acceptance", "domain": "psychology"},
        "defusion": {"title": "Cognitive Defusion", "domain": "psychology"},
        "mindfulness": {"title": "Mindfulness", "domain": "contemplative"},
        "non_attachment": {"title": "Non-Attachment", "domain": "contemplative"},
        "self": {"title": "Self / No-Self", "domain": "philosophy"},
        "awareness": {"title": "Awareness", "domain": "neuroscience"},
        "stress_response": {"title": "Stress Response", "domain": "neuroscience"},
        "prefrontal_cortex": {"title": "Prefrontal Cortex", "domain": "neuroscience"},
        "values": {"title": "Values", "domain": "psychology"},
        "present_moment": {"title": "Present Moment Awareness", "domain": "contemplative"},
        "suffering": {"title": "Suffering / Dukkha", "domain": "contemplative"},
        "compassion": {"title": "Compassion", "domain": "contemplative"},
    }

    concept_ids: dict[str, str] = {}
    for name, data in concepts.items():
        cid = str(uuid.uuid4())
        concept_ids[name] = cid
        graph.add_node(cid, "concept", data["title"], domain=data["domain"])

    # Add book nodes
    for tradition, bid in book_ids.items():
        graph.add_node(bid, "book", f"Book:{tradition}")

    # Add intra-book edges
    intra_edges = [
        ("acceptance", "defusion", "supports"),
        ("defusion", "mindfulness", "extends"),
        ("mindfulness", "non_attachment", "related_to"),
        ("non_attachment", "self", "related_to"),
        ("awareness", "prefrontal_cortex", "related_to"),
        ("stress_response", "prefrontal_cortex", "related_to"),
        ("values", "acceptance", "supports"),
        ("present_moment", "mindfulness", "shares_concept"),
        ("suffering", "non_attachment", "related_to"),
        ("compassion", "mindfulness", "extends"),
    ]

    for src, tgt, rel in intra_edges:
        graph.add_edge(str(uuid.uuid4()), concept_ids[src], concept_ids[tgt], rel)

    # Add cross-book edges
    cross_edges = [
        ("acceptance", "non_attachment", "shares_concept"),
        ("mindfulness", "present_moment", "shares_concept"),
        ("defusion", "non_attachment", "partially_overlaps"),
        ("awareness", "mindfulness", "shares_concept"),
        ("suffering", "stress_response", "different_scope"),
    ]

    for src, tgt, rel in cross_edges:
        graph.add_edge(
            str(uuid.uuid4()), concept_ids[src], concept_ids[tgt], rel,
            cross_book=True,
        )

    graph.version = 3


# ---------------------------------------------------------------------------
# Pytest Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_llm() -> FakeLLMGateway:
    return FakeLLMGateway()


@pytest.fixture
def fake_vector_store() -> FakeVectorStore:
    return FakeVectorStore()


@pytest.fixture
def fake_book_repo() -> FakeBookRepository:
    return FakeBookRepository()


@pytest.fixture
def fake_event_bus() -> FakeEventBus:
    return FakeEventBus()


@pytest.fixture
def fake_embedding() -> FakeEmbeddingGateway:
    return FakeEmbeddingGateway()


@pytest.fixture
def knowledge_graph() -> InMemoryKnowledgeGraph:
    return InMemoryKnowledgeGraph()


@pytest.fixture
def provenance_store() -> InMemoryProvenanceStore:
    return InMemoryProvenanceStore()


@pytest.fixture
def seeded_book_repo() -> tuple[FakeBookRepository, dict[str, str]]:
    repo = FakeBookRepository()
    book_ids = create_seeded_books(repo)
    return repo, book_ids


@pytest.fixture
def seeded_graph() -> tuple[InMemoryKnowledgeGraph, dict[str, str]]:
    graph = InMemoryKnowledgeGraph()
    book_ids = {
        "act": str(uuid.uuid4()),
        "zen": str(uuid.uuid4()),
        "neuroscience": str(uuid.uuid4()),
    }
    create_seeded_graph(graph, book_ids)
    return graph, book_ids


@pytest.fixture
def pipeline_components(
    fake_llm: FakeLLMGateway,
    fake_vector_store: FakeVectorStore,
    seeded_book_repo: tuple[FakeBookRepository, dict[str, str]],
    fake_event_bus: FakeEventBus,
    fake_embedding: FakeEmbeddingGateway,
    seeded_graph: tuple[InMemoryKnowledgeGraph, dict[str, str]],
    provenance_store: InMemoryProvenanceStore,
) -> dict[str, Any]:
    """All components wired together for pipeline testing."""
    book_repo, book_ids = seeded_book_repo
    graph, graph_book_ids = seeded_graph

    return {
        "llm": fake_llm,
        "vector_store": fake_vector_store,
        "book_repo": book_repo,
        "book_ids": book_ids,
        "event_bus": fake_event_bus,
        "embedding": fake_embedding,
        "graph": graph,
        "graph_book_ids": graph_book_ids,
        "provenance_store": provenance_store,
    }
