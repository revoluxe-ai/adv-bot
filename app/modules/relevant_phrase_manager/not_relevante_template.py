import logging
import re

logger = logging.getLogger(__name__)

_RE_FLAGS = re.IGNORECASE


class NotRelevantTemplate:
    def __init__(self, row_template: list[str]):
        self._row_template = row_template
        self._exact: list[str] = []
        self._patterns: list[re.Pattern[str]] = []
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
            try:
                self._patterns.append(re.compile(row, _RE_FLAGS))
            except re.error:
                logger.warning(
                    "Пропуск невалидного regex в шаблоне НРФ: %r",
                    row,
                )

    @staticmethod
    def _is_quoted(text: str) -> bool:
        return (text.startswith('"') or text.endswith('"')) or (
            text.startswith("'") or text.endswith("'")
        )

    def is_relevant(self, phrase: str) -> bool:
        phrase_cf = phrase.casefold()
        for exact in self._exact:
            if phrase_cf == exact.casefold():
                return False
        for pattern in self._patterns:
            if pattern.search(phrase):
                return False
        return True
