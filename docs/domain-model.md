# Domain Model — Ayeneh

## 1. Purpose

Ayeneh is a **Cognitive Companion**, not a chatbot. The distinction is fundamental to the domain.

A chatbot processes messages and generates replies. Its purpose is conversational throughput. Ayeneh processes messages to extract meaning, detect patterns, build a structured model of the user's thinking, and generate insights over time. Conversation is a means, not an end.

The core purpose is to help users observe themselves. Every interaction feeds a persistent model of the user's cognition — what they believe, how they feel, what patterns repeat, and how their perspective changes. The system reflects this model back through structured insights and reflections.

This domain model defines the concepts, boundaries, and rules that make that possible.

---

## 2. Ubiquitous Language

Every term below must be used consistently across all code, documentation, and communication. Variations are considered defects.

---

### User

| Aspect | Description |
|---|---|
| **Definition** | The person whose cognition is being modeled. The subject of all observations, memories, and reflections. |
| **Responsibility** | Provides raw material (messages, journal entries) for cognitive modeling. Owns all data in their boundary. |
| **Lifecycle** | Created on first interaction. Exists indefinitely. Can be deactivated but never deleted (data integrity). |
| **Relationships** | Has many Conversations, Sessions, Memories, Insights, Patterns, Reflections. |

---

### Conversation

| Aspect | Description |
|---|---|
| **Definition** | A coherent exchange between User and Ayeneh around a topic or intent. Spans multiple Messages. |
| **Responsibility** | Groups Messages into a logical unit. Provides temporal and thematic context for memory extraction. |
| **Lifecycle** | Created when a User starts a new topic. Closed explicitly or after a period of inactivity. |
| **Relationships** | Belongs to a User. Contains Messages. Generates Memories and Insights. |

---

### Session

| Aspect | Description |
|---|---|
| **Definition** | A continuous period of interaction. May span multiple Conversations. |
| **Responsibility** | Tracks presence and continuity. Used to determine recency weighting in retrieval. |
| **Lifecycle** | Created when User connects. Ends on disconnect or timeout. |
| **Relationships** | Belongs to a User. Contains Conversations. |

---

### Message

| Aspect | Description |
|---|---|
| **Definition** | A single utterance from User or Ayeneh. The atomic unit of interaction. |
| **Responsibility** | Carries content. Triggers memory extraction. Is the source of raw evidence for patterns. |
| **Lifecycle** | Created during a Conversation. Immutable after creation. |
| **Relationships** | Belongs to a Conversation. References preceding Messages for context. Is the origin of one or more Memories. |

---

### Memory

| Aspect | Description |
|---|---|
| **Definition** | A structured representation of something learned from a Message. The fundamental unit of persistent cognition. |
| **Responsibility** | Preserves extracted facts, events, and context across sessions. Answers "what does the system know about the User." |
| **Lifecycle** | Created during message processing. Updated by later messages that contradict or refine it. Consolidated over time. |
| **Relationships** | Belongs to a User. Originates from one or more Messages. Feeds into Insights, Patterns, Reflections. |

---

### Memory Retrieval

| Aspect | Description |
|---|---|
| **Definition** | The process of selecting Memories relevant to the current context. Not a stored thing — an operation. |
| **Responsibility** | Provides the right context to every prompt. Every retrieval is scoped, ranked, and weighted. |
| **Lifecycle** | Triggered on every User Message. Uses query, recency, relevance, and type filters. |
| **Relationships** | Consumes Memories. Produces a PromptContext. |

---

### Insight

| Aspect | Description |
|---|---|
| **Definition** | A synthesized observation extracted from a single Message or small set of Messages. Granular and immediate. |
| **Responsibility** | Captures something noteworthy about the User's current state — a stated belief, a change in tone, a new goal. |
| **Lifecycle** | Created during message processing. Accumulates until consumed by Pattern or Reflection. |
| **Relationships** | Belongs to a User. Derived from Messages. Feeds into Patterns and Reflections. |

---

### Pattern

