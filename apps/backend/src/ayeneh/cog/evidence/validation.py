"""Evidence Validator for the Ayeneh COG architecture (COG-02).

Validates evidence objects against mandatory attribute requirements,
confidence range checks, provenance completeness, and temporal consistency.
"""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALIDATION_STATUSES: tuple[str, ...] = ('pass', 'pass_with_warning', 'requires_review', 'fail')

MANDATORY_ATTRIBUTES: tuple[str, ...] = (
    'category',
    'epistemic_classification',
    'original_text',
    'speaker',
    'confidence',
    'provenance',
)

CONFIDENCE_RANGE: tuple[float, float] = (0.0, 1.0)

MIN_CONFIDENCE: float = 0.0
MAX_CONFIDENCE: float = 1.0

# Maximum number of warnings before escalating to 'requires_review'
MAX_WARNINGS_FOR_PASS: int = 2


class EvidenceValidator:
    """Validate evidence objects against the COG-02 schema.

    Returns a status of ``pass``, ``pass_with_warning``, ``requires_review``,
    or ``fail`` together with a list of human-readable warning messages.
    """

    VALIDATION_STATUSES = list(VALIDATION_STATUSES)
    MANDATORY_ATTRIBUTES = list(MANDATORY_ATTRIBUTES)

    def validate(self, evidence: Any) -> tuple[str, list[str]]:
        """Validate *evidence* and return ``(status, warnings)``.

        A ``fail`` status means the object is irredeemable and should be
        dropped.  ``requires_review`` means it needs human inspection.
        """
        warnings: list[str] = []

        # 1. Mandatory attributes
        warnings.extend(self._check_mandatory(evidence))

        # 2. Confidence range
        warnings.extend(self._check_confidence(evidence))

        # 3. Provenance completeness
        warnings.extend(self._check_provenance(evidence))

        # 4. Temporal consistency
        warnings.extend(self._check_temporal(evidence))

        # 5. Category validity
        warnings.extend(self._check_category(evidence))

        # 6. Epistemic classification validity
        warnings.extend(self._check_epistemic(evidence))

        # Decide final status
        status = self._decide_status(warnings)

        logger.info(
            'cog.evidence.validated',
            evidence_id=getattr(evidence, 'identifier', 'unknown'),
            status=status,
            warning_count=len(warnings),
        )
        return status, warnings

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_mandatory(self, evidence: Any) -> list[str]:
        """Ensure all mandatory attributes are present and non-empty."""
        warnings: list[str] = []
        evidence_dict = self._to_dict(evidence)

        for attr in self.MANDATORY_ATTRIBUTES:
            value = evidence_dict.get(attr)
            if value is None or value == '':
                warnings.append(f'Missing mandatory attribute: {attr}')

        # Check provenance sub-fields
        provenance = evidence_dict.get('provenance')
        if provenance is not None:
            prov_dict = self._to_dict(provenance)
            for field_name in ('conversation_id', 'speaker', 'timestamp'):
                if not prov_dict.get(field_name):
                    warnings.append(f'Incomplete provenance: missing {field_name}')
        elif 'provenance' not in evidence_dict or evidence_dict.get('provenance') is None:
            warnings.append('Missing provenance object')

        return warnings

    def _check_confidence(self, evidence: Any) -> list[str]:
        """Validate confidence is within [0, 1]."""
        warnings: list[str] = []
        conf = getattr(evidence, 'confidence', None)
        if conf is None:
            warnings.append('Confidence value is None')
        elif not (MIN_CONFIDENCE <= conf <= MAX_CONFIDENCE):
            warnings.append(
                f'Confidence {conf} outside valid range [{MIN_CONFIDENCE}, {MAX_CONFIDENCE}]'
            )
        return warnings

    def _check_provenance(self, evidence: Any) -> list[str]:
        """Check provenance chain completeness."""
        warnings: list[str] = []
        provenance = getattr(evidence, 'provenance', None)
        if provenance is None:
            return ['No provenance attached']

        prov_dict = self._to_dict(provenance)

        required_prov_fields = ('conversation_id', 'speaker', 'timestamp')
        for field_name in required_prov_fields:
            val = prov_dict.get(field_name)
            if val is None or val == '':
                warnings.append(f'Provenance missing field: {field_name}')

        # Check that engine_version is set
        engine_ver = prov_dict.get('engine_version', '')
        if not engine_ver:
            warnings.append('Provenance missing engine_version')

        return warnings

    @staticmethod
    def _check_temporal(evidence: Any) -> list[str]:
        """Verify temporal consistency (creation timestamp exists)."""
        warnings: list[str] = []
        ts = getattr(evidence, 'creation_timestamp', None)
        if ts is None:
            warnings.append('Missing creation_timestamp')
        return warnings

    @staticmethod
    def _check_category(evidence: Any) -> list[str]:
        """Verify category is a valid value."""
        warnings: list[str] = []
        cat = getattr(evidence, 'category', '')
        if not cat:
            warnings.append('Empty evidence category')
        return warnings

    @staticmethod
    def _check_epistemic(evidence: Any) -> list[str]:
        """Verify epistemic classification is present."""
        warnings: list[str] = []
        ec = getattr(evidence, 'epistemic_classification', '')
        if not ec:
            warnings.append('Empty epistemic classification')
        return warnings

    # ------------------------------------------------------------------
    # Status decision
    # ------------------------------------------------------------------

    @staticmethod
    def _decide_status(warnings: list[str]) -> str:
        """Map a list of warnings to a validation status."""
        if not warnings:
            return 'pass'
        if len(warnings) <= MAX_WARNINGS_FOR_PASS:
            return 'pass_with_warning'
        return 'requires_review'

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _to_dict(obj: Any) -> dict[str, Any]:
        """Convert a dataclass or object to a flat dict for inspection."""
        if isinstance(obj, dict):
            return obj
        if hasattr(obj, '__dataclass_fields__'):
            return {f: getattr(obj, f) for f in obj.__dataclass_fields__}
        if hasattr(obj, '__dict__'):
            return dict(obj.__dict__)
        return {}
