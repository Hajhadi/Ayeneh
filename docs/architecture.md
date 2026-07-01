# Ayeneh Architecture

## 1. Vision

Ayeneh is a **Cognitive Companion** — a tool designed for self-observation, cognitive growth, and long-term reflection. It helps users observe their own thinking patterns, track how their perspectives evolve over time, and engage with external knowledge in a structured way.

Ayeneh is **not** a spiritual chatbot, a therapist replacement, or a generic assistant. It does not offer advice, diagnose, or simulate empathy. Instead, it acts as a mirror (the name *Ayeneh* means "mirror" in Persian) — reflecting back what the user has thought, how they have changed, and what patterns emerge across their journal entries, conversations, and interactions.

The ultimate goal is to empower users to understand themselves better through structured reflection, not to replace human relationships or professional help.

## 2. Design Principles

### LLMs Are Stateless
Each LLM call is treated as a stateless computation. No conversational state is stored inside the model. Context is reconstructed from external memory on every request.

### Memory Lives Outside the Model
All user data — conversations, extracted facts, detected patterns, reflections — lives in persistent storage. The LLM is a reasoning engine, not a storage medium.

### Retrieval Before Generation
Every response is grounded in retrieved context. The system retrieves relevant memories, knowledge, and patterns before constructing a prompt. Generation never happens from a blank slate.

### Service Layer Abstraction
Every capability (memory, retrieval, prompting, pattern detection) is encapsulated behind a service interface. Callers depend on abstractions, not concrete implementations.

### Modular Architecture
The system is composed of small, interchangeable modules. Each module has a single responsibility and communicates with others through well-defined boundaries.

### Dynamic Execution Planning
The Agent Runtime does not use a fixed sequential pipeline. Instead, an Execution Planner determines which agents should participate in processing a request, and an Execution Executor runs the generated plan. The Planner uses a hybrid strategy: rule-based planning for common request patterns, and LLM-assisted planning only when the rule engine cannot confidently determine the plan. See ADR-007.

### Replaceable LLM Providers
No hard dependency on any single LLM provider. The system uses LiteLLM as a uniform interface, allowing providers to be swapped via configuration.

### Versioned Prompts
Every prompt is versioned and stored as data. Prompt changes are tracked, reviewed, and deployed independently of application code.

### Separation of Prompts and Knowledge
Prompts (instructions for the LLM) are maintained separately from knowledge (the content the LLM reasons over). Knowledge is data; prompts are configuration.

## 3. High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Frontend                           │
│              (Web / Mobile / CLI)                       │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP / WebSocket
                       ▼
┌─────────────────────────────────────────────────────────┐
│                      API Layer                           │
│           (REST + WebSocket, Authentication, Routing)    │
└──────────┬──────────────────────────────┬────────────────┘
           │                              │
           ▼                              ▼
┌──────────────────────────┐   ┌──────────────────────────┐
│    Agent Runtime          │   │     Background Worker     │
│                          │   │  (Job Queue, Async)       │
│  ┌────────────────────┐  │   │                           │
│  │ Execution Planner  │  │   │  ┌─────────────────────┐  │
│  │ (Rule Engine +     │  │   │  │ Reflection Gen.     │  │
│  │  LLM-assisted)     │  │   │  │ Pattern Detection   │  │
│  └────────┬───────────┘  │   │  │ Library Ingest      │  │
│           │              │   │  │ Memory Consolidation │  │
│           ▼              │   │  └─────────────────────┘  │
│  ┌────────────────────┐  │   └──────────────────────────┘
│  │ Execution Executor │  │
│  │ (Runs plan steps)  │  │
│  └────────┬───────────┘  │
│           │              │
│     ┌─────┼─────┐        │
│     ▼     ▼     ▼        │
│  ┌─────┐ ┌───┐ ┌─────┐  │
│  │Conv │ │Mem│ │Lib  │  │
│  │Agent│ │Agt│ │Agent│  │
│  └─────┘ └───┘ └─────┘  │
│     │     │     │        │
│     └─────┼─────┘        │
│           ▼              │
│  ┌────────────────────┐  │
│  │   RAG Layer        │  │
│  └────────┬───────────┘  │
└───────────┼──────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────┐
│                    Service Layer                          │
├─────────────┬──────────────┬─────────────────────────────┤
│  Memory     │  Knowledge   │   Pattern / Reflection      │
│  Service    │  Service     │   Service                   │
├─────────────┴──────────────┴─────────────────────────────┤
│                    LiteLLM Gateway                        │
│         (Unified LLM Interface — OpenAI / Anthropic /     │
│                 Ollama / etc.)                            │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                    Data Layer                             │
├──────────────────┬──────────────────┬────────────────────┤
│   PostgreSQL     │  Vector Database │    Object Store    │
│ (Relational      │  (pgvector /     │  (Books, Files,    │
│  Data, Sessions, │   Qdrant)        │   Embeddings)      │
│  User State)     │  (Semantic       │                    │
│                  │   Search)        │                    │
└──────────────────┴──────────────────┴────────────────────┘
```

### Component Overview

| Component | Role |
|---|---|
| **Frontend** | User interface for conversations, journaling, library browsing, and reflection review. |
| **API** | Request routing, authentication, session management, and delegation to the Agent Runtime. |
| **Execution Planner** | Determines which agents should participate in a request and in what order. Uses rule-based planning (fast, deterministic) and falls back to LLM-assisted planning when rules are insufficient. |
| **Execution Executor** | Executes the plan produced by the Planner. Invokes agents in order, collects outputs, handles failures, and publishes events. |
| **Worker** | Processes asynchronous jobs: reflection generation, memory consolidation, book ingestion, pattern analysis. |
| **PostgreSQL** | Primary store for user data, session state, structured memories, and metadata. |
| **Vector Database** | Stores embeddings for semantic search over memories, book chunks, and patterns. |
| **LiteLLM** | Unified gateway providing a provider-agnostic interface to multiple LLM backends. |
| **Agents** | Composable reasoning modules that fulfill specific cognitive tasks (conversation, memory extraction, pattern detection, etc.). Agents are stateless and never call each other. |
| **RAG** | Retrieval-Augmented Generation pipeline — retrieves relevant context and injects it into prompts before LLM calls. |
| **Background Jobs** | Queue-based asynchronous processing for expensive or non-blocking operations. |

## 4. Request Lifecycle

```
User Message
     │
     ▼
