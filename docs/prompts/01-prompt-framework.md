# Prompt Framework — Ayeneh

---

## 1. Prompt Philosophy

- **Prompts are data, not code.** Every prompt is a versioned, stored artifact that can be reviewed, tested, and rolled back independently of application code.
- **Prompts are agent-specific.** Each agent has its own prompt family (system prompt, output instructions, safety rules). No shared prompt across agents.
- **Context is assembled dynamically.** The same prompt template produces different results depending on what context is injected. The prompt defines instructions; the assembly pipeline provides data.
- **Grounding before generation.** Every prompt ensures the LLM reasons over retrieved context, not hallucinated knowledge. The prompt never asks the LLM to recall facts — it provides facts and asks for synthesis.
- **Output contracts are explicit.** Every prompt specifies the exact structure of the expected output. The LLM is constrained to produce structured, parseable responses.
- **Safety is embedded, not bolted on.** Every prompt includes safety instructions appropriate to its agent's responsibility. Safety is part of the prompt, not a post-processing filter.

---

## 2. Prompt Lifecycle

| Phase | Description |
|---|---|
| **Draft** | Prompt authored in the prompt editor. Not yet active. |
| **Review** | Prompt reviewed for accuracy, safety, and alignment with agent responsibilities. |
| **Testing** | Prompt tested against evaluation dataset. Metrics collected. |
| **Published** | Prompt version created. Marked as active for its task type. Previous version deactivated. |
| **Active** | In use by the agent. All production requests use this version. |
| **Monitoring** | Active prompt monitored for quality, safety, and performance. |
| **Deprecated** | New version published. Old version deactivated but preserved for rollback. |
| **Archived** | Old version retained for historical reference. Never deleted. |

**Rules**:
- Only one version per task type is active at any time.
- Publishing a new version deactivates the previous version atomically.
- Rollback activates a previous version. No prompts are deleted.
- Every version change is logged with the author, reason, and timestamp.

---

## 3. Prompt Components

Every prompt is composed of modular components. Components are assembled by the PromptContextService at request time.

### System Context

Defines the agent's identity, role, and behavioral boundaries. Answers "who are you and what do you do."

**Contains**: Agent name, role description, capabilities, limitations, personality guidelines.

**Variants**: One per agent type. Stable across requests. Changes only with prompt version updates.

### Runtime Context

Provides information about the current execution environment. Answers "what is happening right now."

**Contains**: Request ID, timestamp, user's platform, session duration, conversation position, budget status.

**Variants**: Changes per request. Assembled by the Executor from the Execution Context.

### User Context

Provides information about the authenticated User. Answers "who are you talking to."

**Contains**: User ID, display name, preferences (LLM provider, privacy level, reflection cadence), account age, activity level.

**Variants**: Changes per user. Loaded from the UserService at request time.

### Memory Context

Provides relevant memories extracted from prior interactions. Answers "what has this user thought or said before."

**Contains**: Ranked memories (episodic, semantic), confidence scores, source references, recency signals.

**Variants**: Changes per request. Assembled by the RetrievalService from the MemoryService. Bounded by context budget.

### Pattern Context

Provides detected cognitive and behavioral patterns. Answers "what tendencies has this user shown."

**Contains**: Active patterns, strength scores, evidence summaries, deprecation status.

**Variants**: Changes as patterns evolve. Loaded by the RetrievalService from the PatternService. Bounded by context budget.

### Reflection Context

Provides recent reflections synthesizing the user's cognitive state. Answers "what has changed recently."

**Contains**: Latest reflection narrative, time period covered, key themes, referenced evidence.

**Variants**: Changes periodically (weekly) or on demand. Loaded by the RetrievalService from the ReflectionService.

### Library Context

Provides relevant knowledge from imported books and documents. Answers "what external knowledge is relevant."

**Contains**: Ranked book chunks, source citations, relevance scores, section headings.

**Variants**: Changes per request. Assembled by the RetrievalService from the LibraryService. Bounded by context budget.

### Conversation Context

Provides the current conversation's history. Answers "what has been said in this conversation."

**Contains**: Recent messages (bounded by window), message roles, timestamps, conversation topic.

