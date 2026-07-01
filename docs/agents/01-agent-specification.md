# Agent Layer Specification — Ayeneh

---

## 1. Agent Design Principles

- **Single responsibility**: Each agent owns exactly one cognitive task. No agent performs multiple unrelated operations.
- **Stateless**: Agents hold no persistent state between invocations. Every call is a fresh computation with externally assembled input.
- **No inter-agent communication**: Agents never call each other. The Execution Executor is the only entity that invokes agents.
- **Service-mediated**: Agents access data and external capabilities exclusively through services. No direct database, LLM, or infrastructure access.
- **Typed contracts**: Every agent has explicit input and output types. No unstructured data passing between agents.
- **Fail-safe**: Agent failures are isolated to their step. No failure propagation to other agents.
- **Observable**: Every agent execution is logged with timing, status, input summary, and output summary.

---

## 2. Agent Lifecycle

Each agent execution follows a strict lifecycle:

1. **Receive input**: The Executor passes the agent its input (a view of the Execution Context).
2. **Validate input**: The agent validates that required fields are present and well-formed. Invalid input → immediate failure.
3. **Execute logic**: The agent performs its cognitive task, invoking services as needed.
4. **Produce output**: The agent returns structured output matching its declared output type.
5. **Return control**: The agent returns to the Executor. It retains nothing from the invocation.

The agent does not persist data directly. If its output needs to be stored, the Executor handles persistence after receiving the output.

---

## 3. Base Agent Contract

Every agent conforms to this conceptual contract:

**Input**: A structured object containing:
- `user_id`: The authenticated User.
- `conversation_id`: The active Conversation (if applicable).
- `messages`: Relevant messages (bounded by context window).
- `retrieval_context`: Pre-loaded memories, patterns, knowledge (if applicable).
- `agent_output`: Outputs from previously executed agents in the plan (keyed by step ID).
- `task_parameters`: Agent-specific configuration for this invocation.

**Output**: A structured object containing:
- `status`: `success` | `partial` | `failed`.
- `data`: The agent's primary output (type varies per agent).
- `metadata`: Processing details (duration, items processed, confidence scores).
- `events`: Domain events to be published by the Executor.

**Contract invariants**:
- Output is always returned, even on failure (with `status: failed` and error details).
- Output never contains raw service internals — only domain-meaningful data.
- Output is always serializable (no circular references, no streams).

---

## 4. Agent Specifications

### ConversationAgent

| Aspect | Detail |
|---|---|
| **Purpose** | Generate a conversational response grounded in retrieved context. |
| **Inputs** | `user_id`, `conversation_id`, `messages` (recent history), `retrieval_context` (memories, knowledge, patterns), `task_parameters` (prompt template version, generation config). |
| **Outputs** | `response_text` (string), `inline_memory_suggestions` (optional: memories the LLM suggests extracting), `citations` (optional: referenced knowledge sources). |
| **Required Context** | Conversation history, retrieved memories, retrieved knowledge chunks, active prompt template. |
| **Produced Events** | None directly. Executor publishes `ResponseGenerated` after storing the response. |
| **Dependencies** | PromptContextService (to assemble prompt), LLM Orchestration Service (to generate), EmbeddingService (for query embedding during retrieval). |
| **Failure Behavior** | Returns `status: failed` with error. Executor may retry once. If all retries fail, returns user-facing error message without response text. |
| **Success Criteria** | Response text is non-empty, coherent, grounded in retrieved context, and matches the prompt template's instructions. |

### MemoryAgent

| Aspect | Detail |
|---|---|
| **Purpose** | Extract structured Memories and Insights from Messages. Determine what to store, update, and supersede. |
| **Inputs** | `user_id`, `messages` (new user + assistant messages), `retrieval_context` (existing memories for contradiction check), `task_parameters` (extraction confidence threshold). |
| **Outputs** | `new_memories` (array of Memory objects), `new_insights` (array of Insight objects), `updated_memories` (array of memories to supersede), `events` (MemoryStored, InsightExtracted). |
| **Required Context** | New messages, existing active memories (for contradiction detection). |
| **Produced Events** | `MemoryStored`, `InsightExtracted`. |
| **Dependencies** | MemoryService (to query existing memories, to persist new ones), LLM Orchestration Service (for extraction). |
| **Failure Behavior** | Returns `status: failed`. Messages already stored by ConversationService. Extraction retried asynchronously by Worker. Partial extraction (some memories saved) returns `status: partial`. |
| **Success Criteria** | Every extractable fact, belief, goal, and emotional state is captured. Contradictions with existing memories are detected. No duplicate memories created for the same content. |

### LibraryAgent

