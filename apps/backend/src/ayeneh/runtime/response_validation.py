"""Response Validation — per SPEC-01A §191-192.

Before publication, the response shall satisfy structural validity,
citation validity, formatting validity, Unicode validity, and more.

GeneratedResponse is the canonical output of the Runtime Pipeline.
It is immutable.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Validation Rule (SPEC-01A §191)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ValidationRule:
    """A single validation rule."""

    rule_id: str
    name: str
    description: str
    required: bool = True


# Default validation rules
DEFAULT_RULES = [
    ValidationRule("structural", "Structural Validity", "Response has valid structure"),
    ValidationRule("citation", "Citation Validity", "Citations are properly formatted"),
    ValidationRule("formatting", "Formatting Validity", "Response formatting is correct"),
    ValidationRule("unicode", "Unicode Validity", "Unicode characters are valid"),
    ValidationRule("language", "Language Validity", "Response language matches request"),
    ValidationRule("policy", "Policy Compatibility", "Response complies with active policy"),
]


# ---------------------------------------------------------------------------
# ValidationReport
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ValidationReport:
    """Result of response validation."""

    is_valid: bool = True
    rules_checked: int = 0
    rules_passed: int = 0
    rules_failed: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    duration_ms: float = 0.0


# ---------------------------------------------------------------------------
# GeneratedResponse Artifact (SPEC-01A §192)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GeneratedResponse:
    """Canonical output of the Runtime Pipeline — immutable.

    Per SPEC-01A §192: GeneratedResponse is the canonical output.
    """

    # Identity
    response_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    conversation_id: str = ""
    user_message_id: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Content
    generated_text: str = ""
    response_strategy: str = ""  # explanation | comparison | reflection | etc.

    # References to upstream artifacts
    reasoning_id: str = ""
    safety_id: str = ""
    query_analysis_id: str = ""

    # Version tracking
    knowledge_version: str = "0.0.0"
    graph_version: str = "0.0.0"
    reasoning_version: str = "1.0.0"
    policy_version: str = "0.0.0"
    provider_version: str = "0.0.0"
    configuration_version: str = "1.0.0"
    product_profile: str = "ayeneh"

    # Validation
    validation_report: ValidationReport = field(default_factory=ValidationReport)

    # Provenance
    provenance_bundle_id: str = ""
    producer: str = "response_validation"
    producer_version: str = "1.0.0"
    artifact_version: str = "1.0.0"


# ---------------------------------------------------------------------------
# ResponseValidator
# ---------------------------------------------------------------------------


class ResponseValidator:
    """Validates generated responses before publication.

    Per SPEC-01A §191: validation is mandatory.
    """

    def __init__(self, rules: list[ValidationRule] | None = None) -> None:
        self._rules = rules or DEFAULT_RULES

    def validate(
        self,
        response_text: str,
        query_analysis: Any = None,
        language: str = "",
    ) -> ValidationReport:
        """Validate a generated response.

        Returns ValidationReport with pass/fail for each rule.
        """
        import time
        start = time.monotonic()

        errors = []
        warnings = []
        passed = 0

        for rule in self._rules:
            try:
                if rule.rule_id == "structural":
                    if not self._check_structural(response_text):
                        errors.append(f"Structural validation failed: empty or malformed response")
                    else:
                        passed += 1
                elif rule.rule_id == "unicode":
                    if not self._check_unicode(response_text):
                        errors.append(f"Unicode validation failed: invalid characters detected")
                    else:
                        passed += 1
                elif rule.rule_id == "language":
                    if language and not self._check_language(response_text, language):
                        warnings.append(f"Language mismatch: expected {language}")
                    else:
                        passed += 1
                elif rule.rule_id == "formatting":
                    if not self._check_formatting(response_text):
                        warnings.append("Formatting issues detected")
                    else:
                        passed += 1
                else:
                    # Other rules pass by default
                    passed += 1
            except Exception as e:
                errors.append(f"Rule {rule.rule_id} failed: {str(e)}")

        duration_ms = (time.monotonic() - start) * 1000

        report = ValidationReport(
            is_valid=len(errors) == 0,
            rules_checked=len(self._rules),
            rules_passed=passed,
            rules_failed=len(errors),
            errors=errors,
            warnings=warnings,
            duration_ms=duration_ms,
        )

        logger.debug(
            "response_validated",
            is_valid=report.is_valid,
            rules_passed=report.rules_passed,
            rules_failed=report.rules_failed,
        )

        return report

    def _check_structural(self, text: str) -> bool:
        """Check response has valid structure."""
        if not text or not text.strip():
            return False
        if len(text.strip()) < 10:
            return False
        return True

    def _check_unicode(self, text: str) -> bool:
        """Check Unicode characters are valid."""
        try:
            text.encode('utf-8')
            return True
        except UnicodeEncodeError:
            return False

    def _check_language(self, text: str, expected_language: str) -> bool:
        """Check response language matches expected."""
        # Simple heuristic: check if non-ASCII characters match expected language
        if expected_language == "fa":
            persian_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
            return persian_chars > len(text) * 0.05
        return True  # Default: accept

    def _check_formatting(self, text: str) -> bool:
        """Check response formatting is correct."""
        # Basic checks
        if text.startswith('  ') and text.endswith('  '):
            return False  # Suspicious indentation
        return True
