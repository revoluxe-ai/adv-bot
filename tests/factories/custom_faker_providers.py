"""Кастомные Faker провайдеры для генерации тестовых данных."""

from faker.providers import BaseProvider

from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
    KeywordStatusReason,
)


class KeywordStatusProvider(BaseProvider):
    """Провайдер для генерации KeywordStatus."""
    
    _statuses = list(KeywordStatus)

    def keyword_status(self) -> KeywordStatus:
        """Возвращает случайный KeywordStatus."""
        return self.random_element(self._statuses)
    
    # Алиас для совместимости
    def keyword_state(self) -> KeywordStatus:
        """Алиас для keyword_status (для совместимости)."""
        return self.keyword_status()


class KeywordStatusReasonProvider(BaseProvider):
    """Провайдер для генерации KeywordStatusReason."""
    
    _reasons = list(KeywordStatusReason)

    def keyword_status_reason(self) -> KeywordStatusReason:
        """Возвращает случайный KeywordStatusReason."""
        return self.random_element(self._reasons)
    
    # Алиас для совместимости
    def status_reason(self) -> KeywordStatusReason:
        """Алиас для keyword_status_reason (для совместимости)."""
        return self.keyword_status_reason()
