# Agent Boundaries and Modularity

## Status

Accepted

## Context

Ayeneh's cognitive capabilities are distributed across multiple agents (Conversation, Memory, Pattern, Library, Reflection, BlindSpot). Without clear boundaries, agents risk overlapping responsibilities, creating circular dependencies, or becoming monolithic. The system needs a decomposition strategy that keeps agents independent, composable, and individually testable.

## Decision

Each agent owns a single cognitive responsibility and communicates exclusively through the service layer. No agent directly calls another agent. Coordination is managed by the caller (the API or worker) which invokes agents in sequence and passes results between them.

Agent rules:
- An agent receives structured input and returns structured output.
- An agent never calls another agent directly.
- An agent never accesses infrastructure directly (databases, LLMs, etc.) — it uses services.
- An agent has no persistent state; all state lives in the service layer.

The orchestration flow is defined at the application level (API routes or worker jobs), not inside any agent. With the introduction of Dynamic Execution Planning (ADR-007), orchestration is now determined dynamically per request by the Execution Planner, and executed by the Execution Executor. The core agent isolation principles remain unchanged — agents still never call each other directly.

## Consequences

### Positive
- Agents are independently replaceable and testable.
- No circular dependencies between agents.
- Orchestration logic is explicit and visible at the application layer.
- Adding a new agent does not require modifying existing agents.

### Negative
- Coordination logic must be duplicated or abstracted in each orchestration site (API and worker).
- Sequencing multiple agents creates pipeline complexity that must be managed carefully.
- Agent inputs and outputs must be well-structured and versioned to avoid coupling.

## Alternatives Considered

- **Agent chaining (agents calling agents)**: Rejected — creates implicit dependencies, makes testing harder, and leads to tightly coupled agent graphs.
- **Single monolithic agent**: Rejected — violates Single Responsibility Principle, becomes unmaintainable as capabilities grow, and cannot be developed in parallel.
- **Event-driven agent communication**: Rejected — adds indirection without clear benefit at current scale; may be revisited for complex cross-agent workflows.