┌─────────────────┐
│ 1. API receives │
│    message      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. Auth &       │
│    Validate     │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│ 3. Execution Planner        │
│    - Rule engine evaluates  │
│    - Match to Plan Template │
│    - LLM-assisted if needed │
│    - Validate plan          │
│    - Produce Exec Plan      │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ 4. Execution Executor       │
│    - Load context           │
│    - Execute plan steps     │
│    - Invoke agents in order │
│    - Collect outputs        │
│    - Handle failures        │
└────────┬────────────────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────┐
│ Agent  │ │ Agent  │  ... (plan determines
│ Step 1 │ │ Step 2 │      which agents run)
└────┬───┘ └────┬───┘
     │          │
     └────┬─────┘
          │
          ▼
┌─────────────────┐
│ 5. Store        │
│    - Save       │
│      conversation│
│    - Persist    │
│      memories   │
│    - Update     │
│      embeddings │
│    - Publish    │
│      events     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 6. Return       │
│    Response     │
│    to User      │
└─────────────────┘

     ─ ─ ─ Async ─ ─ ─
         │
         ▼
┌──────────────────────┐
│ Worker processes:    │
│ - Pattern detection  │
│ - Reflection gen.    │
│ - Memory             │
│   consolidation      │
│ - Book ingestion     │
└──────────────────────┘
```

### Flow Summary

1. User sends a message via the frontend.
2. API authenticates the request and validates input.
3. The **Execution Planner** evaluates the request. The rule engine checks for known patterns (greeting, knowledge query, reflection request, etc.) and matches to a Plan Template. If confidence is high, the template plan is used directly. If not, the LLM is invoked to produce a custom plan. The plan is validated against agent availability, budget limits, and safety rules.
4. The **Execution Executor** loads the execution context (conversation history, active memories, user profile) and executes each agent step in the plan's order. Each agent receives its specified input, produces output, and returns control to the Executor. The Executor handles failures per the plan's error strategy.
5. After agent execution completes, the system persists new data (conversation history, extracted memories, updated embeddings) and publishes domain events.
6. The response is returned to the user.

Meanwhile, the worker asynchronously runs pattern detection, reflection generation, memory consolidation, and other long-running tasks.

## 5. Agent Responsibilities

### ConversationAgent
Handles the primary chat interaction. Assembles context, constructs prompts, manages conversation flow, and ensures responses stay grounded in retrieved memory and knowledge.

### MemoryAgent
Extracts structured memories from raw conversation. Identifies facts, events, relationships, and changes in user state. Decides what to store as episodic or semantic memory.

### PatternAgent
Analyzes memory over time to detect recurring behavioral, emotional, or cognitive patterns. Produces pattern records that link related memories across sessions.

### LibraryAgent
Manages the ingestion, chunking, embedding, and retrieval of external knowledge sources (books, articles, documents). Ensures retrieved content is properly cited.

### ReflectionAgent
Generates periodic reflections by summarizing recent memories, surfacing patterns, and highlighting changes in thinking or behavior. Produces structured reflection documents.

### BlindSpotAgent
Identifies contradictions, gaps, and inconsistencies in the user's self-model. Surfaces areas the user may be overlooking or avoiding. Designed to provoke gentle, constructive self-inquiry.

## 6. Memory System

Ayeneh uses four distinct memory types, each serving a different cognitive function:

### Episodic Memory
Raw records of user interactions — conversations, journal entries, and events. Episodic memories are temporal and narrative. They answer "what happened and when." Each episode has a timestamp, a summary, and a reference to the original content.

### Semantic Memory
Extracted facts, concepts, and relationships that persist across episodes. Semantic memories are abstracted from specific events. They answer "what does the user believe or know." Examples: user preferences, stated goals, personal rules, relationships between concepts.

### Pattern Memory
Detected recurrences in behavior, emotion, or thought. A pattern links multiple episodic or semantic memories and describes an observed tendency. Patterns answer "what does the user tend to do or feel." Patterns are generated asynchronously by the PatternAgent.

### Reflection Memory
Higher-order observations produced by synthesizing episodic, semantic, and pattern memories. Reflections are generated periodically or on demand. They answer "what has changed and what does it mean." Each reflection references the underlying memories it synthesizes.

All four memory types are stored in PostgreSQL for structured queries and simultaneously embedded in the vector database for semantic retrieval.

## 7. Knowledge System

Ayeneh allows users to import books and documents as a personal knowledge base. The pipeline works as follows:

### Ingestion
1. A book is uploaded or referenced via a supported format (PDF, EPUB, Markdown, plain text).
2. The LibraryAgent extracts the raw text, preserving structure (chapters, headings, paragraphs).
3. The text is split into chunks using a configurable strategy (semantic boundaries, token limits, overlap).
4. Metadata is extracted: title, author, chapter, page number, and section heading.

### Embedding
1. Each chunk is embedded using the configured embedding model via LiteLLM.
2. Chunks and their embeddings are stored in both PostgreSQL (for metadata queries) and the vector database (for semantic search).
3. Embeddings are indexed for efficient approximate nearest-neighbor search.

### Retrieval
1. When a user message is received, the RAG layer embeds the query.
2. The vector database is queried for the most semantically similar chunks.
3. Retrieved chunks are ranked, deduplicated, and filtered by relevance threshold.
4. The top chunks are injected into the prompt as context, with source citations.

### Citation
Every retrieved passage is attributed to its source document, chapter, and section. The response can surface citations so users can verify or explore the original material.

## 8. Future Extensibility

### Adding New Agents
Agents implement a common interface (`Agent` with a single `execute(context)` method). New agents are registered with the Execution Planner, which learns their capabilities and input/output contracts. The Planner can then include the new agent in execution plans when appropriate. No existing agents or pipeline code are modified — the Planner dynamically determines which agents participate in each request.

### Adding New LLM Providers
LiteLLM abstracts provider differences behind a unified interface. Adding a new provider requires only adding it to the LiteLLM configuration — no application code changes.

### Adding New Data Sources
The ingestion pipeline is source-agnostic. A new source type (e.g., web pages, RSS feeds, audio transcripts) requires only a new extractor component that produces the standard chunk format. The embedding, storage, and retrieval logic remains unchanged.

### Adding New Memory Types
New memory types can be introduced by defining a schema and implementing a service that follows the memory service interface. Existing agents can reference the new type without structural changes.

## 9. Non-Goals

- **Ayeneh is not a therapist.** It does not diagnose, treat, or provide mental health care. It is a tool for self-observation, not clinical intervention.
- **Ayeneh is not a spiritual guide.** It does not offer spiritual advice, religious counsel, or metaphysical claims.
- **Ayeneh is not a chatbot.** It is an interactive journal and reflection system. Small talk, jokes, and open-ended chit-chat are not primary use cases.
- **Ayeneh is not a knowledge base.** While it can retrieve and cite external knowledge, its purpose is to support personal reflection, not to answer arbitrary factual questions.
- **Ayeneh is not real-time.** There is no guarantee of sub-second response times. Background processing for reflections and patterns may take minutes.
- **Ayeneh does not replace human relationships.** It is a supplement to, not a substitute for, connection with other people.
- **Ayeneh does not store data in the LLM.** All user data is persisted in the system's own data stores. No user data is used for LLM training.
- **Ayeneh does not implement generic AI assistant features.** It is purpose-built for cognitive companionship and will not pursue feature parity with general-purpose assistants.
