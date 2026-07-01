# Four-Type Memory Architecture

## Status

Accepted

## Context

A cognitive companion must remember what happened (episodic), what was learned (semantic), what patterns repeat (pattern), and what insights were derived (reflection). Storing all of this in a single unstructured store makes retrieval imprecise and prevents the system from distinguishing between raw events, extracted facts, observed tendencies, and synthesized insights.

## Decision

Model memory as four distinct types, each with a dedicated schema and retrieval strategy:

- **Episodic Memory**: Raw timestamped records of user interactions and events. Retrieved primarily by time range and recency.
- **Semantic Memory**: Extracted facts, preferences, beliefs, and relationships. Retrieved by semantic similarity and entity matching.
- **Pattern Memory**: Detected recurring behaviors, emotional tendencies, and cognitive patterns. Retrieved by relevance to current context and user state.
- **Reflection Memory**: Periodic synthesized observations that reference underlying memories. Retrieved by time period or thematic relevance.

All four types are stored in both a relational database (for structured queries, filtering, and joins) and a vector database (for semantic similarity search). The memory service provides type-specific retrieval methods while hiding storage details from consumers.

## Consequences

### Positive
- Clear separation of concerns — each memory type serves a distinct retrieval purpose.
- Retrieval precision improves because queries target the right memory type.
- Reflections and patterns remain distinguishable from raw data.
- New memory types can be added by following the established pattern.

### Negative
- Four storage schemas must be maintained and kept in sync.
- Dual storage (relational + vector) increases write complexity and data consistency overhead.
- Consumers must understand the type system to query effectively.

## Alternatives Considered

- **Single unified memory store with type tags**: Rejected — leads to inefficient queries and blurs the distinction between fundamentally different kinds of memory; retrieval logic becomes increasingly complex as the system grows.
- **Only episodic memory (raw log)**: Rejected — without semantic extraction, pattern detection, and reflection synthesis, the system cannot offer meaningful cognitive insights.
- **Only vector store (no relational)**: Rejected — vectors excel at semantic search but cannot efficiently support the structured queries (time ranges, entity filters, aggregations) that memory management requires.
