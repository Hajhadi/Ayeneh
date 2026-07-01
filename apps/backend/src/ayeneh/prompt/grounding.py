"""Grounding rules and uncertainty policy for cognitive prompts."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ayeneh.prompt.types import GroundingResult


class GroundingValidator:
    """Validates that generated text is grounded in provided sources."""

    UNCERTAINTY_MARKERS = [
        "i think", "i believe", "it seems", "based on available",
        "this is uncertain", "i'm not sure", "possibly", "might be",
        "it appears", "from what i can see",
    ]

    ASSERTION_PATTERNS = [
        r"you (always|never|definitely|certainly)",
        r"you (must|should|need to)",
        r"the (data|evidence|research) (clearly|definitely|proves)",
    ]

    def validate(
        self,
        generated_text: str,
        sources: list[dict[str, Any]],
        *,
        require_citations: bool = True,
    ) -> GroundingResult:
        result = GroundingResult()
        source_content = " ".join(str(s.get("content", s.get("excerpt", ""))) for s in sources)

        claims = self._extract_factual_claims(generated_text)
        result.total_claims = len(claims)

        supported = 0
        for claim in claims:
            if self._is_supported(claim, source_content):
                supported += 1
            else:
                result.unsupported_claims.append(claim)

        if result.total_claims > 0:
            result.grounding_score = supported / result.total_claims
        result.is_grounded = len(result.unsupported_claims) == 0 or result.grounding_score >= 0.5
        result.citations_used = len(re.findall(r'\[[\w:]+\]', generated_text))
        return result

    def check_uncertainty(self, text: str) -> float:
        text_lower = text.lower()
        markers_found = sum(1 for m in self.UNCERTAINTY_MARKERS if m in text_lower)
        assertions_found = sum(1 for p in self.ASSERTION_PATTERNS if re.search(p, text_lower))
        if assertions_found > 0 and markers_found == 0:
            return 0.3
        if markers_found > 0:
            return 0.8
        return 0.6

    def _extract_factual_claims(self, text: str) -> list[str]:
        sentences = re.split(r'[.!?]+', text)
        claims = []
        for s in sentences:
            s = s.strip()
            if len(s.split()) >= 4 and not any(m in s.lower() for m in self.UNCERTAINTY_MARKERS):
                claims.append(s)
        return claims[:10]

    def _is_supported(self, claim: str, source_content: str) -> bool:
        claim_words = set(claim.lower().split()) - {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to", "for"}
        source_words = set(source_content.lower().split())
        if not claim_words:
            return True
        overlap = len(claim_words & source_words)
        return overlap / len(claim_words) >= 0.3