| Aspect | Description |
|---|---|
| **Definition** | A recurring tendency detected across multiple Insights or Memories over time. |
| **Responsibility** | Answers "what does the User tend to do, feel, or believe." Evolves with new evidence. |
| **Lifecycle** | Created when sufficient evidence accumulates. Updated as new evidence strengthens or weakens it. Can be deprecated by contradictory evidence. |
| **Relationships** | Belongs to a User. References Insights and Memories as evidence. Feeds into Reflections. May relate to other Patterns (supports, contradicts, supersedes). |

---

### Reflection

| Aspect | Description |
|---|---|
| **Definition** | A structured document that synthesizes multiple Memories, Insights, and Patterns into a coherent narrative about the User's cognitive state. |
| **Responsibility** | Provides a longitudinal view. Summarizes what has changed, what persists, and what may need attention. |
| **Lifecycle** | Created periodically or on demand. References underlying evidence. Replaced by newer Reflections but never deleted. |
| **Relationships** | Belongs to a User. Composed from Memories, Insights, and Patterns. Presented to User for review. |

---

### Library

| Aspect | Description |
|---|---|
| **Definition** | The bounded context that owns external knowledge. Books, documents, and their chunks live here. |
| **Responsibility** | Ingests, stores, and retrieves external knowledge. Provides citations. Has no awareness of User state. |
| **Lifecycle** | Entries added by User or administrator. Exist indefinitely. Updated when new versions provided. |
| **Relationships** | Contains Books. Serves retrieval requests from the RAG layer. |

---

### Book

| Aspect | Description |
|---|---|
| **Definition** | A discrete external knowledge source imported into the Library. |
| **Responsibility** | Provides structured content for chunking and embedding. Carries metadata for citation. |
| **Lifecycle** | Created on import. Read during retrieval. Can be removed by User. |
| **Relationships** | Belongs to the Library. Contains BookChunks. |

---

### Book Chunk

| Aspect | Description |
|---|---|
| **Definition** | A segment of a Book, split at semantic boundaries. The atomic unit of knowledge retrieval. |
| **Responsibility** | Carries a semantically coherent passage. Embeddable and retrievable. Always attributable to a source. |
| **Lifecycle** | Created when a Book is ingested. Retrieved during RAG queries. |
| **Relationships** | Belongs to a Book. Has a position within the Book. Carries a citation path (chapter, section, page). |

---

### Quote

| Aspect | Description |
|---|---|
| **Definition** | A verbatim excerpt from a Book Chunk, attributed and included in a response. |
| **Responsibility** | Provides evidence and authority. Enables User to verify claims against source material. |
| **Lifecycle** | Created at response time. Never stored permanently — reconstructed from BookChunk reference. |
| **Relationships** | References a BookChunk. Included in a Response. Presented to User. |

---

### Prompt Context

| Aspect | Description |
|---|---|
| **Definition** | The assembled set of instructions and data passed to the LLM for a single generation. |
| **Responsibility** | Contains the system prompt (versioned), retrieved Memories, Book Chunks, recent Messages, and generation parameters. |
| **Lifecycle** | Assembled per-request. Discarded after the LLM call completes. |
| **Relationships** | Composed from Prompt Template, Memory Retrieval results, and Knowledge Retrieval results. Consumed by an AgentRun. |

---

### Agent

| Aspect | Description |
|---|---|
| **Definition** | A cognitive unit with a single responsibility. Receives input, produces output. |
| **Responsibility** | Executes one phase of cognition — conversation, memory extraction, pattern detection, reflection generation, etc. |
| **Lifecycle** | Stateless. Instantiated per request. Exists as a module, not a persistent entity. |
| **Relationships** | Consumes services. Produces structured output that is collected by the Execution Executor. Never calls other agents directly. |

---

### Execution Plan

