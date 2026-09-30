"""Domain errors raised by the analysis services.

The API layer translates these into structured HTTP responses so that
malformed user input never surfaces as an opaque 500 error.
"""
from __future__ import annotations


class AlgoAnalyzerError(Exception):
    """Base class for all domain errors."""


class ParseError(AlgoAnalyzerError):
    """Raised when source code cannot be parsed (e.g. Python syntax error)."""


class BenchmarkError(AlgoAnalyzerError):
    """Raised when the benchmark sandbox cannot be initialised."""
