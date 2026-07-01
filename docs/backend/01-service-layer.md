# Backend Service Layer — Ayeneh

---

## 1. Service Layer Principles

- **Single responsibility**: Each service owns one domain capability. No service crosses bounded context boundaries.
- **Interface-driven**: Services expose typed contracts (inputs/outputs). Implementation is hidden behind these contracts.
- **No cross-service calls**: Services never call each other directly. Orchestration happens in the Application Layer or Runtime Coordinator.
- **Domain logic in services**: Business rules live in services, not in agents or API handlers. Agents orchestrate service calls; services enforce rules.
- **Stateless**: Services hold no per-request state. All state lives in the data layer or is passed as input.
- **Observable**: Every service call is traceable via structured logging and metrics.
- **Fail-safe**: Services never throw unhandled exceptions. Errors are typed and propagated to the caller.

---

## 2. Service Catalog

### ConversationService

| Aspect | Detail |
|---|---|
| **Responsibility** | Manages the lifecycle of Conversations and Messages. Creates, closes, retrieves, and summarizes conversations. Enforces message immutability. |
| **Inputs** | User ID, conversation ID, message content, conversation status filters. |
| **Outputs** | Conversation object, message list, conversation summary. |
| **Dependencies** | Data layer (conversations, messages tables). |
| **Owned Rules** | Messages are immutable after creation. Conversations close after configurable inactivity. Sequence numbers are monotonically increasing per conversation. |

### MemoryService

| Aspect | Detail |
|---|---|
| **Responsibility** | Creates, retrieves, updates, consolidates, and archives Memories. Manages the four memory types (episodic, semantic, pattern, reflection). Enforces supersession logic. |
| **Inputs** | User ID, memory content, type, confidence, source message IDs, filters (type, status, time range). |
| **Outputs** | Memory objects, retrieval results ranked by relevance. |
| **Dependencies** | Data layer (memories table), EmbeddingService (for vector operations). |
| **Owned Rules** | Memory type must be valid. Confidence between 0 and 1. Superseded memories transition to `superseded` status. Corrections create new memories, never modify existing. Temporal consistency enforced. |

### InsightService

| Aspect | Detail |
|---|---|
| **Responsibility** | Extracts, stores, and retrieves Insights from Messages. Manages insight lifecycle. |
| **Inputs** | User ID, messages (for extraction), insight type filters, confidence thresholds. |
| **Outputs** | Insight objects, extraction results. |
| **Dependencies** | Data layer (insights table), LLM Orchestration Service (for extraction). |
| **Owned Rules** | Insight type must be valid. Confidence between 0 and 1. Every insight traces back to at least one source message. |

### PatternService

| Aspect | Detail |
|---|---|
| **Responsibility** | Detects, creates, updates, and deprecates Patterns. Manages evidence linkage and pattern-to-pattern relationships. |
| **Inputs** | User ID, memories, insights, time window, pattern filters. |
| **Outputs** | Pattern objects, evidence linkage results, deprecation records. |
| **Dependencies** | Data layer (patterns, pattern_evidence, pattern_relations tables), LLM Orchestration Service (for detection). |
| **Owned Rules** | Pattern requires evidence from at least two distinct time periods. Strength between 0 and 1. Contradictory evidence weakens or deprecates patterns. Evidence count ≥ 0. |

### ReflectionService

| Aspect | Detail |
|---|---|
| **Responsibility** | Generates, stores, and retrieves Reflections. Assembles evidence from memories, insights, and patterns within a time range. |
| **Inputs** | User ID, time period, evidence set, reflection filters. |
| **Outputs** | Reflection objects, evidence snapshot. |
| **Dependencies** | Data layer (reflections table), MemoryService (for evidence collection), PatternService (for pattern evidence), LLM Orchestration Service (for synthesis). |
| **Owned Rules** | Period end > period start. Reflection references evidence but never owns it. Deleting a reflection does not affect referenced evidence. |

### LibraryService

| Aspect | Detail |
|---|---|
| **Responsibility** | Manages Books, BookChapters, and BookChunks. Handles import, ingestion status tracking, deletion, and retrieval of book metadata. |
| **Inputs** | User ID, book file/URL, book metadata, book ID, filters. |
| **Outputs** | Book objects, chapter lists, chunk lists, ingestion status. |
| **Dependencies** | Data layer (books, book_chapters, book_chunks tables). |
| **Owned Rules** | Book status transitions: processing → ready | failed. Chunks are immutable after creation. Deleting a book cascades to chapters and chunks. |

### RetrievalService

| Aspect | Detail |
|---|---|
| **Responsibility** | Executes retrieval across memories and knowledge. Combines vector similarity search with structured queries. Ranks and deduplicates results. |
| **Inputs** | User ID, query text, retrieval scope (memory types, knowledge sources), relevance threshold, max results. |
| **Outputs** | RetrievalContext with ranked memories, book chunks, and relevance scores. |
| **Dependencies** | EmbeddingService (for query embedding), data layer (vector search, structured queries), MemoryService, LibraryService. |
| **Owned Rules** | Results are scoped to the user. Knowledge results are user-agnostic (same chunk, same relevance). Cross-context results merged by relevance score. |