| Aspect | Description |
|---|---|
| **Definition** | A structured description of the work to be done for a single request. Produced by the Execution Planner, consumed by the Execution Executor. |
| **Responsibility** | Determines which agents participate, in what order, with what input, and how failures are handled. |
| **Lifecycle** | Created per-request by the Planner. Discarded after execution. Transient and request-scoped. |
| **Relationships** | References agents by name and input/output contracts. References the execution context. Produced by the Planner, consumed by the Executor. |

---

### Execution Plan Template

| Aspect | Description |
|---|---|
| **Definition** | A pre-defined Execution Plan for a known request pattern. Used by the rule engine to avoid LLM-assisted planning overhead. |
| **Responsibility** | Maps request characteristics to a deterministic agent sequence. Handles common cases (simple conversation, knowledge query, reflection request) without LLM cost. |
| **Lifecycle** | Created by system configuration. Updated when new agent capabilities are registered. Persistent. |
| **Relationships** | References agents and their input/output contracts. Matched to requests by the rule engine. |

---

### Observation

| Aspect | Description |
|---|---|
| **Definition** | A neutral, non-judgmental statement about the User's cognition, surfaced by an Agent. |
| **Responsibility** | Presents evidence without interpretation. Lets the User draw their own conclusions. |
| **Lifecycle** | Created during processing. Presented to User. Can be referenced by later Reflections. |
| **Relationships** | Belongs to a User. Originates from an Agent. References underlying Memories or Patterns. |

---

### Blind Spot

| Aspect | Description |
|---|---|
| **Definition** | An identified gap, contradiction, or inconsistency in the User's self-model. |
| **Responsibility** | Surfaces what the User may be overlooking. Designed to provoke curiosity, not defense. |
| **Lifecycle** | Created by BlindSpotAgent when contradictory evidence is detected. Can be resolved, confirmed, or dismissed by User. |
| **Relationships** | Belongs to a User. References contradictory Memories, Patterns, or Insights. Tracks resolution status. |

---

### Habit

| Aspect | Description |
|---|---|
| **Definition** | A repeated behavior or routine observed across multiple sessions. |
| **Responsibility** | Answers "what does the User regularly do." Distinct from Pattern in that Habit is behavioral, Pattern is cognitive. |
| **Lifecycle** | Identified by PatternAgent. Evolves as behavior changes. Can be consciously modified by User. |
| **Relationships** | Belongs to a User. Supported by temporal evidence from Memories. May be linked to Reflections about change. |

---

### Emotion

| Aspect | Description |
|---|---|
| **Definition** | An affective state expressed or implied in a Message. |
| **Responsibility** | Provides emotional context for Memory extraction and Pattern detection. |
| **Lifecycle** | Detected per Message. Aggregated into emotional trends. Not stored as a first-class entity — always derived. |
| **Relationships** | Present in Messages. Contributes to Pattern detection. Tracked over time for emotional trend analysis. |

---

### Theme

| Aspect | Description |
|---|---|
| **Definition** | A recurring subject or topic that appears across multiple Conversations and Memories. |
| **Responsibility** | Groups related content under a conceptual umbrella. Enables cross-session navigation and synthesis. |
| **Lifecycle** | Emerges automatically as Memories accumulate. Can be named or renamed by User. Merged or split as understanding evolves. |
| **Relationships** | Belongs to a User. Groups Memories, Insights, and Patterns. Feeds into Reflections. |

---

## 3. Domain Entities

Each entity below represents a conceptual identity in the domain. Attributes are described conceptually — they are not database columns.

---

### User

| Aspect | Description |
|---|---|
| **Description** | The subject of all cognitive modeling. A User exists from first interaction and owns all associated data. |
| **Responsibilities** | Authenticates identity. Provides raw interaction data. Controls data retention and export. Configures preferences (LLM provider, reflection cadence, privacy level). |
| **Important Attributes** | Identity, preferences, lifecycle state (active / paused / deactivated), creation time, last active time. |
| **Relationships** | Owns all Conversations, Memories, Insights, Patterns, Reflections. References Library for knowledge retrieval. |
| **Created By** | Registration or first interaction. |
| **Updated By** | User profile changes, activity updates. |
| **Read By** | System (during processing), User (via interface). |

