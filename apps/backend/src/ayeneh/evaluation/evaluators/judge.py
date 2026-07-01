"""LLM-as-a-Judge evaluator — pluggable judge backed by any LLM."""

from __future__ import annotations

import json
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

JUDGE_PROMPT = """You are a strict evaluation judge for a Cognitive Companion AI system.
Given the input, expected output, and actual output, rate the quality.

Input: {input}
Expected: {expected}
Actual: {actual}
Context: {context}

Rate on a scale of 0.0 to 1.0:
- 0.0-0.3: Poor — major issues
- 0.3-0.6: Acceptable — some issues
- 0.6-0.8: Good — minor issues
- 0.8-1.0: Excellent — production ready

Return JSON: {{"score": <float>, "reasoning": "<brief explanation>"}}
"""


class LLMJudge:
    """Evaluates agent outputs using an LLM as judge.

    Pluggable: accepts any LLM gateway that implements `chat()`.
    """

    def __init__(self, llm_gateway: Any | None = None, model: str = "gpt-4o-mini") -> None:
        self._llm = llm_gateway
        self._model = model

    def judge(
        self,
        input_data: dict[str, Any],
        expected: dict[str, Any],
        actual: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> tuple[float, str]:
        if self._llm is None:
            return self._heuristic_judge(input_data, expected, actual, context)

        prompt = JUDGE_PROMPT.format(
            input=json.dumps(input_data, default=str)[:2000],
            expected=json.dumps(expected, default=str)[:2000],
            actual=json.dumps(actual, default=str)[:2000],
            context=json.dumps(context or {}, default=str)[:1000],
        )

        try:
            import asyncio
            result = asyncio.get_event_loop().run_until_complete(
                self._llm.chat(
                    [{"role": "user", "content": prompt}],
                    model=self._model,
                    temperature=0.0,
                )
            )
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            parsed = json.loads(content)
            return parsed.get("score", 0.5), parsed.get("reasoning", "")
        except Exception as exc:
            logger.warning("llm_judge_failed", error=str(exc))
            return self._heuristic_judge(input_data, expected, actual, context)

    def _heuristic_judge(
        self,
        input_data: dict[str, Any],
        expected: dict[str, Any],
        actual: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> tuple[float, str]:
        score = 0.5
        reasons = []

        for key in expected:
            if key in actual:
                exp_val = expected[key]
                act_val = actual[key]
                if isinstance(exp_val, str) and isinstance(act_val, str):
                    overlap = len(set(exp_val.lower().split()) & set(act_val.lower().split()))
                    total = max(len(set(exp_val.lower().split())), 1)
                    partial = overlap / total
                    score += partial * 0.2
                    reasons.append(f"{key}: {partial:.0%} overlap")
                elif isinstance(exp_val, list) and isinstance(act_val, list):
                    score += min(0.2, len(act_val) / max(len(exp_val), 1) * 0.2)
                    reasons.append(f"{key}: {len(act_val)}/{len(exp_val)} items")
            else:
                score -= 0.1
                reasons.append(f"{key}: missing from actual")

        score = max(0.0, min(1.0, score))
        return score, "; ".join(reasons)
