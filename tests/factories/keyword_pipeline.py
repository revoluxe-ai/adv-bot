"""Factory Boy фабрики для создания CalculatedKeyword и связанных объектов.

Основная фабрика - CalculatedKeywordFactory.
Позволяет задавать параметры напрямую или использовать вложенные фабрики.

Примеры использования:
    # Простое создание
    kw = CalculatedKeywordFactory()
    
    # С конкретными параметрами
    kw = CalculatedKeywordFactory(
        keyword_setting__text="платье",
        keyword_setting__hard_status=HardStatus.WHITELIST,
        cluster_stat__views=1000,
        cluster_stat__clicks=50,
        state__status=KeywordStatus.GOOD,
    )
    
    # Batch создание
    keywords = CalculatedKeywordFactory.create_batch(10)
    
    # С готовыми объектами (для сложных случаев)
    kw = CalculatedKeywordFactory(
        keyword_setting=my_dto,
        cluster_stat=my_stat,
    )
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import IntEnum

import factory
from faker import Faker

from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.inner_dto.keyword_state import (
    KeywordState,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.inner_dto.pre_calculated_keyword import (
    PreCalculatedKeyword,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
    KeywordStatusReason,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_setting_dto import (
    KeywordSettingDTO,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_stat import (
    KeywordStat,
)
from tests.factories.custom_faker_providers import (
    KeywordStatusProvider,
    KeywordStatusReasonProvider,
)

fake = Faker("ru_RU")
fake.add_provider(KeywordStatusProvider)
fake.add_provider(KeywordStatusReasonProvider)


class HardStatus(IntEnum):
    """Статусы ключевых слов (hard_status)."""

    BLACKLIST = 0  # чёрный список
    IN_TEST = 1  # в тестировании
    WHITELIST = 2  # белый список
    TURN_OFF = 3  # отключён


# ============================================================================
# KeywordSettingDTO Factory
# ============================================================================


class KeywordSettingDTOFactory(factory.Factory):
    """Factory для KeywordSettingDTO."""

    class Meta:
        model = KeywordSettingDTO

    text = factory.LazyFunction(lambda: fake.unique.word())
    relevant = factory.LazyFunction(lambda: fake.boolean())
    hard_status = factory.LazyFunction(
        lambda: fake.random_element([HardStatus.BLACKLIST, HardStatus.IN_TEST, HardStatus.WHITELIST])
    )
    id = factory.LazyFunction(lambda: fake.random_int(1, 100000))
    predict_ctr = factory.LazyFunction(
        lambda: round(fake.pyfloat(min_value=0.01, max_value=0.15), 4) if fake.boolean(chance_of_getting_true=70) else None
    )
    added_clicks = factory.LazyFunction(lambda: fake.random_int(0, 50))


# ============================================================================
# KeywordStat Factory
# ============================================================================


class KeywordStatFactory(factory.Factory):
    """Factory для KeywordStat.
    
    KeywordStat использует pydantic Field(alias=...), поэтому при создании
    нужно использовать alias-имена (norm_query, views_all_time, orders_all_time).
    """

    class Meta:
        model = KeywordStat

    # Используем alias-имена для pydantic модели
    norm_query = factory.LazyFunction(lambda: fake.word())
    position = factory.LazyFunction(lambda: round(fake.pyfloat(min_value=1.0, max_value=100.0), 2))
    timestamp = factory.LazyFunction(
        lambda: fake.date_time_between(start_date="-30d", end_date="now", tzinfo=timezone.utc)
    )
    
    # Статистика с логичными зависимостями
    views = factory.LazyFunction(lambda: fake.random_int(100, 10000))
    clicks = factory.LazyAttribute(lambda obj: fake.random_int(1, max(1, int(obj.views * 0.1))))
    add_to_cart = factory.LazyAttribute(lambda obj: fake.random_int(0, obj.clicks))
    orders = factory.LazyAttribute(lambda obj: fake.random_int(0, max(1, obj.add_to_cart)))
    spend = factory.LazyFunction(lambda: round(fake.pyfloat(min_value=10.0, max_value=5000.0), 2))
    cpc = factory.LazyFunction(lambda: fake.random_int(50, 500))
    cpm = factory.LazyFunction(lambda: round(fake.pyfloat(min_value=50.0, max_value=500.0), 2))
    
    # Расчётные поля
    base_cart_to_order_conv = factory.LazyFunction(
        lambda: round(fake.pyfloat(min_value=0.1, max_value=0.8), 3)
    )
    expected_orders_from_cart = factory.LazyAttribute(
        lambda obj: round(fake.pyfloat(min_value=0.0, max_value=max(0.01, float(obj.add_to_cart))), 2)
    )
    expected_orders = factory.LazyFunction(
        lambda: round(fake.pyfloat(min_value=0.0, max_value=10.0), 2)
    )
    final_rating = factory.LazyFunction(
        lambda: round(fake.pyfloat(min_value=0.0, max_value=100.0), 2)
    )
    
    # Исторические данные (alias-имена)
    views_all_time = factory.LazyAttribute(
        lambda obj: fake.random_int(obj.views, obj.views * 10)
    )
    orders_all_time = factory.LazyAttribute(
        lambda obj: fake.random_int(obj.orders, max(1, obj.orders * 10))
    )


# ============================================================================
# KeywordState Factory
# ============================================================================


class KeywordStateFactory(factory.Factory):
    """Factory для KeywordState."""

    class Meta:
        model = KeywordState

    status = factory.LazyFunction(lambda: fake.keyword_status())
    reason = factory.LazyFunction(lambda: fake.status_reason())
    best_keyword_status = factory.LazyFunction(lambda: fake.boolean(chance_of_getting_true=10))


# ============================================================================
# PreCalculatedKeyword Factory
# ============================================================================


class PreCalculatedKeywordFactory(factory.Factory):
    """Factory для PreCalculatedKeyword.
    
    PreCalculatedKeyword - промежуточный объект перед расчётом статуса ключевого слова.
    Содержит keyword_setting, cluster_stat и adv_id.
    
    Примеры:
        # Простое создание
        pre_kw = PreCalculatedKeywordFactory()
        
        # С конкретным CTR (views=1000, clicks=100 -> ctr=0.1)
        pre_kw = PreCalculatedKeywordFactory(
            cluster_stat__views=1000,
            cluster_stat__clicks=100,
        )
        
        # Whitelist keyword
        pre_kw = PreCalculatedKeywordFactory(
            keyword_setting__hard_status=HardStatus.WHITELIST,
        )
    """

    class Meta:
        model = PreCalculatedKeyword

    adv_id = factory.LazyFunction(lambda: fake.random_int(1, 100000))
    keyword_setting = factory.SubFactory(KeywordSettingDTOFactory)
    cluster_stat = factory.SubFactory(KeywordStatFactory)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Переопределяем создание для синхронизации text."""
        keyword_setting = kwargs.get('keyword_setting')
        cluster_stat = kwargs.get('cluster_stat')
        
        # Если cluster_stat не передан, но есть keyword_setting, синхронизируем text
        if cluster_stat is None and keyword_setting is not None:
            cluster_stat_kwargs = {}
            for key, value in list(kwargs.items()):
                if key.startswith('cluster_stat__'):
                    cluster_stat_kwargs[key.replace('cluster_stat__', '')] = value
            
            if 'norm_query' not in cluster_stat_kwargs:
                cluster_stat_kwargs['norm_query'] = keyword_setting.text
            
            kwargs['cluster_stat'] = KeywordStatFactory(**cluster_stat_kwargs)
            kwargs = {k: v for k, v in kwargs.items() if not k.startswith('cluster_stat__')}
        
        return super()._create(model_class, *args, **kwargs)