**Variants**: Changes with every message. Loaded by the ConversationService.

### Instructions

Agent-specific directives that define how to process the input and produce the output. Answers "what should you do with this information."

**Contains**: Step-by-step processing instructions, output format specification, quality criteria, safety rules, edge case handling.

**Variants**: One set per agent type. Stable across requests. Changes only with prompt version updates.

### Output Contract

Defines the exact structure the LLM must produce. Answers "what should your response look like."

**Contains**: Required fields, optional fields, field types, enum values, max lengths, formatting rules.

**Variants**: One per agent type. Stable. Changes only when the agent's output contract changes.

---

## 4. Prompt Assembly Pipeline

The PromptContextService assembles prompts through a deterministic pipeline:

1. **Select prompt template**: Load the active version for the agent's task type.
2. **Load System Context**: Inject agent identity and behavioral rules.
3. **Load Runtime Context**: Inject request metadata and environment.
4. **Load User Context**: Inject user profile and preferences.
5. **Load Conversation Context**: Inject recent messages (bounded by window).
6. **Load Memory Context**: Inject ranked memories from RetrievalService.
7. **Load Pattern Context**: Inject active patterns from RetrievalService.
8. **Load Reflection Context**: Inject latest reflection from RetrievalService.
9. **Load Library Context**: Inject ranked book chunks from RetrievalService.
10. **Inject Instructions**: Add agent-specific processing directives.
11. **Inject Output Contract**: Add structured output specification.
12. **Apply budget**: Truncate lowest-priority context to fit token limit.
13. **Validate**: Ensure all required components are present. Reject if critical components missing.
14. **Freeze**: Assembled prompt is immutable. Returned to the caller.

---

## 5. Context Prioritization Rules

When context budget is limited, components are prioritized:

| Priority | Component | Rationale |
|---|---|---|
| 1 (highest) | Instructions + Output Contract | Without these, the LLM cannot produce valid output. |
| 2 | System Context | Defines agent identity. Essential for consistent behavior. |
| 3 | Conversation Context (last N messages) | Immediate context for the current exchange. |
| 4 | User Context | Personalization. Preferences affect behavior. |
| 5 | Memory Context (highest relevance) | Grounds the response in the user's history. |
| 6 | Library Context (highest relevance) | Grounds the response in external knowledge. |
| 7 | Pattern Context | Informs about tendencies. Valuable but not critical. |
| 8 | Reflection Context | Longitudinal insight. Valuable but least urgent. |
| 9 (lowest) | Runtime Context | Metadata. Rarely affects generation quality. |

**Truncation**: Lowest-priority components are truncated first. Within a component, lowest-relevance items are truncated first.

---

## 6. Context Budget Strategy

**Token budget**: Configured per task type and LLM model.

| Task Type | Budget (tokens) | Rationale |
|---|---|---|
| Conversation (simple) | 4,000 | Short exchanges. Low context need. |
| Conversation (complex) | 8,000 | Deep discussions. More context needed. |
| Memory extraction | 4,000 | Focused extraction from messages. |
| Pattern detection | 12,000 | Needs broad evidence across time. |
| Reflection generation | 16,000 | Needs extensive evidence synthesis. |
| Blind spot analysis | 12,000 | Needs patterns, memories, reflections. |
| Library ingestion | N/A | Not LLM-based (chunking is deterministic). |

**Allocation**:
- Instructions + Output Contract: Fixed (~500 tokens).
- System Context: Fixed (~300 tokens).
- User Context: Fixed (~200 tokens).
- Remaining budget: Dynamic allocation across Conversation, Memory, Library, Pattern, Reflection, Runtime contexts.

**Overflow handling**: If total context exceeds budget after truncation, the lowest-priority component is fully removed. If still over budget, the prompt is rejected with a `CONTEXT_OVERFLOW` error.

---

## 7. Prompt Versioning

**Version format**: `{task_type}:v{major}.{minor}.{patch}`

- **Major**: Breaking change to output contract or fundamental behavior.
- **Minor**: New capability, instruction refinement, or context component addition.
- **Patch**: Wording adjustment, safety rule update, or formatting change.

