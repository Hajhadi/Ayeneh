"""Tests for Response Validation per SPEC-01A §191-192."""

import pytest
from ayeneh.runtime.response_validation import (
    ResponseValidator,
    GeneratedResponse,
    ValidationReport,
    ValidationRule,
    DEFAULT_RULES,
)


@pytest.fixture
def validator():
    return ResponseValidator()


# ---------------------------------------------------------------------------
# ValidationReport
# ---------------------------------------------------------------------------


class TestValidationReport:
    def test_creation(self):
        r = ValidationReport()
        assert r.is_valid is True
        assert r.rules_checked == 0

    def test_immutable(self):
        r = ValidationReport()
        with pytest.raises(AttributeError):
            r.is_valid = False


# ---------------------------------------------------------------------------
# GeneratedResponse
# ---------------------------------------------------------------------------


class TestGeneratedResponse:
    def test_creation(self):
        gr = GeneratedResponse(generated_text="Test response")
        assert gr.generated_text == "Test response"
        assert gr.response_id is not None

    def test_immutable(self):
        gr = GeneratedResponse()
        with pytest.raises(AttributeError):
            gr.generated_text = "changed"

    def test_has_version_fields(self):
        gr = GeneratedResponse()
        assert gr.knowledge_version == "0.0.0"
        assert gr.graph_version == "0.0.0"
        assert gr.reasoning_version == "1.0.0"

    def test_has_validation_report(self):
        gr = GeneratedResponse()
        assert isinstance(gr.validation_report, ValidationReport)


# ---------------------------------------------------------------------------
# ResponseValidator
# ---------------------------------------------------------------------------


class TestResponseValidator:
    def test_valid_response(self, validator):
        report = validator.validate("This is a valid response with enough content.")
        assert report.is_valid is True
        assert report.rules_passed > 0

    def test_empty_response_fails(self, validator):
        report = validator.validate("")
        assert report.is_valid is False

    def test_short_response_fails(self, validator):
        report = validator.validate("Hi")
        assert report.is_valid is False

    def test_valid_persian_response(self, validator):
        report = validator.validate("این یک پاسخ معتبر فارسی است که به اندازه کافی طولانی باشد.", language="fa")
        assert report.is_valid is True

    def test_rules_checked(self, validator):
        report = validator.validate("Valid response with enough content.")
        assert report.rules_checked == len(DEFAULT_RULES)

    def test_custom_rules(self):
        custom_rules = [ValidationRule("test", "Test Rule", "Test")]
        validator = ResponseValidator(rules=custom_rules)
        report = validator.validate("Valid response.")
        assert report.rules_checked == 1


# ---------------------------------------------------------------------------
# Backward Compatibility
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_generated_response_has_all_required_fields(self):
        gr = GeneratedResponse()
        assert hasattr(gr, 'response_id')
        assert hasattr(gr, 'session_id')
        assert hasattr(gr, 'conversation_id')
        assert hasattr(gr, 'generated_text')
        assert hasattr(gr, 'response_strategy')
        assert hasattr(gr, 'reasoning_id')
        assert hasattr(gr, 'safety_id')
        assert hasattr(gr, 'query_analysis_id')
        assert hasattr(gr, 'knowledge_version')
        assert hasattr(gr, 'graph_version')
        assert hasattr(gr, 'validation_report')
        assert hasattr(gr, 'provenance_bundle_id')
