"""Optional LLM-backed explanation provider (OpenAI Chat Completions).

Activated with::

    AI_PROVIDER=openai
    OPENAI_API_KEY=sk-...

Any failure (missing key, network error, timeout) degrades gracefully to
the deterministic :class:`HeuristicExplainer`, so the platform never
depends on an external service to produce explanations.
"""
from __future__ import annotations

import json

import httpx

from app.core.config import get_settings
from app.services.ai.heuristic_explainer import HeuristicExplainer
from app.services.reports.generator import ReportInputs

_API_URL = "https://api.openai.com/v1/chat/completions"

_SYSTEM_PROMPT = (
    "You are a senior computer-science educator. You receive a structured JSON "
    "analysis of two algorithms and write a clear, correct, university-level "
    "explanation (3-5 short paragraphs, Markdown) covering: what each algorithm "
    "does, whether they are functionally equivalent, their complexity trade-offs "
    "with the underlying recurrence/Master Theorem reasoning, and a practical "
    "recommendation. Use the numbers provided; do not invent measurements."
)


class OpenAIExplainer:
    """LLM explanation with graceful fallback to the heuristic engine."""

    name = "openai"

    def __init__(self) -> None:
        self._fallback = HeuristicExplainer()
        self._settings = get_settings()

    def explain(self, data: ReportInputs) -> str:
        if not self._settings.openai_api_key:
            return self._fallback.explain(data)
        try:
            return self._call_openai(data)
        except Exception:  # noqa: BLE001 - never break the analysis pipeline
            return self._fallback.explain(data)

    def _call_openai(self, data: ReportInputs) -> str:
        payload = {
            "model": self._settings.openai_model,
            "temperature": 0.3,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(self._summarise(data), indent=2)},
            ],
        }
        headers = {"Authorization": f"Bearer {self._settings.openai_api_key}"}
        response = httpx.post(
            _API_URL,
            json=payload,
            headers=headers,
            timeout=self._settings.openai_timeout_seconds,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()

    @staticmethod
    def _summarise(data: ReportInputs) -> dict:
        """Compact JSON view of the analysis for the language model."""
        return {
            "algorithm_a": {
                "name": data.ir_a.name,
                "pattern": data.complexity_a.pattern,
                "recurrence": data.complexity_a.recurrence,
                "time": {
                    "best": data.complexity_a.time.best.label,
                    "average": data.complexity_a.time.average.label,
                    "worst": data.complexity_a.time.worst.label,
                },
                "aux_space": data.complexity_a.space.auxiliary.label,
                "math_explanations": data.complexity_a.explanations,
            },
            "algorithm_b": {
                "name": data.ir_b.name,
                "pattern": data.complexity_b.pattern,
                "recurrence": data.complexity_b.recurrence,
                "time": {
                    "best": data.complexity_b.time.best.label,
                    "average": data.complexity_b.time.average.label,
                    "worst": data.complexity_b.time.worst.label,
                },
                "aux_space": data.complexity_b.space.auxiliary.label,
                "math_explanations": data.complexity_b.explanations,
            },
            "functional": {
                "equivalent": data.functional.equivalent,
                "purpose_a": data.functional.purpose_a,
                "purpose_b": data.functional.purpose_b,
                "output_agreement": data.benchmark.output_agreement,
            },
            "similarity": {"score": data.similarity.score, "band": data.similarity.band},
            "benchmark": data.benchmark.comparison[-3:] if data.benchmark.comparison else [],
        }