---

### Conversation

| Aspect | Description |
|---|---|
| **Description** | A bounded interaction around a purpose or topic. Groups Messages for context. |
| **Responsibilities** | Maintains topic coherence. Provides temporal grouping for extraction. Holds metadata (title, summary, tags). |
| **Important Attributes** | Topic, status (active / closed / archived), start time, end time, message count, summary. |
| **Relationships** | Owned by User. Contains Messages. Generates Memories. |
| **Created By** | User (explicitly or implicitly by sending a first message). |
| **Updated By** | System (new messages, summary updates). |
| **Read By** | System (context assembly), User (review). |

---

### Session

| Aspect | Description |
|---|---|
| **Description** | A continuous connection period. Spans zero or more Conversations. |
| **Responsibilities** | Tracks presence. Provides recency signal for retrieval weighting. |
| **Important Attributes** | Start time, end time, duration, conversation count, device/platform. |
| **Relationships** | Owned by User. Contains Conversations. |
| **Created By** | System on User connect. |
| **Updated By** | System on disconnect. |
| **Read By** | System (retrieval weighting). |

---

### Message

| Aspect | Description |
|---|---|
| **Description** | The atomic interaction unit. A single utterance from User or Ayeneh. |
| **Responsibilities** | Carries content and metadata. Triggers memory extraction. Serves as evidence for Patterns. |
| **Important Attributes** | Content, role (user / assistant), timestamp, sequence position, extracted Emotions, referenced Memories. |
| **Relationships** | Belongs to a Conversation. References preceding Messages. Origin of one or more Memories. |
| **Created By** | User (sends) or System (generated response). |
| **Updated By** | Never — immutable after creation. |
| **Read By** | System (processing, retrieval), User (review). |

---

### Memory

| Aspect | Description |
|---|---|
| **Description** | A structured knowledge unit extracted from Messages. The persistent representation of what the system knows. |
| **Responsibilities** | Preserves facts, events, beliefs, and relationships. Supports semantic and structured retrieval. Can be consolidated and refined. |
| **Important Attributes** | Type (episodic / semantic / pattern / reflection), content, confidence, creation timestamp, relevance score, evidence references. |
| **Relationships** | Owned by User. Originates from Messages. Referenced by Insights, Patterns, Reflections. |
| **Created By** | MemoryAgent during message processing. |
| **Updated By** | MemoryAgent (consolidation, refinement, contradiction resolution). |
| **Read By** | All Agents (via MemoryService), User (via interface). |

---

### Insight

| Aspect | Description |
|---|---|
| **Description** | A granular observation extracted from one or more Messages. A building block for higher-level cognition. |
| **Responsibilities** | Captures a discrete observation. Accumulates until synthesized into Patterns or Reflections. |
| **Important Attributes** | Content, type (belief / goal / change / concern / etc.), confidence, source Messages, timestamp. |
| **Relationships** | Owned by User. Derived from Messages. Consumed by Patterns and Reflections. |
| **Created By** | MemoryAgent or InsightExtraction service. |
| **Updated By** | System (confidence adjustment, refutation). |
| **Read By** | PatternAgent, ReflectionAgent, User. |

---

### Pattern

| Aspect | Description |
|---|---|
| **Description** | A recurrent cognitive or behavioral tendency detected across time. |
| **Responsibilities** | Describes what the User tends to do, feel, or believe. Evolves with new evidence. Supports contradiction tracking. |
| **Important Attributes** | Description, strength, evidence count, first detected time, last updated time, status (active / weakening / deprecated), contradictory Patterns. |
| **Relationships** | Owned by User. References supporting Insights and Memories. May relate to other Patterns. Feeds into Reflections. |
| **Created By** | PatternAgent. |
| **Updated By** | PatternAgent (as new evidence arrives or contradicts). |
| **Read By** | ConversationAgent, ReflectionAgent, BlindSpotAgent, User. |

---

### Reflection

