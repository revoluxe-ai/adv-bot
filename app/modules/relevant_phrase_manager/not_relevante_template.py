from ._compiled_phrase_template import CompiledPhraseTemplate


class NotRelevantTemplate(CompiledPhraseTemplate):
    def __init__(self, row_template: list[str]):
        super().__init__(row_template=row_template, log_context="НРФ")

    def is_relevant(self, phrase: str) -> bool:
        return not self._matches_any(phrase)
