from ._compiled_phrase_template import CompiledPhraseTemplate


class NotRelevantTemplate(CompiledPhraseTemplate):
    """НРФ (чёрный список): тот же синтаксис строк, что у релевантных шаблонов, но инвертированная проверка."""

    def __init__(self, row_template: list[str]) -> None:
        super().__init__(
            row_template=row_template,
            log_context="НРФ",
            not_unquoted_as_exclude=True,
        )

    def is_relevant(self, phrase: str) -> bool:
        phrase_cf = phrase.casefold()
        for exact in self._exact:
            if phrase_cf == exact.casefold():
                return False
        for sub in self._substring_excludes:
            if sub.casefold() in phrase_cf:
                return False
        for pattern in self._patterns:
            if pattern.search(phrase):
                return False
        for group in self._any_groups:
            if not any(token.casefold() in phrase_cf for token in group):
                return False
        return True