| Aspect | Description |
|---|---|
| **Description** | A synthesized document that weaves Memories, Insights, and Patterns into a coherent narrative about the User's cognitive evolution. |
| **Responsibilities** | Provides a longitudinal summary. Highlights changes, persistent themes, and areas of growth. Supports User review and annotation. |
| **Important Attributes** | Title, narrative body, time period covered, referenced entities, status (draft / published / archived), User notes. |
| **Relationships** | Owned by User. Composed from Memories, Insights, Patterns. May reference prior Reflections. |
| **Created By** | ReflectionAgent (scheduled or on demand). |
| **Updated By** | System (if regenerated), User (annotations). |
| **Read By** | User (primary), BlindSpotAgent (for gap analysis). |

---

### Observation

| Aspect | Description |
|---|---|
| **Description** | A neutral, evidence-based statement surfaced to the User. Non-judgmental by design. |
| **Responsibilities** | Presents what the system has noticed without interpretation. Supports User self-inquiry. |
| **Important Attributes** | Content, source (which Agent), supporting evidence, timestamp, status (pending / acknowledged / dismissed). |
| **Relationships** | Owned by User. Originates from an Agent. References underlying Memories or Patterns. |
| **Created By** | Any Agent (primarily BlindSpotAgent and PatternAgent). |
| **Updated By** | User (acknowledgment or dismissal). |
| **Read By** | User. |

---

### Book

| Aspect | Description |
|---|---|
| **Description** | An external knowledge source imported into the Library. Any document the User wishes to reference. |
| **Responsibilities** | Provides authoritative content. Carries metadata for accurate citation. |
| **Important Attributes** | Title, author, source format, import time, status (processing / ready / failed), metadata (ISBN, URL, etc.). |
| **Relationships** | Belongs to Library context. Contains BookChunks. Referenced by Quotes in responses. |
| **Created By** | User (upload or link). |
| **Updated By** | System (status updates during processing). |
| **Read By** | RAG layer (during retrieval), User (browsing). |

---

### BookChunk

| Aspect | Description |
|---|---|
| **Description** | A semantically coherent segment of a Book. The retrievable unit of external knowledge. |
| **Responsibilities** | Carries content and positional metadata for accurate citation. Embeddable for semantic search. |
| **Important Attributes** | Content, sequence position, chapter, section, page range, embedding vector (conceptually), token count. |
| **Relationships** | Belongs to a Book. Referenced by Quotes. |
| **Created By** | LibraryAgent during book ingestion. |
| **Updated By** | Never — re-ingestion creates new chunks; old chunks are replaced. |
| **Read By** | RAG layer, User (via citation). |

---

### Quote

| Aspect | Description |
|---|---|
| **Description** | A verbatim excerpt from a BookChunk, attributed and included in an Ayeneh response. |
| **Responsibilities** | Provides direct evidence. Enables source verification. |
| **Important Attributes** | Excerpt text, source reference (Book, chapter, section), position in response. |
| **Relationships** | References a BookChunk. Part of a Message. |
| **Created By** | System at response generation time. |
| **Updated By** | Never — transient, reconstructed on demand. |
| **Read By** | User. |

---

### AgentRun

| Aspect | Description |
|---|---|
| **Description** | A record of a single Agent execution within an Execution Plan. Captures what happened for observability. |
| **Responsibilities** | Logs inputs, outputs, duration, and errors. Supports debugging, audit, and performance analysis. |
| **Important Attributes** | Agent type, input summary, output summary, start time, duration, status (success / failed), error details, plan step reference. |
| **Relationships** | References the Agent definition and the Execution Plan step. Associated with the triggering Message or Job. Not a domain entity — an infrastructure record. |
| **Created By** | Execution Executor when an Agent executes as part of a plan. |
| **Updated By** | System (status updates). |
| **Read By** | Developers (debugging), System (monitoring). |

---

### PromptContext

