# Service Layer Abstraction

## Status

Accepted

## Context

Agents in Ayeneh need to interact with external systems — databases, vector stores, LLM providers, and file storage. If agents directly depend on these systems, every data source change ripples through all agent implementations. The system also needs to support testing without real infrastructure and allow replacing underlying implementations without modifying agent logic.

## Decision

Introduce a service layer that sits between agents and infrastructure. Each external capability (memory storage, knowledge retrieval, LLM interaction, embedding generation) is defined as a service interface. Agents depend only on these interfaces. Concrete implementations are injected at composition root.

Services are organized by domain:
- MemoryService — read/write for all memory types
- KnowledgeService — book ingestion, chunking, retrieval
- LLMService — prompt execution via LiteLLM
- EmbeddingService — text-to-vector conversion
- PatternService — pattern detection and lookup

## Consequences

### Positive
- Agents remain agnostic to infrastructure details.
- Each service can be tested independently with mock implementations.
- Replacing a database, vector store, or LLM provider requires changes only in the service implementation, not in agents.
- Clear ownership boundaries between domain logic and infrastructure.

### Negative
- Increased number of interfaces and indirection.
- Service definitions must be stable; frequent changes break all consumers.
- Requires dependency injection setup at application entry points.

## Alternatives Considered

- **Direct agent-to-infrastructure coupling**: Rejected — creates tight coupling, makes testing difficult, and violates the Single Responsibility Principle.
- **Repository pattern only**: Rejected — repositories handle data access but not cross-cutting concerns like LLM calls or embedding generation; a broader service layer is needed.
- **Event-driven bus between agents and infrastructure**: Rejected — adds unnecessary complexity for the current scale; may be revisited if cross-service eventing becomes a requirement.
