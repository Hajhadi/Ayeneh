"""Ayeneh Cognitive Architecture (COG-00 through COG-16).

A longitudinal cognitive modeling system that continuously constructs
an increasingly accurate, evidence-based, temporally evolving model
of a person's cognition.

Architecture layers:
  COG-01: Conversation Understanding
  COG-02: Evidence Extraction
  COG-03: Cognitive Evidence Model (base types)
  COG-04: Personal Knowledge Extraction
  COG-05: Narrative Extraction
  COG-06: Belief Modeling
  COG-07: Value Modeling
  COG-08: Goal Modeling
  COG-09: Identity Graph
  COG-10: Decision Architecture
  COG-11: Behavioral Pattern
  COG-12: Reflection Engine
  COG-13: Cognitive Trajectory
  COG-14: Predictive Cognitive
  COG-15: Reality Calibration
  COG-16: Meta-Cognition
"""

from ayeneh.cog.base import CognitiveObject, EvidenceRef, TemporalMetadata, Revision
from ayeneh.cog.pipeline.graph import CognitiveGraph
from ayeneh.cog.pipeline.orchestrator import CognitivePipelineOrchestrator

__all__ = [
    "CognitiveObject",
    "CognitiveGraph",
    "CognitivePipelineOrchestrator",
    "EvidenceRef",
    "Revision",
    "TemporalMetadata",
]
