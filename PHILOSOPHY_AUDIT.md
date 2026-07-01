# Ayeneh Philosophy Alignment Audit

## Audit Scope

Every subsystem inspected against the 10 philosophy criteria derived from the architecture document and the Ayeneh philosophy:

> Ayeneh means "mirror." It helps users observe their thinking patterns, track perspective evolution, and engage with external knowledge. It is NOT a therapist, spiritual guide, chatbot, or generic assistant. It does not offer advice, diagnose, or simulate empathy. It acts as a mirror — reflecting back what the user has thought, how they have changed, and what patterns emerge.

---

## 1. Prompt Profiles

**Location:** `prompt/profiles.py` — `CONVERSATION_PROFILE`, `REFLECTION_PROFILE`, `BLIND_SPOT_PROFILE`, `PATTERN_PROFILE`, `MEMORY_PROFILE`, `GOAL_REASONING_PROFILE`

| Criterion | Status | Notes |
|---|---|---|
| Observation over advice | ✅ PASS | Communication style says "Avoid prescriptive advice" and "prefer reflective questions" |
| Distinguishes observation/interpretation/hypothesis/fact | ✅ PASS | Epistemic policy: "Distinguish between known, inferred, and unknown" |
| No guru/therapist/spiritual authority | ⚠️ MINOR | Safety rules say "Never diagnose" but identity says "help users understand their thinking patterns" — slightly directive. Should soften to "reflect thinking patterns back" |
| Increases user autonomy | ✅ PASS | Intervention strategy: "Increase user independence" |
| Epistemic humility | ✅ PASS | Uncertainty policy explicitly mandates hedging language |
| Honest uncertainty | ✅ PASS | "Never present ungrounded reasoning as fact" |
| Reflective questions over answers | ✅ PASS | Communication style: "Use questions to encourage self-observation" |
| Contemplative dialogue | ✅ PASS | Reflective, supportive, curious style |
| Avoids false certainty | ✅ PASS | "When evidence is weak, explicitly express uncertainty" |
| Consistent with philosophy | ⚠️ MINOR | Identity says "help users understand" — slightly directive vs pure mirroring |

**Findings:** 2 minor violations. Identity and philosophy language can be slightly softened.

---

## 2. ConversationAgent

**Location:** `agents/conversation.py`

| Criterion | Status | Notes |
|---|---|---|
| Observation over advice | ⚠️ ISSUE | Fallback prompt says "Help users observe their thinking patterns" — slightly directive. Should say "Reflect back thinking patterns" |
| Distinguishes observation/interpretation/hypothesis/fact | ✅ PASS | Grounding rules enforced, citations required |
| No guru/therapist/spiritual authority | ✅ PASS | Safety rules: "Never diagnose conditions" |
| Increases user autonomy | ✅ PASS | Goal integration encourages self-directed progress |
| Epistemic humility | ✅ PASS | Uncertainty policy injected |
| Honest uncertainty | ✅ PASS | Grounding validation rejects unsupported claims |
| Reflective questions over answers | ⚠️ MINOR | No explicit instruction to prefer questions over answers in the fallback prompt |
| Contemplative dialogue | ⚠️ MINOR | Fallback prompt doesn't mention contemplative style |
| Avoids false certainty | ✅ PASS | Uncertainty policy present |
| Consistent with philosophy | ⚠️ MINOR | Fallback prompt hardcodes "Help users observe" rather than "Reflect back observations" |

**Findings:** 3 minor violations in the fallback prompt at line 231.

---

## 3. ReflectionAgent

**Location:** `agents/reflection.py`

| Criterion | Status | Notes |
|---|---|---|
| Observation over advice | ✅ PASS | Synthesizes longitudinal insights without prescribing actions |
| Distinguishes observation/interpretation/hypothesis/fact | ✅ PASS | Rule-based detection uses structured categories |
| No guru/therapist/spiritual authority | ✅ PASS | Never diagnoses or prescribes |
| Increases user autonomy | ✅ PASS | Reflections present observations for user interpretation |
| Epistemic humility | ✅ PASS | Confidence scoring with uncertainty |
| Honest uncertainty | ✅ PASS | Fallback analysis when LLM unavailable |
| Reflective questions over answers | ⚠️ MINOR | Could explicitly include "what does this mean to you?" framing |
| Contemplative dialogue | ✅ PASS | Designed for longitudinal synthesis |
| Avoids false certainty | ✅ PASS | Confidence scoring present |
| Consistent with philosophy | ✅ PASS | Clean alignment |

**Findings:** 1 minor opportunity for improvement.

---

## 4. BlindSpotAgent

**Location:** `agents/blind_spot.py`