| Aspect | Detail |
|---|---|
| **Purpose** | Ingest, chunk, embed, and index knowledge sources. Retrieve relevant knowledge during conversations. |
| **Inputs** | For ingestion: `book_id`, `source_file` or `source_url`, `metadata`. For retrieval: `query`, `user_id`, `scope`, `max_results`. |
| **Outputs** | For ingestion: `chunks` (array of BookChunk objects), `ingestion_status` (ready/failed). For retrieval: `book_chunks` (ranked with citations and relevance scores). |
| **Required Context** | Book source file (ingestion), query embedding (retrieval). |
| **Produced Events** | `BookIndexed` (after successful ingestion). |
| **Dependencies** | LibraryService (to manage books/chunks), EmbeddingService (for chunk and query embedding), Knowledge Data Layer (vector search). |
| **Failure Behavior** | Ingestion: partial chunks stored, failed chunks retried. Book status set to `failed` if extraction fails entirely. Retrieval: returns empty results on failure, logs error. |
| **Success Criteria** | Ingestion: all chunks embedded, stored, and indexed. Book status = `ready`. Retrieval: relevant chunks returned with accurate citations and relevance scores above threshold. |

### PatternAgent

| Aspect | Detail |
|---|---|
| **Purpose** | Detect recurring cognitive and behavioral patterns across Memories and Insights over time. |
| **Inputs** | `user_id`, `memories` (within time window), `insights` (within time window), `existing_patterns` (for update/deprecation), `task_parameters` (time window, minimum evidence count). |
| **Outputs** | `new_patterns` (array), `updated_patterns` (array with changed strength/status), `deprecated_patterns` (array), `events` (PatternUpdated, PatternCreated, PatternDeprecated). |
| **Required Context** | Memories and Insights from the target time window, existing active patterns. |
| **Produced Events** | `PatternUpdated`, `PatternCreated`, `PatternDeprecated`. |
| **Dependencies** | PatternService (to query/update patterns), MemoryService (to query memories/insights), LLM Orchestration Service (for detection). |
| **Failure Behavior** | Returns `status: failed`. Job requeued with exponential backoff. Partial results discarded (detection is all-or-nothing per window). |
| **Success Criteria** | Patterns are supported by evidence from ≥ 2 distinct time periods. Contradictory evidence weakens or deprecates patterns. No duplicate patterns for the same tendency. Strength values are accurate. |

### ReflectionAgent

| Aspect | Detail |
|---|---|
| **Purpose** | Synthesize a longitudinal Reflection document from Memories, Insights, and Patterns within a time range. |
| **Inputs** | `user_id`, `time_period` (start/end), `memories`, `insights`, `patterns`, `prior_reflections` (for continuity), `task_parameters` (narrative style, length). |
| **Outputs** | `reflection` (Reflection object with title, narrative, evidence_snapshot), `events` (ReflectionCreated). |
| **Required Context** | Evidence from the target period, prior reflections for continuity. |
| **Produced Events** | `ReflectionCreated`. |
| **Dependencies** | ReflectionService (to persist), MemoryService (to collect evidence), PatternService (for pattern evidence), LLM Orchestration Service (for synthesis). |
| **Failure Behavior** | Returns `status: failed`. Job requeued. Partial results discarded. If insufficient evidence, returns `status: partial` with minimal reflection noting limited data. |
| **Success Criteria** | Narrative synthesizes evidence coherently. References underlying memories, insights, and patterns. Covers the full time period. No new facts introduced (only synthesis of existing evidence). |

### BlindSpotAgent

| Aspect | Detail |
|---|---|
| **Purpose** | Identify contradictions, gaps, and inconsistencies in the User's cognitive model. Surface Observations for self-inquiry. |
| **Inputs** | `user_id`, `patterns` (all active), `recent_memories`, `latest_reflections`, `task_parameters` (analysis depth). |
| **Outputs** | `observations` (array of Observation objects), `events` (BlindSpotDetected per observation). |
| **Required Context** | User's current patterns, recent memories, latest reflections. |
| **Produced Events** | `BlindSpotDetected`. |
| **Dependencies** | ReflectionService (to query observations), MemoryService (to query memories/patterns), LLM Orchestration Service (for analysis). |
| **Failure Behavior** | Returns `status: failed`. Job requeued. No observations surfaced (graceful absence). |
| **Success Criteria** | Observations are evidence-based, neutral, and non-judgmental. Each observation references specific contradictions or gaps. No duplicate observations for the same blind spot. |

---

## 5. Agent Communication Rules

- **Agents never communicate with each other.** All coordination is through the Execution Executor.
- **Agent output is consumed by the Executor**, not by other agents. If Agent B needs Agent A's output, the Executor passes it via the `agent_output` field in the input.
- **Agents publish events** as part of their output. The Executor handles persistence and event publishing.
- **Agents do not share mutable state.** Each agent receives a copy of its input, not a reference to shared state.
- **Agents do not make external calls** except through declared service dependencies. No direct HTTP, database, or LLM calls.

---

## 6. Agent Capability Matrix

