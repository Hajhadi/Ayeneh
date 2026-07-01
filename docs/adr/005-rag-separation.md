# RAG as an Independent Layer

## Status

Accepted

## Context

Retrieval-Augmented Generation is central to Ayeneh — every response should be grounded in relevant context from memory and knowledge. If RAG logic is embedded inside agents, each agent duplicates retrieval logic and the retrieval strategy becomes coupled to agent behavior. Changes to chunking, embedding, or retrieval strategy would require modifying every agent.

## Decision

Separate RAG into an independent layer exposed through the KnowledgeService. The RAG layer owns:

- Text chunking strategies for knowledge sources.
- Embedding generation and vector storage.
- Query construction, similarity search, and result ranking.
- Citation tracking and source attribution.

Agents and the API call the RAG layer through a uniform interface: provide a query and a scope (memory type, knowledge base, or both), receive ranked results with citations. The RAG layer does not know about agents, prompts, or conversation flow — it only retrieves and ranks content.

## Consequences

### Positive
- Retrieval strategy can be improved independently of agent logic.
- All consumers benefit from the same retrieval improvements.
- RAG can be tested in isolation with known document collections.
- Adding a new knowledge source type requires changes only in the RAG layer.

### Negative
- RAG becomes a single point of quality — if retrieval is poor, all downstream consumers are affected.
- The RAG interface must be stable and generic enough to serve all consumers.
- Cross-memory-type queries (e.g., search both episodic and knowledge) require coordination at the caller level.

## Alternatives Considered

- **RAG embedded in each agent**: Rejected — leads to code duplication, inconsistent retrieval behavior, and coupling between retrieval strategy and agent logic.
- **RAG as an agent**: Rejected — RAG is an infrastructure capability, not a cognitive unit; modeling it as an agent would conflate retrieval with reasoning.
- **External RAG service (microservice)**: Rejected — adds network overhead and deployment complexity that is not justified at the current scale; may be revisited if performance requirements demand it.
