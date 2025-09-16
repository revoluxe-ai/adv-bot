from dataclasses import dataclass


@dataclass
class ParsingTask:
    """
    Модель задачи парсинга
    
    Attributes:
        keyword: Ключевая фраза для поиска
        nmids: Множество nmids для поиска
        adv_id_order: ID заказа (опционально)
    """
    keyword: str
    nmids: set[int]
    adv_id_order: str | None = None

    @property
    def id(self) -> str:
        """Генерирует уникальный ID задачи на основе ключевой фразы"""
        import hashlib
        return hashlib.sha1(self.keyword.encode()).hexdigest()[:12]