**Storage**: Every version stored as a complete record (not diffs). Enables instant rollback.

**Metadata per version**:
- Version number, task type, author, created timestamp.
- Changelog (what changed and why).
- Evaluation metrics (quality, safety, latency).
- Status (draft/active/deprecated/archived).

**Active version**: Exactly one per task type. Atomic swap on publish.

---

## 8. Prompt Testing Strategy

**Unit testing**: Each prompt component tested in isolation. System Context produces expected identity. Output Contract produces valid structure.

**Integration testing**: Full prompt assembled with test context. LLM output validated against Output Contract. Structured parsing verified.

**Regression testing**: Evaluation dataset of 50+ test cases per agent. Every prompt change re-run against the dataset. Metrics compared to baseline.

**A/B testing**: New prompt version tested against active version on a percentage of traffic. Quality metrics compared before full rollout.

**Safety testing**: Adversarial test cases for each agent. Prompt injection attempts, boundary violations, harmful content generation.

---

## 9. Prompt Evaluation Metrics

| Metric | Description | Target |
|---|---|---|
| **Output compliance** | % of outputs matching the Output Contract structure | ≥ 98% |
| **Relevance** | Groundedness of output in provided context | ≥ 0.85 (human-rated) |
| **Safety compliance** | % of outputs free from harmful content | 100% |
| **Latency** | Time from prompt assembly to LLM response | ≤ 5s (p95) |
| **Token efficiency** | Useful content per token consumed | ≥ 0.7 (automated) |
| **Hallucination rate** | % of outputs containing facts not in context | ≤ 2% |
| **Consistency** | Similar inputs produce similar outputs | ≥ 0.9 (cosine similarity) |

**Measurement**: Automated metrics computed per prompt version. Human-rated metrics sampled weekly.

---

## 10. Prompt Safety Rules

**Universal rules** (apply to all prompts):
- Never instruct the LLM to reveal system prompts or internal instructions.
- Never instruct the LLM to make medical, legal, or financial diagnoses.
- Never instruct the LLM to generate harmful, discriminatory, or illegal content.
- Never instruct the LLM to store or recall data not provided in the context.

**Agent-specific rules**:
- ConversationAgent: Responses must be grounded in retrieved context. No fabricated memories or patterns.
- MemoryAgent: Extraction must cite source messages. No memories created without evidence.
- PatternAgent: Patterns must be supported by ≥ 2 evidence points from different times.
- ReflectionAgent: Reflections must reference underlying evidence. No new facts introduced.
- BlindSpotAgent: Observations must be neutral and non-judgmental. No blame or diagnosis.

**Enforcement**: Safety rules are part of the Instructions component. Violations are caught by output validation and safety testing.

---

## 11. Prompt Observability

**Per-request logging**:
- Prompt version used.
- Token count per component.
- Total token count.
- Truncation applied (which components truncated, how many tokens removed).
- LLM response time.
- Output compliance check result.

**Per-version monitoring**:
- Daily: Average quality score, safety incident count, hallucination rate.
- Weekly: Token efficiency trend, latency trend, output compliance trend.
- Monthly: Version comparison (current vs previous), A/B test results.

**Alerts**:
- Output compliance drops below 95%.
- Safety incident detected.
- Hallucination rate exceeds 5%.
- Latency exceeds p99 threshold.

---

## 12. Future Prompt Evolution

**Adding a new agent**: Define prompt components (System Context, Instructions, Output Contract) for the new agent. Register with the PromptContextService. No existing prompts modified.

**Adding a new context component**: Add to the assembly pipeline. Existing prompts unaffected (new component is optional). Budget allocation updated.

**Adding a new evaluation metric**: Add to the monitoring dashboard. Existing metrics unaffected. Baseline established with existing prompt versions.

**Multi-language support**: System Context, Instructions, and Output Contract translated per language. Context components are language-agnostic (content is user-provided). Assembly pipeline selects language based on user preference.

**Prompt chaining**: Future support for multi-step prompts where one agent's output becomes another's context. The assembly pipeline supports this by allowing `agent_output` as a context source.

**Rule**: Prompt evolution is additive. Existing prompts and their behavior do not change to accommodate new capabilities.