| Criterion | Status | Notes |
|---|---|---|
| Observation over advice | ✅ PASS | Reports observations, never prescribes |
| Distinguishes observation/interpretation/hypothesis/fact | ✅ PASS | Each blind spot includes evidence and alternative interpretations |
| No guru/therapist/spiritual authority | ✅ PASS | Clinical safety boundary enforced |
| Increases user autonomy | ✅ PASS | Reflective questions included |
| Epistemic humility | ✅ PASS | "alternative_interpretations" mandatory |
| Honest uncertainty | ✅ PASS | Evidence-backed only |
| Reflective questions over answers | ✅ PASS | Every blind spot includes reflective questions |
| Contemplative dialogue | ✅ PASS | Observation-focused |
| Avoids false certainty | ✅ PASS | Never labels or diagnoses |
| Consistent with philosophy | ✅ PASS | Clean alignment |

**Findings:** 0 violations. Well-aligned.

---

## 5. PatternAgent

**Location:** `agents/pattern.py`

| Criterion | Status | Notes |
|---|---|---|
| Observation over advice | ✅ PASS | Reports patterns, never prescribes |
| Distinguishes observation/interpretation/hypothesis/fact | ⚠️ MINOR | Patterns are presented as facts rather than observations |
| No guru/therapist/spiritual authority | ✅ PASS | No diagnosis |
| Increases user autonomy | ✅ PASS | Patterns help users see their own behavior |
| Epistemic humility | ✅ PASS | Confidence scoring present |
| Honest uncertainty | ✅ PASS | Pattern strength indicates confidence |
| Reflective questions over answers | ⚠️ MINOR | Could add "what patterns do you notice?" framing |
| Contemplative dialogue | ✅ PASS | Pattern-focused |
| Avoids false certainty | ✅ PASS | Strength-based scoring |
| Consistent with philosophy | ✅ PASS | Clean alignment |

**Findings:** 2 minor opportunities.

---

## 6. MemoryAgent

**Location:** `agents/memory.py`

| Criterion | Status | Notes |
|---|---|---|
| Observation over advice | ✅ PASS | Extracts memories, never advises |
| Distinguishes observation/interpretation/hypothesis/fact | ✅ PASS | Memory types separate episodic from semantic |
| No guru/therapist/spiritual authority | ✅ PASS | Pure extraction engine |
| Increases user autonomy | ✅ PASS | Memory helps users track their own evolution |
| Epistemic humility | ✅ PASS | Confidence scoring per memory |
| Honest uncertainty | ✅ PASS | Low-confidence memories flagged |
| Reflective questions over answers | ✅ PASS | N/A for extraction engine |
| Contemplative dialogue | ✅ PASS | N/A for extraction engine |
| Avoids false certainty | ✅ PASS | Confidence-based filtering |
| Consistent with philosophy | ✅ PASS | Clean alignment |

**Findings:** 0 violations.

---

## 7. Goal Integration

**Location:** `goal/service.py`, `goal/context.py`, `goal/grounding/`

| Criterion | Status | Notes |
|---|---|---|
| Observation over advice | ⚠️ MINOR | Goal creation endpoint could include "what matters to you" framing |
| Distinguishes observation/interpretation/hypothesis/fact | ✅ PASS | Goals are explicit user-stated intentions |
| No guru/therapist/spiritual authority | ✅ PASS | Goals are user-owned, never imposed |
| Increases user autonomy | ✅ PASS | Goal tracking empowers self-direction |
| Epistemic humility | ✅ PASS | Confidence scoring on goals |
| Honest uncertainty | ✅ PASS | Uncertainty expressed through confidence levels |
| Reflective questions over answers | ✅ PASS | Goal grounding returns questions for clarification |
| Contemplative dialogue | ✅ PASS | Goal reviews encourage reflection |
| Avoids false certainty | ✅ PASS | Confidence-based ranking |
| Consistent with philosophy | ✅ PASS | Clean alignment |

**Findings:** 1 minor opportunity.

---

## 8. Reasoning Engine

**Location:** `reasoning/engine.py`, `reasoning/types.py`

| Criterion | Status | Notes |
|---|---|---|
| Observation over advice | ✅ PASS | Generates reasoning summaries, not advice |
| Distinguishes observation/interpretation/hypothesis/fact | ✅ PASS | Hypotheses have supporting/opposing evidence, confidence levels |
| No guru/therapist/spiritual authority | ✅ PASS | Pure reasoning engine, no response generation |
| Increases user autonomy | ✅ PASS | Presents alternatives for user consideration |
| Epistemic humility | ✅ PASS | Uncertainty estimation with explicit reasons |
| Honest uncertainty | ✅ PASS | Missing evidence tracked, confidence calibrated |
| Reflective questions over answers | ✅ PASS | Questions for clarification generated |
| Contemplative dialogue | ✅ PASS | Multi-stage reasoning with alternatives |
| Avoids false certainty | ✅ PASS | Confidence never exceeds 0.95 |
| Consistent with philosophy | ✅ PASS | Clean alignment |

