"""INF-03 Multi-Hop Reasoning module."""

from ayeneh.inf.multihop.engine import MultiHopReasoningEngine
from ayeneh.inf.multihop.loops import NarrativeLoopDetector
from ayeneh.inf.multihop.types import (
    HOP_TYPES,
    REASONING_DIMENSIONS,
    LOOP_TYPES,
    HiddenPattern,
    MultiHopChain,
    MultiHopResult,
    NarrativeLoop,
    ReasoningHop,
)

__all__ = [
    'HOP_TYPES',
    'REASONING_DIMENSIONS',
    'LOOP_TYPES',
    'HiddenPattern',
    'MultiHopChain',
    'MultiHopReasoningEngine',
    'MultiHopResult',
    'NarrativeLoop',
    'NarrativeLoopDetector',
    'ReasoningHop',
]
