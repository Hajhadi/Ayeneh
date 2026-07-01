"""Safety — input/output validation, prompt injection detection, output limits."""

from __future__ import annotations

import re
from typing import Any

import structlog

from ayeneh.llm.types import LLMConfig, SafetyConfig

logger = structlog.get_logger(__name__)

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"you\s+are\s+now\s+(a|an)\s+",
    r"disregard\s+(all|any|your)\s+",
    r"forget\s+(everything|all|your)\s+",
    r"system\s*:\s*you\s+are",
    r"new\s+instructions?\s*:",
    r"<\s*system\s*>",
    r"\[system\]",
    r"override\s+(safety|instructions?)",
]


class SafetyValidator:
    """Validates inputs and outputs against safety policies."""

    def __init__(self, config: SafetyConfig | None = None) -> None:
        self._config = config or SafetyConfig()

    def validate_input(self, text: str) -> tuple[bool, list[str]]:
        issues: list[str] = []

        if len(text) > self._config.max_prompt_length:
            issues.append(f"Input exceeds max length ({len(text)} > {self._config.max_prompt_length})")

        if self._config.injection_check_enabled:
            for pattern in INJECTION_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    issues.append(f"Potential prompt injection detected: {pattern[:40]}")
                    break

        return len(issues) == 0, issues

    def validate_config(self, config: LLMConfig) -> tuple[bool, list[str]]:
        issues: list[str] = []

        t_min, t_max = self._config.temperature_range
        if config.temperature < t_min or config.temperature > t_max:
            issues.append(f"Temperature {config.temperature} outside range [{t_min}, {t_max}]")

        if config.max_tokens > self._config.max_tokens:
            issues.append(f"max_tokens {config.max_tokens} exceeds limit {self._config.max_tokens}")

        if config.max_tokens < 1:
            issues.append("max_tokens must be at least 1")

        return len(issues) == 0, issues

    def validate_output(self, text: str) -> tuple[bool, list[str]]:
        issues: list[str] = []
        if not text.strip():
            issues.append("Empty output")
        return len(issues) == 0, issues

    def sanitize_output(self, text: str) -> str:
        text = text.strip()
        for seq in self._config.stop_sequences:
            idx = text.find(seq)
            if idx >= 0:
                text = text[:idx]
        return text