| Aspect | Description |
|---|---|
| **Description** | The complete set of instructions and data assembled for a single LLM call. |
| **Responsibilities** | Ensures every LLM call has the right system instructions, retrieved context, and user input. Versioned for reproducibility. |
| **Important Attributes** | Prompt template version, assembled messages (system, context, user), retrieval summaries, generation parameters. |
| **Relationships** | Composed by Prompt Builder Service. Consumed by LLM Orchestration Service. |
| **Created By** | Prompt Builder Service per request. |
| **Updated By** | Never — discarded after use. |
| **Read By** | LLM Orchestration Service. |

---

### RetrievalContext

| Aspect | Description |
|---|---|
| **Description** | The result set of a memory or knowledge retrieval operation. Captures what was considered. |
| **Responsibilities** | Preserves the evidence base for a given generation. Enables audit of what context influenced a response. |
| **Important Attributes** | Query used, retrieved items with scores, scope (memory types, knowledge sources), ranking strategy, timestamp. |
| **Relationships** | Produced by Memory Retrieval Service or Knowledge Service. Consumed by Prompt Builder Service. |
| **Created By** | Retrieval services per request. |
| **Updated By** | Never — discarded after use. |
| **Read By** | Prompt Builder Service, audit/debugging. |

---

## 4. Aggregates

### Aggregate Roots

| Aggregate Root | Owns | Invariant |
|---|---|---|
| **User** | Conversations, Sessions, Memories, Insights, Patterns, Reflections, Observations, BlindSpots | A User is the sole owner of all cognitive data within their boundary. No entity crosses User boundaries. |
| **Conversation** | Messages | Messages belong to exactly one Conversation. Conversation owns the lifecycle of its Messages. |
| **Book** | BookChunks | Book owns its chunks. Chunks are created and replaced only through Book operations. |
| **Reflection** | Referenced entities (read-only references) | A Reflection references Memories, Insights, and Patterns but does not own them. |

### Ownership Boundaries

- **User Aggregate** is the top-level ownership boundary. Nothing spans multiple Users.
- **Conversation Aggregate** is the unit of interaction. Messages cannot exist outside a Conversation.
- **Book Aggregate** is the unit of knowledge import. BookChunks cannot exist outside a Book.
- **Reflection** is a document aggregate. It references but does not own its constituent entities.
- **Patterns** and **Insights** are owned by User but are not aggregate roots themselves — they are always accessed through User or through domain services that perform cross-entity retrieval.

---

## 5. Domain Services

Domain services encapsulate operations that do not naturally belong to a single entity.

### Memory Retrieval Service

Responsible for querying Memories across all four types. Applies scoping (by User, time range, type), ranking (by relevance, recency, importance), and filtering (by confidence threshold). Does not know about prompts or agents — only about retrieval.

### Pattern Detection Service

Responsible for scanning Memories and Insights over a time window to identify recurring themes, behaviors, and emotional tendencies. Produces candidate Patterns and updates existing Patterns with new evidence. Runs asynchronously.

### Reflection Service

Responsible for assembling a Reflection from a set of Memories, Insights, and Patterns within a time range. Determines narrative structure, selects salient points, and ensures the Reflection is grounded in evidence. May be triggered periodically or on demand.

### Library Search Service

Responsible for querying the Book and BookChunk collection. Handles query embedding, vector search, metadata filtering, and result ranking. Returns results with citation paths. Has no awareness of User state.

### Prompt Builder Service

Responsible for assembling a PromptContext for a given generation task. Selects the correct versioned system prompt, injects retrieved context (Memories, BookChunks), formats conversation history, and sets generation parameters. The only service that bridges retrieval and generation.

### LLM Orchestration Service

Responsible for executing LLM calls via the LiteLLM abstraction. Handles provider selection, retries, fallbacks, rate limiting, and response parsing. Returns structured output. Has no awareness of prompt content or domain logic.

### Insight Extraction Service

Responsible for extracting discrete Insights from a Message or Message sequence. Identifies stated beliefs, goals, emotional states, and changes. Produces structured Insight records. Called during message processing.

---

## 6. Domain Events

Events are named in past tense. They represent something that has already happened.

