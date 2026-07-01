"""Goal-aware evaluation benchmarks for all cognitive agents."""

from ayeneh.evaluation.core import EvalCase


# ── Conversation + Goals ──

CONVERSATION_GOAL_BENCHMARKS: list[EvalCase] = [
    EvalCase(
        case_id="conv-goal-001",
        agent_type="conversation",
        input_data={
            "message": "How is my Python learning going?",
            "goals": [{"title": "Learn Python", "progress": 0.6, "priority": "high"}],
        },
        expected_output={
            "response_text": "",
            "keywords": ["python", "learn", "progress"],
            "referenced_goals": ["Learn Python"],
        },
        context={"source_texts": ["User wants to learn Python. Goal at 60% progress."]},
        tags=["goal-aware", "progress-reference"],
        difficulty="standard",
    ),
    EvalCase(
        case_id="conv-goal-002",
        agent_type="conversation",
        input_data={
            "message": "I want to give up on learning Python",
            "goals": [{"title": "Learn Python", "progress": 0.6, "priority": "high"}],
        },
        expected_output={
            "response_text": "",
            "keywords": ["python", "goal", "consider"],
            "referenced_goals": [],
        },
        context={"source_texts": ["User has a goal to learn Python at 60% progress."]},
        tags=["goal-aware", "encouragement"],
        difficulty="standard",
    ),
    EvalCase(
        case_id="conv-goal-003",
        agent_type="conversation",
        input_data={
            "message": "What should I focus on today?",
            "goals": [
                {"title": "Finish report", "progress": 0.3, "priority": "critical", "deadline": "tomorrow"},
                {"title": "Exercise", "progress": 0.7, "priority": "medium"},
            ],
        },
        expected_output={
            "response_text": "",
            "keywords": ["report", "focus", "priority"],
            "referenced_goals": ["Finish report"],
        },
        context={"source_texts": ["User has urgent deadline tomorrow."]},
        tags=["goal-aware", "prioritization"],
        difficulty="standard",
    ),
]

# ── Pattern + Goals ──

PATTERN_GOAL_BENCHMARKS: list[EvalCase] = [
    EvalCase(
        case_id="pat-goal-001",
        agent_type="pattern",
        input_data={
            "memories": ["Started 5 projects, finished none", "Always starting new things"],
            "goals": [
                {"title": "Project A", "progress": 0.1},
                {"title": "Project B", "progress": 0.0},
                {"title": "Project C", "progress": 0.05},
            ],
        },
        expected_output={
            "expected_patterns": [
                {"description": "Goal switching pattern", "category": "goal_switching"}
            ]
        },
        context={},
        tags=["goal-aware", "goal-switching"],
        difficulty="standard",
    ),
    EvalCase(
        case_id="pat-goal-002",
        agent_type="pattern",
        input_data={
            "memories": ["I keep postponing my reading goal"],
            "goals": [
                {"title": "Read 12 books", "progress": 0.2, "deadline": "end of year"},
            ],
        },
        expected_output={
            "expected_patterns": [
                {"description": "Goal procrastination pattern", "category": "procrastination"}
            ]
        },
        context={},
        tags=["goal-aware", "procrastination"],
        difficulty="standard",
    ),
]

# ── Reflection + Goals ──

REFLECTION_GOAL_BENCHMARKS: list[EvalCase] = [
    EvalCase(
        case_id="ref-goal-001",
        agent_type="reflection",
        input_data={
            "memories": ["Value honesty but often avoid difficult conversations"],
            "patterns": [{"description": "Conflict avoidance"}],
            "goals": [
                {"title": "Improve communication", "progress": 0.3, "priority": "high"},
                {"title": "Build confidence", "progress": 0.5, "priority": "medium"},
            ],
        },
        expected_output={
            "narrative": "",
            "keywords": ["communication", "confidence", "honesty", "progress"],
            "referenced_goals": ["Improve communication", "Build confidence"],
        },
        context={"source_texts": ["Goal-progress gap detected."]},
        tags=["goal-aware", "goal-alignment"],
        difficulty="standard",
    ),
]

# ── Blind Spot + Goals ──

BLIND_SPOT_GOAL_BENCHMARKS: list[EvalCase] = [
    EvalCase(
        case_id="bs-goal-001",
        agent_type="blind_spot",
        input_data={
            "memories": ["I want to write a book", "I haven't written in months"],
            "goals": [
                {"title": "Write a novel", "progress": 0.05, "priority": "high"},
            ],
        },
        expected_output={
            "expected_observations": [
                {"content": "Goal inconsistency: stated desire vs. inaction", "type": "goal_inconsistency"}
            ]
        },
        context={"source_texts": ["User claims to want to write but shows no progress."]},
        tags=["goal-aware", "goal-inconsistency"],
        difficulty="standard",
    ),
]


def get_goal_benchmarks(agent_type: str) -> list[EvalCase]:
    all_benchmarks = {
        "conversation": CONVERSATION_GOAL_BENCHMARKS,
        "pattern": PATTERN_GOAL_BENCHMARKS,
        "reflection": REFLECTION_GOAL_BENCHMARKS,
        "blind_spot": BLIND_SPOT_GOAL_BENCHMARKS,
    }
    return all_benchmarks.get(agent_type, [])


def get_all_goal_benchmarks() -> list[EvalCase]:
    return (
        CONVERSATION_GOAL_BENCHMARKS + PATTERN_GOAL_BENCHMARKS
        + REFLECTION_GOAL_BENCHMARKS + BLIND_SPOT_GOAL_BENCHMARKS
    )
