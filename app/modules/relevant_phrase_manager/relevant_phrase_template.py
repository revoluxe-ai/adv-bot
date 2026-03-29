from ._compiled_phrase_template import CompiledPhraseTemplate


class RelevantPhraseTemplate(CompiledPhraseTemplate):
    """Шаблоны релевантных фраз: те же правила, что у NotRelevantTemplate (quoted + RE2).

    Фраза «подходит» под шаблон, если совпадает с точной строкой в кавычках
    или матчится regex (без кавычек).
    """

    def __init__(self, row_template: list[str]):
        super().__init__(row_template=row_template, log_context="релевантных фраз")

    def matches(self, phrase: str) -> bool:
        return self._matches_any(phrase)
