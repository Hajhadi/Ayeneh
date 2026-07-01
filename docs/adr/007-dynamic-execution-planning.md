# Dynamic Execution Planning

## Status

Accepted

## Context

The current Agent Runtime operates as a fixed sequential pipeline. Every request — regardless of whether the User is asking a simple question, importing a book, or requesting a reflection — flows through the same ordered sequence of agent invocations. This creates three problems:

1. **Unnecessary work**: A User asking "what did I write about anxiety last week?" does not need the BlindSpotAgent or the PatternAgent to run. The current runtime invokes them anyway, wasting LLM calls and adding latency.
2. **Rigid ordering**: The fixed sequence assumes a universal optimal order. In reality, the optimal order depends on the request. A reflection request should prioritize the ReflectionAgent; a knowledge question should prioritize the LibraryAgent; a simple greeting needs only the ConversationAgent.
3. **Scaling friction**: Adding a new agent to the pipeline requires modifying the fixed sequence. Every new agent increases the cost of every request, even when it is irrelevant.

The system needs a runtime that decides *what* to execute and *in what order* based on the specific request, rather than executing a hardcoded pipeline for every request.

## Decision

Introduce **Dynamic Execution Planning** into the Agent Runtime. The runtime is decomposed into two new conceptual components:

### Execution Planner

The Execution Planner is responsible for determining which agents should participate in processing a given request, and in what order. It produces an **Execution Plan** — a structured description of the work to be done.

The Planner uses a **Hybrid Planning Strategy**:

**Stage 1 — Rule-based planning**: A deterministic rule engine evaluates the request against a set of known patterns. Rules match on request characteristics — message content type, conversation state, user intent signals, presence of uploaded books, recency of last reflection — and produce a candidate Execution Plan. The rule engine is fast, predictable, and requires no LLM call.

**Stage 2 — LLM-assisted planning** (conditional): The LLM is invoked only when the rule engine cannot confidently determine the Execution Plan. This occurs when:
- The request does not match any known pattern.
- The request matches multiple patterns with conflicting agent selections.
- The request is ambiguous — it could be a simple question or a deep reflection trigger.
- The system's confidence in the rule-based plan falls below a configurable threshold.

When LLM-assisted planning is triggered, the LLM receives the request, conversation context, and a description of available agents and their capabilities. It returns a structured Execution Plan — which agents to invoke, in what order, with what input parameters. The LLM's plan is validated against constraints (agent availability, budget limits, safety rules) before execution.

**Stage 3 — Plan validation**: The Execution Planner validates the plan against system constraints:
- Agent availability (is the agent configured and operational?).
- Budget limits (how many LLM calls are permitted for this request?).
- Safety rules (certain agents may be restricted in certain contexts).
- User preferences (the User may disable certain agents or workflows).

### Execution Executor

The Execution Executor is responsible for executing the generated Execution Plan. It receives a validated plan and:

1. Invokes each agent in the specified order.
2. Passes the specified input to each agent.
3. Collects each agent's output.
4. Handles failures according to the plan's error strategy.
5. Publishes domain events as agents complete.
6. Returns the final response.

The Executor does not decide what to execute — it only executes what the Planner produced. It is a dumb runner with smart error handling.

### Execution Plan

An Execution Plan is a structured artifact produced by the Planner and consumed by the Executor. It describes:

- **Agent steps**: An ordered list of agent invocations. Each step specifies the agent, its input type, and its expected output type.
- **Input bindings**: For each step, which data from the execution context or previous steps should be passed as input.
- **Error strategy**: For each step, how to handle failure — retry, skip, abort, or degrade.
- **Budget**: The maximum number of LLM calls and total processing time allowed.
- **Metadata**: The planning strategy used (rule-based or LLM-assisted), confidence score, and planning timestamp.

The Execution Plan is a transient, request-scoped artifact. It is created per-request and discarded after execution.

### Plan Templates

To avoid the overhead of LLM-assisted planning for common request types, the system maintains **Plan Templates** — pre-defined Execution Plans for known request patterns. Examples:

| Template | Trigger | Agents Involved |
|---|---|---|
| **Simple Conversation** | Greeting, simple question, small talk | ConversationAgent, MemoryAgent |
| **Knowledge Query** | Question answerable from Library content | ConversationAgent, MemoryAgent, LibraryAgent |
| **Deep Reflection** | Request for insight, self-observation prompt | ConversationAgent, MemoryAgent, ReflectionAgent, BlindSpotAgent |
| **Pattern Review** | Request to see patterns or tendencies | ConversationAgent, PatternAgent |
| **Library Import** | File upload or book reference | LibraryAgent |

The rule engine matches requests to templates. When a match is found with high confidence, the template's plan is used directly — no LLM call needed.

### Relationship to ADR-003 (Agent Boundaries)

This decision does not contradict ADR-003. The core agent isolation principles remain:

- Agents never call other agents directly. (Still true — the Executor invokes agents, not other agents.)
- Agents are stateless. (Still true — the Execution Plan provides all necessary context.)
- Agents access infrastructure through services. (Still true — unchanged.)
- Orchestration lives at the application layer. (Refined — orchestration now lives in the Execution Planner and Executor, which are application-layer components.)

The change is that orchestration is no longer hardcoded — it is dynamically determined per request.

## Consequences

### Positive

- **Reduced latency**: Requests that need only one or two agents skip unnecessary invocations.
- **Reduced cost**: Fewer LLM calls per request when the rule engine can determine the plan.
- **Improved extensibility**: Adding a new agent requires registering it with the Planner — no changes to existing pipeline code.
- **Better error isolation**: A failure in one agent does not cascade to agents that were not part of the plan.
- **Adaptive behavior**: The system can adjust its processing strategy based on request characteristics.

### Negative

- **Increased complexity**: The runtime now has two components (Planner and Executor) instead of one fixed sequence.
- **Planning overhead**: LLM-assisted planning adds latency and cost when triggered. This is mitigated by the rule engine handling common cases.
- **Plan validation**: The system must validate plans against constraints, adding a new failure mode (invalid plan).
- **Debugging difficulty**: Tracing which plan was executed for a given request requires logging the plan and its source (rule-based vs. LLM-assisted).

### Mitigations

- Plan Templates handle the majority of requests without LLM overhead.
- LLM-assisted planning is bounded by configurable confidence thresholds — it is triggered only when the rule engine is insufficient.
- Plan validation is deterministic and fast — it checks agent availability and budget, not domain logic.
- Full plan logging ensures reproducibility and debugging.

## Alternatives Considered

- **Keep fixed sequential pipeline**: Rejected — wastes resources, scales poorly, and cannot adapt to request characteristics.
- **Full LLM planning (no rules)**: Rejected — adds unnecessary latency and cost for common request patterns that can be handled deterministically.
- **Agent self-selection (agents decide whether to run)**: Rejected — violates the principle that agents are stateless and do not know about each other. Would create implicit coupling.
- **Event-driven agent triggers**: Rejected — adds indirection and makes the execution flow harder to reason about. May be revisited for complex cross-agent workflows.
