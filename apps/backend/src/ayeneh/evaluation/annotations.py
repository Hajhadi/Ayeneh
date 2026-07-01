"""Human annotation support for evaluation ground-truth creation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class HumanAnnotation:
    annotation_id: str
    case_id: str
    annotator_id: str
    rating: float
    label: str
    comment: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class AnnotationStore:
    """Stores human annotations for evaluation cases."""

    def __init__(self) -> None:
        self._annotations: dict[str, list[HumanAnnotation]] = {}

    def add_annotation(self, annotation: HumanAnnotation) -> None:
        self._annotations.setdefault(annotation.case_id, []).append(annotation)
        logger.info(
            "annotation_added",
            case_id=annotation.case_id,
            annotator=annotation.annotator_id,
            rating=annotation.rating,
        )

    def get_annotations(self, case_id: str) -> list[HumanAnnotation]:
        return self._annotations.get(case_id, [])

    def get_inter_annotator_agreement(self, case_id: str) -> float:
        annotations = self.get_annotations(case_id)
        if len(annotations) < 2:
            return 1.0
        ratings = [a.rating for a in annotations]
        mean = sum(ratings) / len(ratings)
        variance = sum((r - mean) ** 2 for r in ratings) / len(ratings)
        return max(0.0, 1.0 - variance)

    def get_annotation_summary(self) -> dict[str, Any]:
        total = sum(len(anns) for anns in self._annotations.values())
        cases_annotated = len(self._annotations)
        avg_rating = 0.0
        if total > 0:
            all_ratings = [a.rating for anns in self._annotations.values() for a in anns]
            avg_rating = sum(all_ratings) / len(all_ratings)
        return {
            "total_annotations": total,
            "cases_annotated": cases_annotated,
            "average_rating": avg_rating,
        }
