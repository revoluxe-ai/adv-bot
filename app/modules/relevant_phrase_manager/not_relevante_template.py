class NotRelevantTemplate:
    def __init__(self, row_template: list[str]):
        self._row_template = row_template

    @property
    def _negative_contains(self) -> set[str]:
        phrases = set()
        for row in self._row_template:
            row = row.strip()
            if row.lower().startswith("any:"):
                continue

            row = self._strip_not_prefix(row)

            if not self._is_quoted(row):
                phrases.add(row)
        return phrases

    @property
    def _negative_exact(self) -> set[str]:
        phrases = set()
        for row in self._row_template:
            row = row.strip()
            if row.lower().startswith("any:"):
                continue

            row = self._strip_not_prefix(row)

            if self._is_quoted(row):
                phrases.add(row.strip("\"'"))  # убираем кавычки
        return phrases

    @property
    def _required_any_groups(self) -> list[list[str]]:
        groups = []
        for row in self._row_template:
            row = row.strip()
            if row.lower().startswith("any:"):
                content = row.split(":", 1)[1].strip()
                group = [item.strip() for item in content.split(",") if item.strip()]
                if group:
                    groups.append(group)
        return groups

    def _is_quoted(self, text: str) -> bool:
        return (text.startswith('"') or text.endswith('"')) or (
            text.startswith("'") or text.endswith("'")
        )

    def _strip_not_prefix(self, text: str) -> str:
        if text.lower().startswith("not:"):
            return text[4:].strip()
        return text

    def is_relevant(self, phrase: str) -> bool:
        phrase_lower = phrase.lower()

        # 1. Исключаем по точному совпадению
        if phrase_lower in (p.lower() for p in self._negative_exact):
            return False

        # 2. Исключаем по вхождению
        for neg in self._negative_contains:
            if neg.lower() in phrase_lower:
                return False

        # 3. Проверка обязательных ANY-групп (в каждой группе должно быть хотя бы одно вхождение)
        for group in self._required_any_groups:
            if not any(word.lower() in phrase_lower for word in group):
                return False

        # Если ни одно правило не нарушено — релевантна
        return True