### PromptContextService

| Aspect | Detail |
|---|---|
| **Responsibility** | Assembles the PromptContext for a single LLM call. Loads versioned system prompt, injects retrieved context, formats conversation history, sets generation parameters. |
| **Inputs** | User ID, conversation history, retrieval context, task type, generation parameters. |
| **Outputs** | PromptContext object (prompt template, assembled messages, retrieval summaries, generation config). |
| **Dependencies** | Data layer (prompt_templates), RetrievalService. |
| **Owned Rules** | Exactly one active prompt template per task type. Context is truncated to fit token limits (lowest-ranked items first). PromptContext is immutable once assembled. |

### RuntimeService

| Aspect | Detail |
|---|---|
| **Responsibility** | Top-level orchestrator for synchronous request processing. Coordinates the Planner and Executor. Manages the full request lifecycle from message receipt to response delivery. |
| **Inputs** | User ID, user message, conversation ID (optional), request metadata. |
| **Outputs** | Assistant response text, metadata (agents invoked, processing time, plan source). |
| **Dependencies** | ExecutionPlannerService, ExecutionExecutorService, ConversationService, EventPublisher. |
| **Owned Rules** | Request must be authenticated. Budget limits enforced at runtime level. Global timeout enforced. |

### ExecutionPlannerService

| Aspect | Detail |
|---|---|
| **Responsibility** | Produces an ExecutionPlan for a request. Evaluates rules first, escalates to LLM if needed. Validates and normalizes the plan. |
| **Inputs** | User ID, request content, conversation context, agent catalog, budget constraints. |
| **Outputs** | ExecutionPlan (ordered steps, input bindings, error strategies, confidence score, strategy used). |
| **Dependencies** | Data layer (execution_plan_templates), LLM Orchestration Service (for LLM planning), Agent Registry. |
| **Owned Rules** | Confidence threshold determines rule vs LLM path. Plan must pass validation (agent existence, availability, budget, safety). Invalid plans rejected with fallback to default template. |

### ExecutionExecutorService

| Aspect | Detail |
|---|---|
| **Responsibility** | Executes a validated ExecutionPlan. Invokes agents in order, collects outputs, handles per-step failures, publishes events. |
| **Inputs** | ExecutionPlan, execution context (user data, conversation history, pre-loaded state). |
| **Outputs** | Agent outputs (map of step ID to output), execution status (completed/aborted/failed), step statuses. |
| **Dependencies** | Agent Registry (to invoke agents), FailureManager, EventPublisher, ObservabilityLayer. |
| **Owned Rules** | Agents invoked in plan order. Optional steps skipped on dependency failure. Global timeout enforced. Cancellation signals propagated. Output validated against expected type. |

### EmbeddingService

| Aspect | Detail |
|---|---|
| **Responsibility** | Generates and manages vector embeddings. Stores embeddings in the vector database. Handles re-embedding on model upgrades. |
| **Inputs** | Text content, entity ID, entity type, model version. |
| **Outputs** | Embedding vector, embedding version, storage confirmation. |
| **Dependencies** | LLM Orchestration Service (for embedding generation), Vector Database. |
| **Owned Rules** | Embedding version tracked per entity. Stale embeddings (version < current) flagged for re-embedding. Embedding generation failures retried individually. |

### UserService

| Aspect | Detail |
|---|---|
| **Responsibility** | Manages User identity, preferences, authentication, authorization, data export, and data deletion. |
| **Inputs** | User credentials, preference updates, export/delete requests. |
| **Outputs** | User profile, JWT tokens, export file, deletion confirmation. |
| **Dependencies** | Data layer (users table), EventPublisher. |
| **Owned Rules** | Email unique across active users. Preferences validated against schema. Data deletion cascades to all user-owned entities. Export includes all user data. |

---

## 3. Service Interaction Rules

- **No circular dependencies**: Service A depends on Service B, never both.
- **No direct service-to-service calls**: Orchestration happens in Application Services or the Runtime Coordinator. If Service A needs Service B's capability, the orchestrator calls both and passes results.
- **Services interact through the data layer**: Services read/write to the data layer independently. They do not read each other's writes within the same transaction (unless orchestrated).
- **Input validation at service boundary**: Every service validates its inputs before processing. Invalid inputs rejected with typed errors.
- **Output contracts honored**: Every service returns exactly the output type declared in its contract. No surprises.

---

## 4. Transaction Boundaries

