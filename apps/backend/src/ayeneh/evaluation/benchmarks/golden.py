"""Golden benchmark datasets for each cognitive agent."""

from __future__ import annotations

from ayeneh.evaluation.core import EvalCase


# ════════════════════════════════════════════════════════════════════════
# Conversation benchmarks
# ════════════════════════════════════════════════════════════════════════

CONVERSATION_BENCHMARKS: list[EvalCase] = [
    EvalCase(
        case_id="conv-001",
        agent_type="conversation",
        input_data={"message": "How are you doing today?", "history": []},
        expected_output={
            "response_text": "",
            "keywords": ["ayeneh", "companion"],
        },
        context={"source_texts": ["Ayeneh is a cognitive companion."]},
        tags=["greeting", "basic"],
        difficulty="easy",
    ),
    EvalCase(
        case_id="conv-002",
        agent_type="conversation",
        input_data={
            "message": "I feel overwhelmed with work lately",
            "history": [],
        },
        expected_output={
            "response_text": "",
            "keywords": ["overwhelm", "work"],
        },
        context={"source_texts": ["Feeling overwhelmed is common during high-demand periods."]},
        tags=["emotional", "empathy"],
        difficulty="standard",
    ),
    EvalCase(
        case_id="conv-003",
        agent_type="conversation",
        input_data={
            "message": "What do you know about cognitive behavioral therapy?",
            "history": [],
        },
        expected_output={
            "response_text": "",
            "keywords": ["cognitive", "behavioral", "therapy"],
        },
        context={
            "source_texts": [
                "Cognitive behavioral therapy (CBT) is a structured, "
                "time-limited psychotherapy that aims to solve current problems."
            ]
        },
        tags=["knowledge", "grounded"],
        difficulty="standard",
    ),
]


# ════════════════════════════════════════════════════════════════════════
# Memory extraction benchmarks
# ════════════════════════════════════════════════════════════════════════

MEMORY_BENCHMARKS: list[EvalCase] = [
    EvalCase(
        case_id="mem-001",
        agent_type="memory",
        input_data={"message": "I always procrastinate on important deadlines"},
        expected_output={
            "expected_memories": [
                {"content": "I always procrastinate on important deadlines", "type": "semantic"}
            ]
        },
        context={},
        tags=["behavioral", "pattern"],
        difficulty="easy",
    ),
    EvalCase(
        case_id="mem-002",
        agent_type="memory",
        input_data={"message": "Yesterday I felt really anxious about the presentation"},
        expected_output={
            "expected_memories": [
                {"content": "felt anxious about the presentation", "type": "episodic"}
            ]
        },
        context={},
        tags=["emotional", "episodic"],
        difficulty="standard",
    ),
    EvalCase(
        case_id="mem-003",
        agent_type="memory",
        input_data={"message": "I believe honesty is the most important value"},
        expected_output={
            "expected_memories": [
                {"content": "honesty is the most important value", "type": "semantic"}
            ]
        },
        context={},
        tags=["belief", "value"],
        difficulty="easy",
    ),
]


# ════════════════════════════════════════════════════════════════════════
# Pattern detection benchmarks
# ════════════════════════════════════════════════════════════════════════

PATTERN_BENCHMARKS: list[EvalCase] = [
    EvalCase(
        case_id="pat-001",
        agent_type="pattern",
        input_data={
            "memories": [
                "I always avoid difficult conversations",
                "I tend to procrastinate when tasks are hard",
                "I usually give up when facing challenges",
            ]
        },
        expected_output={
            "expected_patterns": [
                {"description": "Avoidance tendency", "category": "avoidance"}
            ]
        },
        context={},
        tags=["avoidance", "behavioral"],
        difficulty="easy",
    ),
    EvalCase(
        case_id="pat-002",
        agent_type="pattern",
        input_data={
            "memories": [
                "I need everything to be perfect before I start",
                "I spend hours on small details",
                "I can't submit work unless it's flawless",
            ]
        },
        expected_output={
            "expected_patterns": [
                {"description": "Perfectionism tendency", "category": "perfectionism"}
            ]
        },
        context={},
        tags=["perfectionism", "behavioral"],
        difficulty="standard",
    ),
]


# ════════════════════════════════════════════════════════════════════════
# Reflection benchmarks
# ════════════════════════════════════════════════════════════════════════

REFLECTION_BENCHMARKS: list[EvalCase] = [
    EvalCase(
        case_id="ref-001",
        agent_type="reflection",
        input_data={
            "memories": [
                "I value honesty but I often avoid telling the truth when it's uncomfortable",
                "I believe in personal growth",
            ],
            "patterns": [{"description": "Conflict avoidance"}],
        },
        expected_output={
            "narrative": "",
            "keywords": ["honesty", "conflict", "growth"],
        },
        context={
            "source_texts": [
                "The user values honesty but avoids uncomfortable truths.",
                "There is a conflict between stated values and behavior."
            ]
        },
        tags=["self-reflection", "conflict"],
        difficulty="standard",
    ),
]


# ════════════════════════════════════════════════════════════════════════
# Blind spot detection benchmarks
# ════════════════════════════════════════════════════════════════════════

BLIND_SPOT_BENCHMARKS: list[EvalCase] = [
    EvalCase(
        case_id="bs-001",
        agent_type="blind_spot",
        input_data={
            "memories": [
                "I always put others first",
                "I feel exhausted and resentful most days",
            ],
            "patterns": [{"description": "People-pleasing"}],
        },
        expected_output={
            "expected_observations": [
                {
                    "content": "Contradiction between selflessness claim and exhaustion",
                    "type": "contradiction",
                }
            ]
        },
        context={
            "source_texts": [
                "User claims to always put others first but reports exhaustion and resentment."
            ]
        },
        tags=["contradiction", "self-awareness"],
        difficulty="standard",
    ),
    EvalCase(
        case_id="bs-002",
        agent_type="blind_spot",
        input_data={
            "memories": [
                "I never procrastinate",
                "I started 3 projects this month and finished none",
            ],
            "patterns": [],
        },
        expected_output={
            "expected_observations": [
                {
                    "content": "Claim of no procrastination contradicted by project abandonment",
                    "type": "self-defeating",
                }
            ]
        },
        context={
            "source_texts": [
                "User claims never to procrastinate but has abandoned multiple projects."
            ]
        },
        tags=["self-defeating", "contradiction"],
        difficulty="standard",
    ),
]


def get_benchmarks(agent_type: str) -> list[EvalCase]:
    """Return all benchmark cases for a given agent type."""
    all_benchmarks = {
        "conversation": CONVERSATION_BENCHMARKS,
        "memory": MEMORY_BENCHMARKS,
        "pattern": PATTERN_BENCHMARKS,
        "reflection": REFLECTION_BENCHMARKS,
        "blind_spot": BLIND_SPOT_BENCHMARKS,
    }
    return all_benchmarks.get(agent_type, [])


def get_all_benchmarks() -> list[EvalCase]:
    return (
        CONVERSATION_BENCHMARKS + MEMORY_BENCHMARKS + PATTERN_BENCHMARKS
        + REFLECTION_BENCHMARKS + BLIND_SPOT_BENCHMARKS
    )