**Findings:** 0 violations.

---

## 9. Prompt Composition

**Location:** `prompt/composition.py`, `prompt/selection.py`, `prompt/grounding.py`

| Criterion | Status | Notes |
|---|---|---|
| Observation over advice | ✅ PASS | Composes prompts from profile policies, not hardcoded advice |
| Distinguishes observation/interpretation/hypothesis/fact | ✅ PASS | Grounding validator checks unsupported claims |
| No guru/therapist/spiritual authority | ✅ PASS | Profile-driven, not hardcoded |
| Increases user autonomy | ✅ PASS | Adaptive selection respects user context |
| Epistemic humility | ✅ PASS | Uncertainty policy injected from profile |
| Honest uncertainty | ✅ PASS | Grounding validation + uncertainty markers |
| Reflective questions over answers | ✅ PASS | Profile communication style drives tone |
| Contemplative dialogue | ✅ PASS | Profile-driven |
| Avoids false certainty | ✅ PASS | Grounding validator rejects unsupported claims |
| Consistent with philosophy | ✅ PASS | Clean alignment |

**Findings:** 0 violations.

---

## 10. Goal Grounding

**Location:** `goal/grounding/service.py`, `goal/grounding/prompt_builder.py`

| Criterion | Status | Notes |
|---|---|---|
| Observation over advice | ✅ PASS | Grounds references, never generates advice |
| Distinguishes observation/interpretation/hypothesis/fact | ✅ PASS | Every reference verified against real Goal objects |
| No guru/therapist/spiritual authority | ✅ PASS | No advice generation |
| Increases user autonomy | ✅ PASS | Prevents hallucinated goals |
| Epistemic humility | ✅ PASS | Rejected goals tracked with reasons |
| Honest uncertainty | ✅ PASS | Grounding score reported |
| Reflective questions over answers | ✅ PASS | N/A for grounding service |
| Contemplative dialogue | ✅ PASS | N/A for grounding service |
| Avoids false certainty | ✅ PASS | Anti-hallucination enforcement |
| Consistent with philosophy | ✅ PASS | Clean alignment |

**Findings:** 0 violations.

---

## 11. Product Profiles

**Location:** `product/profiles/builtins.py`

| Criterion | Status | Notes |
|---|---|---|
| Observation over advice | ✅ PASS | Communication style: "Avoid prescriptive advice" |
| Distinguishes observation/interpretation/hypothesis/fact | ✅ PASS | Epistemic policy present |
| No guru/therapist/spiritual authority | ✅ PASS | "Not a therapist, spiritual guide, chatbot" |
| Increases user autonomy | ✅ PASS | "Increase user independence" |
| Epistemic humility | ✅ PASS | Uncertainty policy present |
| Honest uncertainty | ✅ PASS | "Never present ungrounded reasoning as fact" |
| Reflective questions over answers | ✅ PASS | "Prefer reflective questions over direct answers" |
| Contemplative dialogue | ✅ PASS | Communication style supports it |
| Avoids false certainty | ✅ PASS | Explicit uncertainty policy |
| Consistent with philosophy | ✅ PASS | Well-aligned |

**Findings:** 0 violations.

---

## 12. Retrieval

**Location:** `application/services/retrieval.py`

| Criterion | Status | Notes |
|---|---|---|
| Observation over advice | ✅ PASS | Pure retrieval, no response generation |
| Distinguishes observation/interpretation/hypothesis/fact | ✅ PASS | Confidence scores on all results |
| No guru/therapist/spiritual authority | ✅ PASS | Infrastructure service |
| Increases user autonomy | ✅ PASS | Provides information for user processing |
| Epistemic humility | ✅ PASS | Source attribution included |
| Honest uncertainty | ✅ PASS | Low-confidence items flagged |
| Reflective questions over answers | ✅ PASS | N/A for retrieval |
| Contemplative dialogue | ✅ PASS | N/A for retrieval |
| Avoids false certainty | ✅ PASS | Score-based ranking |
| Consistent with philosophy | ✅ PASS | Clean alignment |

**Findings:** 0 violations.

---

## 13. Evaluation

**Location:** `evaluation/`

