import logging
from typing import Any

import re2

logger = logging.getLogger(__name__)

_RE2_OPTS = re2.Options()
_RE2_OPTS.case_sensitive = False

_MAX_PATTERN_LEN = 512


class CompiledPhraseTemplate:
    """Common parser/compiler for quoted exact matches, legacy any:/not:, and RE2."""

    def __init__(
        self,
        row_template: list[str],
        log_context: str,
        *,
        not_unquoted_as_exclude: bool = False,
    ) -> None:
        self._row_template = row_template
        self._log_context = log_context
        self._not_unquoted_as_exclude = not_unquoted_as_exclude
        self._exact: list[str] = []
        self._substring_includes: list[str] = []
        self._substring_excludes: list[str] = []
        self._any_groups: list[list[str]] = []
        self._patterns: list[Any] = []
        self._parse_rows()

    def _parse_rows(self) -> None:
        for raw in self._row_template:
            row = raw.strip()
            if not row:
                continue
            row_cf = row.casefold()
            if row_cf.startswith("any:"):
                if len(row) > _MAX_PATTERN_LEN:
                    logger.warning(
                        "Пропуск слишком длинного шаблона %s (%s симв.): %r…",
                        self._log_context,
                        len(row),
                        row[:80],
                    )
                    continue
                content = row.split(":", 1)[1].strip()
                group = [item.strip() for item in content.split(",") if item.strip()]
                if group:
                    self._any_groups.append(group)
                continue
            if row_cf.startswith("not:"):
                rest = row.split(":", 1)[1].strip()
                if not rest:
                    continue
                if self._is_quoted(rest):
                    inner = rest.strip("\"'")
                    if inner:
                        self._exact.append(inner)
                    continue
                if len(rest) > _MAX_PATTERN_LEN:
                    logger.warning(
                        "Пропуск слишком длинного шаблона %s (%s симв.): %r…",
                        self._log_context,
                        len(rest),
                        rest[:80],
                    )
                    continue
                if self._not_unquoted_as_exclude:
                    self._substring_excludes.append(rest)
                else:
                    self._substring_includes.append(rest)
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
        """True only when wrapped in a matching pair of ``"`` or ``'`` (same delimiter both ends)."""
        if len(text) < 2:
            return False
        opening = text[0]
        if opening not in "\"'":
            return False
        return text[-1] == opening

    def _matches_any(self, phrase: str) -> bool:
        phrase_cf = phrase.casefold()
        for exact in self._exact:
            if phrase_cf == exact.casefold():
                return True
        for sub in self._substring_includes:
            if sub.casefold() in phrase_cf:
                return True
        for pattern in self._patterns:
            if pattern.search(phrase):
                return True
        for group in self._any_groups:
            if any(token.casefold() in phrase_cf for token in group):
                return True
        return False