# ============================================================================
# CalculatedKeyword Factory (основная)
# ============================================================================


class CalculatedKeywordFactory(factory.Factory):
    """Основная Factory для CalculatedKeyword.
    
    Примеры:
        # Простое создание
        kw = CalculatedKeywordFactory()
        
        # С конкретным статусом
        kw = CalculatedKeywordFactory(
            state__status=KeywordStatus.GOOD,
            keyword_setting__hard_status=HardStatus.WHITELIST,
        )
        
        # С конкретной статистикой
        kw = CalculatedKeywordFactory(
            cluster_stat__views=1000,
            cluster_stat__clicks=100,
        )
        
        # Batch создание
        keywords = CalculatedKeywordFactory.create_batch(10)
    """

    class Meta:
        model = CalculatedKeyword

    adv_id = factory.LazyFunction(lambda: fake.random_int(1, 100000))
    keyword_setting = factory.SubFactory(KeywordSettingDTOFactory)
    cluster_stat = factory.SubFactory(KeywordStatFactory)
    state = factory.SubFactory(KeywordStateFactory)

    @factory.lazy_attribute
    def _sync_text(self):
        """Синхронизирует text между keyword_setting и cluster_stat."""
        # Этот атрибут не используется в модели, но выполняет побочный эффект
        if hasattr(self, 'keyword_setting') and hasattr(self, 'cluster_stat'):
            # Если cluster_stat уже создан, синхронизируем text
            pass
        return None

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Переопределяем создание для синхронизации text."""
        # Извлекаем или создаём keyword_setting
        keyword_setting = kwargs.get('keyword_setting')
        cluster_stat = kwargs.get('cluster_stat')
        
        # Если cluster_stat не передан, но есть keyword_setting, синхронизируем text
        if cluster_stat is None and keyword_setting is not None:
            # Получаем параметры для cluster_stat
            cluster_stat_kwargs = {}
            for key, value in list(kwargs.items()):
                if key.startswith('cluster_stat__'):
                    cluster_stat_kwargs[key.replace('cluster_stat__', '')] = value
            
            # Устанавливаем norm_query из keyword_setting.text
            if 'norm_query' not in cluster_stat_kwargs:
                cluster_stat_kwargs['norm_query'] = keyword_setting.text
            
            kwargs['cluster_stat'] = KeywordStatFactory(**cluster_stat_kwargs)
            # Удаляем обработанные параметры
            kwargs = {k: v for k, v in kwargs.items() if not k.startswith('cluster_stat__')}
        
        return super()._create(model_class, *args, **kwargs)


# ============================================================================
# Специализированные фабрики для типичных сценариев
# ============================================================================


class GoodKeywordFactory(CalculatedKeywordFactory):
    """Фабрика для хороших ключевых слов (whitelist, GOOD status)."""
    
    keyword_setting = factory.SubFactory(
        KeywordSettingDTOFactory,
        hard_status=HardStatus.WHITELIST,
        relevant=True,
    )
    state = factory.SubFactory(
        KeywordStateFactory,
        status=KeywordStatus.GOOD,
        reason=KeywordStatusReason.WHITE_LIST,
    )
    cluster_stat = factory.SubFactory(
        KeywordStatFactory,
        views=factory.LazyFunction(lambda: fake.random_int(500, 5000)),
        clicks=factory.LazyFunction(lambda: fake.random_int(50, 500)),
    )


class BadKeywordFactory(CalculatedKeywordFactory):
    """Фабрика для плохих ключевых слов (blacklist, BAD status)."""
    
    keyword_setting = factory.SubFactory(
        KeywordSettingDTOFactory,
        hard_status=HardStatus.BLACKLIST,
        relevant=False,
    )
    state = factory.SubFactory(
        KeywordStateFactory,
        status=KeywordStatus.BAD,
        reason=KeywordStatusReason.BLACK_LIST,
    )
    cluster_stat = factory.SubFactory(
        KeywordStatFactory,
        views=factory.LazyFunction(lambda: fake.random_int(100, 500)),
        clicks=factory.LazyFunction(lambda: fake.random_int(1, 20)),
    )


class TestingKeywordFactory(CalculatedKeywordFactory):
    """Фабрика для ключевых слов в тестировании."""
    
    keyword_setting = factory.SubFactory(
        KeywordSettingDTOFactory,
        hard_status=HardStatus.IN_TEST,
    )
    state = factory.SubFactory(
        KeywordStateFactory,
        status=KeywordStatus.VIEWS_IS_NOT_ENOUGH,
        reason=KeywordStatusReason.MORE_THEN_HARD_MIN_CTR,
    )


class BestKeywordFactory(GoodKeywordFactory):
    """Фабрика для лучшего ключевого слова."""
    
    state = factory.SubFactory(
        KeywordStateFactory,
        status=KeywordStatus.GOOD,
        reason=KeywordStatusReason.WHITE_LIST,
        best_keyword_status=True,
    )
    cluster_stat = factory.SubFactory(
        KeywordStatFactory,
        views=factory.LazyFunction(lambda: fake.random_int(2000, 10000)),
        clicks=factory.LazyFunction(lambda: fake.random_int(200, 1000)),
        final_rating=factory.LazyFunction(lambda: round(fake.pyfloat(min_value=80.0, max_value=100.0), 2)),
    )


# ============================================================================
# Вспомогательные функции для обратной совместимости
# ============================================================================


def make_calculated_keyword(**kwargs) -> CalculatedKeyword:
    """Создаёт CalculatedKeyword с Faker-данными.
    
    Обёртка над CalculatedKeywordFactory для обратной совместимости.
    
    Args:
        **kwargs: Параметры для CalculatedKeywordFactory
        
    Returns:
        CalculatedKeyword с заданными или сгенерированными данными
    """
    # Преобразуем плоские параметры в nested формат Factory Boy
    factory_kwargs = {}
    
    # Маппинг плоских параметров на nested
    flat_to_nested = {
        'text': 'keyword_setting__text',
        'hard_status': 'keyword_setting__hard_status',
        'relevant': 'keyword_setting__relevant',
        'keyword_setting_id': 'keyword_setting__id',
        'predict_ctr': 'keyword_setting__predict_ctr',
        'added_clicks': 'keyword_setting__added_clicks',
        'position': 'cluster_stat__position',
        'views': 'cluster_stat__views',
        'clicks': 'cluster_stat__clicks',
        'add_to_cart': 'cluster_stat__add_to_cart',
        'orders': 'cluster_stat__orders',
        'spend': 'cluster_stat__spend',
        'final_rating': 'cluster_stat__final_rating',
        'total_views': 'cluster_stat__views_all_time',
        'total_orders': 'cluster_stat__orders_all_time',
        'last_keyword_stat_updated': 'cluster_stat__timestamp',
        'status': 'state__status',
        'best_keyword_status': 'state__best_keyword_status',
        'reason': 'state__reason',
    }
    
    for flat_key, nested_key in flat_to_nested.items():
        if flat_key in kwargs:
            factory_kwargs[nested_key] = kwargs.pop(flat_key)
    
    # Добавляем оставшиеся параметры как есть
    factory_kwargs.update(kwargs)
    
    return CalculatedKeywordFactory(**factory_kwargs)


def make_keyword_setting_dto(**kwargs) -> KeywordSettingDTO:
    """Создаёт KeywordSettingDTO с Faker-данными."""
    return KeywordSettingDTOFactory(**kwargs)


def make_keyword_stat(**kwargs) -> KeywordStat:
    """Создаёт KeywordStat с Faker-данными."""
    # Преобразуем text в norm_query для pydantic модели
    if 'text' in kwargs:
        kwargs['norm_query'] = kwargs.pop('text')
    if 'last_keyword_stat_updated' in kwargs:
        kwargs['timestamp'] = kwargs.pop('last_keyword_stat_updated')
    if 'total_views' in kwargs:
        kwargs['views_all_time'] = kwargs.pop('total_views')
    if 'total_orders' in kwargs:
        kwargs['orders_all_time'] = kwargs.pop('total_orders')
    return KeywordStatFactory(**kwargs)


def make_keyword_state(**kwargs) -> KeywordState:
    """Создаёт KeywordState с Faker-данными."""
    return KeywordStateFactory(**kwargs)


# ============================================================================
# Генераторы списков
# ============================================================================


class KeywordsWithBest:
    """Результат генерации списка keywords с best_keyword."""

    def __init__(self, keywords: list[CalculatedKeyword]):
        self.keywords = keywords
        self._best: CalculatedKeyword | None = None

    @property
    def best(self) -> CalculatedKeyword:
        """Возвращает keyword с наивысшим rating_by_orders."""
        if self._best is None:
            self._best = max(self.keywords, key=lambda kw: kw.rating_by_orders)
        return self._best

    def __iter__(self):
        return iter(self.keywords)

    def __len__(self):
        return len(self.keywords)


def generate_keywords_with_best(
    count: int = 3,
    *,
    adv_id: int | None = None,
) -> KeywordsWithBest:
    """Генерирует список CalculatedKeyword с разными final_rating.

    Возвращает объект с доступом к списку и best_keyword.

    Пример:
        result = generate_keywords_with_best(count=3)
        keywords = result.keywords  # список всех keywords
        best = result.best  # keyword с наивысшим rating_by_orders

    Args:
        count: количество ключевых слов для генерации
        adv_id: ID рекламной кампании (общий для всех)

    Returns:
        KeywordsWithBest с keywords и best
    """
    _adv_id = adv_id if adv_id is not None else fake.random_int(1, 100000)

    # Генерируем уникальные final_rating для каждого keyword
    ratings = sorted(
        [fake.pyfloat(min_value=10.0, max_value=100.0) for _ in range(count)],
        reverse=True,
    )

    keywords = [
        CalculatedKeywordFactory(
            adv_id=_adv_id,
            cluster_stat__final_rating=round(rating, 2),
            keyword_setting__hard_status=HardStatus.IN_TEST,
        )
        for rating in ratings
    ]

    return KeywordsWithBest(keywords)


def generate_calculated_keywords(
    count: int = 5,
    *,
    adv_id: int | None = None,
    status_distribution: dict[KeywordStatus, int] | None = None,
) -> list[CalculatedKeyword]:
    """Генерирует список CalculatedKeyword.

    Args:
        count: количество ключевых слов для генерации
        adv_id: ID рекламной кампании (общий для всех)
        status_distribution: распределение статусов {KeywordStatus: count}
            Пример: {KeywordStatus.GOOD: 3, KeywordStatus.BAD: 2}

    Returns:
        Список CalculatedKeyword
    """
    _adv_id = adv_id if adv_id is not None else fake.random_int(1, 100000)
    result: list[CalculatedKeyword] = []

    if status_distribution:
        for status, num in status_distribution.items():
            for _ in range(num):
                if status == KeywordStatus.GOOD:
                    result.append(GoodKeywordFactory(adv_id=_adv_id))
                elif status == KeywordStatus.BAD:
                    result.append(BadKeywordFactory(adv_id=_adv_id))
                else:
                    result.append(TestingKeywordFactory(adv_id=_adv_id))
        return result

    # Генерация со случайным распределением
    for _ in range(count):
        choice = fake.random_int(0, 2)
        if choice == 0:
            result.append(GoodKeywordFactory(adv_id=_adv_id))
        elif choice == 1:
            result.append(BadKeywordFactory(adv_id=_adv_id))
        else:
            result.append(TestingKeywordFactory(adv_id=_adv_id))

    return result


# ============================================================================
# Экспорт
# ============================================================================

__all__ = [
    # Enum
    "HardStatus",
    # Factories
    "KeywordSettingDTOFactory",
    "KeywordStatFactory",
    "KeywordStateFactory",
    "PreCalculatedKeywordFactory",
    "CalculatedKeywordFactory",
    "GoodKeywordFactory",
    "BadKeywordFactory",
    "TestingKeywordFactory",
    "BestKeywordFactory",
    # Legacy functions
    "make_calculated_keyword",
    "make_keyword_setting_dto",
    "make_keyword_stat",
    "make_keyword_state",
    # Generators
    "KeywordsWithBest",
    "generate_keywords_with_best",
    "generate_calculated_keywords",
    # Faker instance
    "fake",
]