| Event | Trigger | Meaning | Consumed By |
|---|---|---|---|
| **MessageReceived** | User sends a message | New raw data is available for processing. | API (triggers processing pipeline), Worker (enqueues async jobs). |
| **ResponseGenerated** | LLM call completes successfully | A response is ready for delivery and the generation is complete. | API (delivers to User), MemoryAgent (extracts memories from response). |
| **MemoryStored** | MemoryAgent extracts and persists a Memory | New structured knowledge is available. | PatternAgent (may trigger pattern reevaluation), Worker (may schedule consolidation). |
| **InsightExtracted** | Insight Extraction Service completes | A discrete observation has been captured. | PatternAgent (feeds pattern detection), Reflection Service (may trigger reflection update). |
| **PatternUpdated** | PatternAgent detects change in evidence | A Pattern's strength, status, or description has changed. | ReflectionAgent (may trigger reflection regeneration), BlindSpotAgent (may detect contradictions). |
| **ReflectionCreated** | Reflection Service completes generation | A new longitudinal synthesis is available. | User (notified), BlindSpotAgent (may analyze for gaps). |
| **BookIndexed** | Library ingestion pipeline completes | A Book is ready for retrieval. | RAG layer (updates search index), User (notified). |
| **BlindSpotDetected** | BlindSpotAgent identifies a contradiction | A potential gap in self-understanding has been found. | User (surfaced as observation), ReflectionAgent (may incorporate into next Reflection). |
| **UserStateChanged** | Significant change in User's cognitive model | The system's understanding of the User has meaningfully shifted. | Worker (may trigger early reflection), User (may receive notification). |

---

## 7. Bounded Contexts

### Conversation Context

**Responsibility**: Owns the real-time interaction between User and Ayeneh. Manages sessions, conversations, messages, and the immediate response loop.

**Entities**: Session, Conversation, Message.

**Collaborates with**: Memory Context (for retrieval and extraction), Knowledge Context (for grounded responses), Prompt Context (for assembly).

**Key rule**: No long-term state lives here. Everything is transient or immediately passed to Memory.

---

### Memory Context

**Responsibility**: Owns all forms of structured knowledge about the User. Controls memory extraction, storage, retrieval, consolidation, and lifecycle.

**Entities**: Memory (all four types), Insight.

**Collaborates with**: Conversation Context (receives messages), Pattern Analysis Context (provides raw material), Reflection Context (provides evidence).

**Key rule**: Memory is the single source of truth about what the system knows. No other context persists User knowledge.

---

### Knowledge Context

**Responsibility**: Owns external knowledge sources. Manages ingestion, chunking, embedding, retrieval, and citation.

**Entities**: Book, BookChunk, Quote.

**Collaborates with**: Conversation Context (provides grounded context for responses), Memory Context (retrieval scope is separate).

**Key rule**: Knowledge Context has no awareness of User state. It is a library, not a profile.

---

### Reflection Context

**Responsibility**: Owns the periodic synthesis of Memories, Insights, and Patterns into structured narrative documents.

**Entities**: Reflection.

**Collaborates with**: Memory Context (reads evidence), Pattern Analysis Context (reads patterns), Conversation Context (may be triggered by user request).

**Key rule**: A Reflection never contains new facts. It synthesizes what already exists.

---

### Pattern Analysis Context

**Responsibility**: Owns the detection, evolution, and lifecycle of cognitive and behavioral Patterns.

**Entities**: Pattern, Habit.

**Collaborates with**: Memory Context (reads Memories and Insights), Reflection Context (provides input), Blind Spot Context (provides contradictory evidence).

**Key rule**: Patterns emerge from evidence. They are never created without supporting data.

---

### Identity Context

**Responsibility**: Owns User identity, authentication, authorization, and preferences.

**Entities**: User (identity aspects only).

**Collaborates with**: All contexts (for user scoping).

**Key rule**: No cognitive data lives in this context. It handles who you are, not what you think.

---

### Infrastructure Context

