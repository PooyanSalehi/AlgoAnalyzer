"""AI explanation layer — pluggable interface.

The platform generates human-readable explanations of the analysis through
an :class:`Explainer` implementation:

* :class:`HeuristicExplainer` (default) — deterministic, template-driven
  natural-language generation that works fully offline.
* :class:`OpenAIExplainer` — optional LLM-backed explainer (requires
  ``OPENAI_API_KEY``); on any failure it transparently falls back to the
  heuristic engine.

Adding a new provider is a matter of implementing ``explain`` and
registering it in :func:`get_explainer` — the rest of the platform is
unaware of the choice (strategy pattern).
"""
from __future__ import annotations

from typing import Protocol

from app.services.reports.generator import ReportInputs


class Explainer(Protocol):
    """Interface every AI explanation provider must implement."""

    name: str

    def explain(self, data: ReportInputs) -> str:
        """Return a human-readable explanation of the comparison."""
        ...


def get_explainer(provider: str = "heuristic") -> Explainer:
    """Factory returning the configured explainer (modular & replaceable)."""
    from app.services.ai.heuristic_explainer import HeuristicExplainer

    if provider == "openai":
        from app.services.ai.openai_explainer import OpenAIExplainer

        return OpenAIExplainer()
    return HeuristicExplainer()
