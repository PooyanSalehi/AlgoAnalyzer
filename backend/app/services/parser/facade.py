"""Parser facade: dispatches an algorithm submission to the right backend."""
from __future__ import annotations

from app.services.parser.heuristic_parsers import NaturalLanguageParser, PseudocodeParser
from app.services.parser.models import AlgorithmIR, InputMode
from app.services.parser.python_parser import PythonParser


class AlgorithmParser:
    """Front door of the parsing subsystem.

    Usage::

        parser = AlgorithmParser()
        ir = parser.parse(code="def sort(a): ...", name="Merge Sort", mode=InputMode.PYTHON)
    """

    def __init__(self) -> None:
        self._backends = {
            InputMode.PYTHON: PythonParser(),
            InputMode.PSEUDOCODE: PseudocodeParser(),
            InputMode.NATURAL: NaturalLanguageParser(),
        }

    def parse(self, code: str, name: str, mode: InputMode) -> AlgorithmIR:
        backend = self._backends.get(mode, self._backends[InputMode.PYTHON])
        ir = backend.parse(code, name=name or "Algorithm")
        if not ir.name or ir.name == "Algorithm":
            ir.name = name or "Algorithm"
        return ir