**Responsibility**: Owns cross-cutting concerns: LLM abstraction (LiteLLM), embedding generation, logging, monitoring, configuration, and the Agent Runtime (Execution Planner and Execution Executor).

**Not domain entities**: This context has no domain entities. It provides services consumed by all other contexts. The Planner and Executor are infrastructure components that orchestrate agent invocations.

**Collaborates with**: Every context that needs LLM calls or embeddings. Invokes agents through well-defined interfaces.

**Key rule**: Infrastructure never contains domain logic. The Planner determines what to execute based on request characteristics and Plan Templates; the Executor runs the plan. Neither contains business rules about Memory, Pattern, or Reflection semantics.

---

## 8. Invariants

The following business rules must always hold true.

### Agent Isolation

No Agent directly modifies state owned by another Agent's responsibility. ConversationAgent does not write Memories. MemoryAgent does not generate responses. Coordination happens at the Execution Executor, which invokes agents in the order specified by the Execution Plan. No Agent knows about other Agents — they receive input from the Executor and return output to it.

### LLM Statelessness

The LLM never owns or stores User data. Every LLM call is a stateless computation. Context is always assembled externally and discarded after use.

### Message Origin

Every Insight is derived from one or more Messages. Insights cannot be created from nothing. A Message without extraction may produce zero Insights, but an Insight always traces back to a Message.

### Pattern Grounding

Every Pattern is supported by at least two pieces of evidence (Memories or Insights) from distinct time periods. A single observation does not constitute a Pattern.

### Knowledge Isolation

Knowledge (Books, Chunks) is a separate bounded context. No User-specific state influences knowledge ingestion or retrieval. Knowledge retrieval is stateless with respect to the User's cognitive model.

### Temporal Consistency

Memories are timestamped and never retroactively changed. Corrections create new Memories that supersede old ones. This preserves the temporal integrity of the cognitive model.

### Reflection Non-Ownership

A Reflection references Memories, Insights, and Patterns but does not own them. Deleting a Reflection has no effect on the entities it references.

### User Data Boundary

No entity, event, or operation spans multiple Users. Every query, retrieval, and mutation is scoped to exactly one User.

### Memory Type Integrity

A Memory has exactly one type (episodic, semantic, pattern, or reflection). No hybrid types. A single Memory cannot serve two type roles.

---

## 9. Future Evolution

### Adding New Agents

A new Agent defines its input, output, and responsibility. It is registered with the Execution Planner, which learns its capabilities and input/output contracts. The Planner can then include the new agent in execution plans when the request characteristics match. New Plan Templates can be added to handle common use cases of the new agent. No existing Agents or services are modified. The new Agent uses existing services (MemoryService, KnowledgeService, LLMService) and produces output that existing services can consume. No domain model changes are required.

### Adding New Memory Types

A new Memory type is introduced by:
1. Adding it to the Memory type vocabulary in the Ubiquitous Language.
2. Defining its relationship to existing types.
3. Implementing a new retrieval strategy (if needed) in the Memory Retrieval Service.

Existing Agents and services require no changes. The MemoryService interface expands to accommodate the new type, but existing methods remain unchanged.

### Adding New Knowledge Sources

A new knowledge source type (e.g., web pages, RSS, audio transcripts) requires:
1. A new ingestion pipeline in the Knowledge Context that produces BookChunks.
2. No changes to the retrieval, citation, or response generation paths.

The BookChunk entity abstracts source-specific details. As long as the new source produces standard BookChunks, the rest of the system is unaffected.

### Adding New Bounded Contexts

A new bounded context defines its own entities, services, and events. It communicates with existing contexts through domain events and service interfaces. The overall coordination is managed at the application layer (API and Worker). Existing contexts do not need to know about the new context.

### Non-Breaking Pattern

The domain model is designed so that new capabilities are additive. No existing entity, service, or event changes its contract to accommodate new functionality. Old consumers continue to work. This is achieved through:
- Interface-based service definitions
- Event-driven communication for async workflows
- Clear aggregate boundaries that prevent cascading changes
- A Ubiquitous Language that is extended, not revised
