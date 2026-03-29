import logging
from typing import Any

import re2

logger = logging.getLogger(__name__)

# RE2 guarantees linear-time matching (no catastrophic backtracking). User patterns are
# compiled with case-insensitive semantics equivalent to re.IGNORECASE for literals.
_RE2_OPTS = re2.Options()
_RE2_OPTS.case_sensitive = False

_MAX_PATTERN_LEN = 512


class CompiledPhraseTemplate:
    """Common parser/compiler for quoted exact matches and RE2 regex templates."""

    def __init__(self, row_template: list[str], log_context: str):
        self._row_template = row_template
        self._log_context = log_context
        self._exact: list[str] = []
        self._patterns: list[Any] = []
        self._parse_rows()

    def _parse_rows(self) -> None:
        for raw in self._row_template:
            row = raw.strip()
            if not row:
                continue
            if self._is_quoted(row):
                inner = row.strip("\"'")
                if inner:
                    self._exact.append(inner)
                continue
            if len(row) > _MAX_PATTERN_LEN:
                logger.warning(
                    "Пропуск слишком длинного шаблона %s (%s симв.): %r…",
                    self._log_context,
                    len(row),
                    row[:80],
                )
                continue
            try:
                self._patterns.append(
                    re2.compile(row, _RE2_OPTS)  # pyright: ignore[reportUnknownMemberType]
                )
            except re2.error:  # pyright: ignore[reportUnknownMemberType]
                logger.warning(
                    "Пропуск невалидного или неподдерживаемого regex в шаблоне %s: %r",
                    self._log_context,
                    row,
                )

    @staticmethod
    def _is_quoted(text: str) -> bool:
        return (text.startswith('"') or text.endswith('"')) or (
            text.startswith("'") or text.endswith("'")
        )

    def _matches_any(self, phrase: str) -> bool:
        phrase_cf = phrase.casefold()
        for exact in self._exact:
            if phrase_cf == exact.casefold():
                return True
        for pattern in self._patterns:
            if pattern.search(phrase):
                return True
        return False