| Capability | Conversation | Memory | Library | Pattern | Reflection | BlindSpot |
|---|---|---|---|---|---|---|
| Reads Messages | ✓ | ✓ | — | — | — | — |
| Reads Memories | ✓ | ✓ | — | ✓ | ✓ | ✓ |
| Reads Insights | — | ✓ | — | ✓ | ✓ | ✓ |
| Reads Patterns | ✓ | — | — | ✓ | ✓ | ✓ |
| Reads Reflections | — | — | — | — | ✓ | ✓ |
| Reads Books/Chunks | ✓ | — | ✓ | — | — | — |
| Writes Memories | — | ✓ | — | — | — | — |
| Writes Insights | — | ✓ | — | — | — | — |
| Writes Patterns | — | — | — | ✓ | — | — |
| Writes Reflections | — | — | — | — | ✓ | — |
| Writes Observations | — | — | — | — | — | ✓ |
| Writes Books/Chunks | — | — | ✓ | — | — | — |
| Calls LLM | ✓ | ✓ | — | ✓ | ✓ | ✓ |
| Generates Embeddings | — | — | ✓ | — | — | — |

---

## 7. Agent Isolation Rules

- **No agent references another agent by name.** Agents do not know which other agents exist.
- **No agent reads another agent's output directly.** The Executor mediates all data flow.
- **No agent modifies state owned by another agent's context.** MemoryAgent writes memories; PatternAgent reads them but writes patterns.
- **No agent accesses infrastructure directly.** All access goes through the service layer.
- **No agent makes decisions about which agents should run.** That is the Planner's responsibility.
- **No agent contains orchestration logic.** Orchestration is the Executor's responsibility.

---

## 8. Agent Timeouts

| Agent | Default Timeout | Maximum Timeout | Rationale |
|---|---|---|---|
| ConversationAgent | 30s | 60s | Primary response path. User waiting. |
| MemoryAgent | 15s | 30s | Extraction is post-response. Can be async-retried. |
| LibraryAgent (ingestion) | 300s | 600s | Long-running. Background job. |
| LibraryAgent (retrieval) | 5s | 10s | Fast retrieval. Graceful degradation on timeout. |
| PatternAgent | 60s | 120s | Async job. Can be retried. |
| ReflectionAgent | 120s | 300s | Complex synthesis. Async job. |
| BlindSpotAgent | 60s | 120s | Async job. Can be deferred. |

**Timeout behavior**: Agent is terminated. Output is discarded. Step marked as `failed`. Error strategy applied (retry, skip, or abort).

---

## 9. Agent Retry Policy

| Agent | Retryable | Max Retries | Backoff | Rationale |
|---|---|---|---|---|
| ConversationAgent | Yes | 1 | None (immediate) | User waiting. One retry acceptable. |
| MemoryAgent | Yes | 3 | Exponential (1s, 4s, 16s) | Async path. Transient LLM failures common. |
| LibraryAgent (ingestion) | Yes | 3 | Exponential | Long-running. Partial progress preserved. |
| LibraryAgent (retrieval) | No | 0 | — | Graceful degradation preferred over delay. |
| PatternAgent | Yes | 3 | Exponential | Async job. Transient failures recoverable. |
| ReflectionAgent | Yes | 2 | Exponential | Async job. Longer timeout first. |
| BlindSpotAgent | Yes | 2 | Exponential | Async job. Can be deferred. |

**Retry rules**: Same input on every retry. Output validated after each retry. All retries failed → step marked `failed`.

---

## 10. Agent Observability

Every agent execution logs:

- **Trace ID**: Links to the Execution Plan and request.
- **Step ID**: Unique within the plan.
- **Agent name**: Which agent executed.
- **Input summary**: Key parameters (not full content — size-bounded).
- **Output summary**: Key results (not full content — size-bounded).
- **Duration**: Milliseconds from start to completion.
- **Status**: `success` | `partial` | `failed`.
- **Error details**: If failed, the error message and type.
- **Retry count**: Number of retries attempted.
- **Service calls**: Which services were called, with latency.

**Metrics**:
- Execution count per agent (success/failure/partial).
- Latency distribution per agent (p50, p95, p99).
- Error rate per agent.
- Retry rate per agent.

---

## 11. Agent Versioning Strategy

- **Agents are not versioned individually.** They are stateless and version-agnostic — each invocation is independent.
- **Agent logic changes** are deployed as code updates. No migration needed.
- **Agent input/output contracts** may change between deployments. The Executor validates output against the expected type. Contract changes require coordination with the Planner (which specifies input/output types in the plan).
- **Prompt templates** are versioned separately (see PromptTemplate in the data model). Changing a prompt does not change the agent — it changes the instructions the agent follows.
- **Agent registration** (name, capabilities, contracts) is configuration-driven. Updating registration does not require code changes.

---

## 12. Future Agent Registration Model

New agents are registered through configuration:

1. **Declare the agent**: Name, description, capabilities (what it can read/write).
2. **Declare contracts**: Input type, output type, required context fields.
3. **Declare behavior**: Timeout, retry policy, failure strategy (retry/skip/abort/degrade).
4. **Register with the Planner**: The Planner learns the agent's capabilities and can include it in execution plans.
5. **Add Plan Templates**: Create templates that reference the new agent for common use cases.

**No existing agents or runtime code change.** The new agent is a new step type in the plan. The Executor invokes it like any other agent. The Planner determines when to include it.

**Registration validation**: The system validates that declared input/output types are compatible with existing services. Incompatible registrations are rejected at configuration time, not at runtime.