| Operation | Transaction |
|---|---|
| Message storage + conversation update | Single transaction |
| Memory creation + insight extraction | Single transaction per batch |
| Pattern update + evidence linkage | Single transaction |
| Reflection creation | Single transaction |
| Book status transition (processing → ready) | Single transaction |
| Prompt template activation (deactivate old + activate new) | Single transaction |
| Soft-delete cascade (user or book) | Single transaction |
| Execution plan creation + agent run logging | Separate transactions |
| Embedding generation | Outside transaction (async, eventually consistent) |
| LLM calls | Outside transaction (stateless computation) |

**Rule**: Long-running operations (LLM, embedding, external calls) never run inside transactions. Transactions are short and fast.

---

## 5. Error Propagation

**Service-level errors** are typed and propagated to the caller:

| Error Type | Behavior |
|---|---|
| **Validation error** | Service rejects input. Returns typed error. Caller decides next step. |
| **Not found** | Service returns empty or not-found error. Caller handles gracefully. |
| **Transient error** | Service retries internally (configurable max). If all retries fail, returns error to caller. |
| **Permanent error** | Service returns error immediately. No retry. |
| **Downstream failure** | Service wraps the error with context. Caller receives enriched error. |

**Rules**:
- Services never swallow errors silently.
- Services never throw raw exceptions to callers.
- Error messages include enough context for debugging but no sensitive data.
- Agent failures are isolated — never propagated to other agents.

---

## 6. Event Publishing

**Mechanism**: Services publish domain events through the EventPublisher after significant state changes.

| Service | Events Published |
|---|---|
| ConversationService | `MessageReceived`, `ResponseGenerated` |
| MemoryService | `MemoryStored`, `MemoryConsolidated` |
| InsightService | `InsightExtracted` |
| PatternService | `PatternUpdated`, `PatternCreated`, `PatternDeprecated` |
| ReflectionService | `ReflectionCreated` |
| LibraryService | `BookImported`, `BookIndexed` |
| UserService | `UserDataExported`, `UserDataDeleted` |
| ExecutionExecutorService | `RuntimeStarted`, `PlanCreated`, `AgentStarted`, `AgentCompleted`, `AgentFailed`, `PlanCompleted`, `RuntimeCompleted`, `RuntimeFailed` |

**Rules**:
- Events published after state is committed (not before).
- Events are fire-and-forget — services never wait for consumers.
- Events include enough context for consumers to act (user ID, entity ID, event type).
- Event publishing failure is logged but does not block the service call.

---

## 7. Caching Responsibilities

| Service | What to Cache | Strategy |
|---|---|---|
| PromptContextService | Active prompt templates (by task_type) | In-memory, invalidated on template activation |
| RetrievalService | Query embeddings (by query hash) | Short TTL (minutes), model-version aware |
| UserService | User preferences (by user_id) | In-memory, invalidated on preference update |
| LibraryService | Book metadata (by book_id) | Short TTL (minutes) |

**Rules**:
- Caching is a service-internal concern. Callers never know whether a cache was used.
- Cache invalidation is synchronous with state changes (not eventual).
- Cache keys include version/model to prevent stale data after upgrades.
- No cache for user-owned mutable data (memories, patterns) — always fresh from database.

---

## 8. Observability Responsibilities

Every service must:

- **Log**: Structured logs at INFO (state changes), WARN (recoverable errors), ERROR (unrecoverable errors). Include request ID, user ID, service name, operation.
- **Metrics**: Request count, latency (p50/p95/p99), error rate, cache hit rate.
- **Traces**: Distributed tracing spans for cross-service calls. Parent-child relationships preserved.
- **Audit**: User actions (data export, deletion, preference changes) logged as audit events.

**Rules**:
- No sensitive data in logs (no message content, no tokens, no passwords).
- Metrics aggregated at 1-minute intervals.
- Traces sampled at 10% in production, 100% in staging.

---

## 9. Service Lifecycle

| Phase | Description |
|---|---|
| **Design** | Contract defined (responsibility, inputs, outputs, dependencies, rules). |
| **Development** | Implementation against contract. Unit tests validate business rules. |
| **Integration** | Contract tests validate inputs/outputs. Integration tests validate data layer. |
| **Deployment** | Deployed independently. No coordination with other service deployments. |
| **Monitoring** | Metrics and traces monitored. Alerts on error rate spikes or latency degradation. |
| **Deprecation** | Contract marked deprecated. Callers migrated. Removed after migration complete. |

---

## 10. Future Expansion

**Adding a service**: Define contract (responsibility, inputs, outputs, dependencies, rules). Implement against contract. Register with orchestrator. No existing services modified.

**Adding a dependency**: New dependency added to service contract. Implementation updated. Existing callers unaffected (dependency is internal).

**Splitting a service**: If a service grows too large, split by subdomain. New service gets its own contract. Existing callers migrate incrementally. Old service deprecated.

**Merging services**: If two services are always called together and share data, consider merging. New merged service gets a new contract. Callers migrate. Old services deprecated.

**Rule**: New capabilities are additive. Existing service contracts do not change to accommodate new features.