| Criterion | Status | Notes |
|---|---|---|
| Observation over advice | ✅ PASS | Evaluates grounding, not advice quality |
| Distinguishes observation/interpretation/hypothesis/fact | ✅ PASS | Grounding scorer validates claims |
| No guru/therapist/spiritual authority | ✅ PASS | No philosophy-specific evaluation |
| Increases user autonomy | ✅ PASS | Measures autonomy-supporting behaviors |
| Epistemic humility | ✅ PASS | Hallucination rate tracked |
| Honest uncertainty | ✅ PASS | Grounding rate measured |
| Reflective questions over answers | ✅ PASS | N/A for evaluation |
| Contemplative dialogue | ✅ PASS | N/A for evaluation |
| Avoids false certainty | ✅ PASS | Hallucination detection |
| Consistent with philosophy | ✅ PASS | Clean alignment |

**Findings:** 0 violations.

---

## 14. Safety

**Location:** `llm/safety.py`, prompt safety rules

| Criterion | Status | Notes |
|---|---|---|
| Observation over advice | ✅ PASS | Safety rules prevent advice-giving |
| Distinguishes observation/interpretation/hypothesis/fact | ✅ PASS | Safety validates grounded claims |
| No guru/therapist/spiritual authority | ✅ PASS | "Never diagnose conditions" enforced |
| Increases user autonomy | ✅ PASS | "Respect user autonomy" |
| Epistemic humility | ✅ PASS | Injection detection prevents manipulation |
| Honest uncertainty | ✅ PASS | Prompt injection patterns detected |
| Reflective questions over answers | ✅ PASS | Safety rules prevent prescriptive responses |
| Contemplative dialogue | ✅ PASS | Safety preserves contemplative tone |
| Avoids false certainty | ✅ PASS | Output validation present |
| Consistent with philosophy | ✅ PASS | Clean alignment |

**Findings:** 0 violations.

---

## 15. Runtime Orchestration

**Location:** `runtime/coordinator.py`, `runtime/executor.py`

| Criterion | Status | Notes |
|---|---|---|
| Observation over advice | ✅ PASS | Runtime orchestrates agents, never generates responses |
| Distinguishes observation/interpretation/hypothesis/fact | ✅ PASS | Agent outputs are structured, not free-form |
| No guru/therapist/spiritual authority | ✅ PASS | Pure infrastructure orchestration |
| Increases user autonomy | ✅ PASS | Enables user-driven workflows |
| Epistemic humility | ✅ PASS | Reasoning engine integrated before composition |
| Honest uncertainty | ✅ PASS | Confidence flows through the pipeline |
| Reflective questions over answers | ✅ PASS | Prompt profiles drive tone |
| Contemplative dialogue | ✅ PASS | Profile-driven behavior |
| Avoids false certainty | ✅ PASS | Grounding enforced at prompt level |
| Consistent with philosophy | ✅ PASS | Clean alignment |

**Findings:** 0 violations.

---

## Summary

| Subsystem | Violations | Action Required |
|---|---|---|
| Prompt Profiles | 2 minor | Soften identity/philosophy language |
| ConversationAgent | 3 minor | Fix fallback prompt to be more mirroring-oriented |
| ReflectionAgent | 1 minor | Consider adding "what does this mean to you?" framing |
| PatternAgent | 2 minor | Minor wording improvements |
| MemoryAgent | 0 | None |
| Goal Integration | 1 minor | Goal creation could use softer framing |
| Reasoning Engine | 0 | None |
| Prompt Composition | 0 | None |
| Goal Grounding | 0 | None |
| Product Profiles | 0 | None |
| Retrieval | 0 | None |
| Evaluation | 0 | None |
| Safety | 0 | None |
| Runtime Orchestration | 0 | None |

**Total: 9 minor violations across 15 subsystems.**

---

## Recommended Changes

### Change 1: Soften ConversationAgent fallback prompt
**File:** `agents/conversation.py` line 231
**Current:** "Help users observe their thinking patterns and engage with knowledge thoughtfully."
**Change to:** "Reflect back the user's thinking patterns and engage with knowledge thoughtfully."

### Change 2: Soften ConversationAgent identity in fallback
**File:** `agents/conversation.py` line 231
**Current:** "You are Ayeneh, a Cognitive Companion. Help users observe..."
**Change to:** "You are Ayeneh, a Cognitive Companion. Reflect back observations..."

### Change 3: Add contemplative framing to fallback
**File:** `agents/conversation.py` line 231
**Current:** Missing contemplative tone
**Change to:** Add "Ask reflective questions. Avoid premature answers."

### Change 4: Soften Ayeneh profile identity
**File:** `product/profiles/builtins.py`
**Current:** "You help users understand their thinking patterns"
**Change to:** "You reflect back users' thinking patterns and help them observe themselves"
