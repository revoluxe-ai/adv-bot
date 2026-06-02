"""Конфигурация пакета ``snapshot_data_updater``.

Все флаги и таймауты читаются из переменных окружения при импорте модуля
(см. ``SnapshotUpdaterConfig.from_env()`` и глобальный ``DEFAULT_CONFIG``).

Важно про режимы stub / live
-----------------------------
**``use_live_updater=False`` (значение по умолчанию)** — «безопасный» режим разработки
и unit-тестов:

- фабрика ``build_snapshot_updater()`` собирает **stub-стек**:
  ``StubPostgresSnapshotProvider``, ``StubRedisSnapshotProvider``,
  ``StubClickHouseSnapshotProvider``;
- **нет** реальных подключений к Postgres, Redis, ClickHouse;
- ``RedisAdvDataSnapshotStore`` работает в режиме **no-op** (только лог save);
- процесс можно поднять локально/в CI без БД.

**``use_live_updater=True``** (env: ``SNAPSHOT_UPDATER_USE_LIVE=1``) — production/shadow
контур с реальным read-only I/O:

- ``PostgresSnapshotProviderLive`` — активные РК из PG;
- ``RedisSnapshotProviderLive`` — чтение ``calculated_keywords:{adv_id}``, min_bids v2;
- ``ClickHouseSnapshotProviderLive`` — batch plan/fact, cluster texts;
- ``CalculatedKeywordsWarmupService`` — прогрев ключей через существующий
  ``get_good_bad_phrases``;
- снимки **пишутся** в Redis (новый namespace ``adv_snapshot:v1:...``).

Переключение live **не** меняет поведение ``shop_runner`` само по себе: consumers
(``update_cluster_bids``, ``get_wb_advs_dto``) подключаются отдельными флагами
(``SNAPSHOT_CLUSTER_BIDS_*``, ``SNAPSHOT_WB_ADV_DTO_*``).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from app.snapshot_data_updater.freshness_policy import FreshnessPolicy


def _env_bool(name: str, default: bool = False) -> bool:
    """Парсит env-переменную как bool (1/true/yes/on)."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    """Парсит env-переменную как float."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return float(raw)


def _env_optional_float(name: str) -> float | None:
    """Парсит env-переменную как float; пустое/отсутствующее → ``None``."""
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return None
    return float(raw)


def _env_int(name: str, default: int) -> int:
    """Парсит env-переменную как int."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return int(raw)


def _freshness_policy_from_env(
    prefix: str,
    *,
    default_skip: float,
    default_stale: float,
    legacy_stale_env: str | None = None,
    legacy_stale_default: float | None = None,
) -> FreshnessPolicy:
    """Собирает ``FreshnessPolicy`` из ``SNAPSHOT_{PREFIX}_SKIP_REFRESH_SEC`` / ``_STALE_SEC``."""
    skip = _env_float(f"SNAPSHOT_{prefix}_SKIP_REFRESH_SEC", default_skip)
    stale_default = default_stale
    if legacy_stale_env is not None:
        stale_default = _env_float(legacy_stale_env, legacy_stale_default or default_stale)
    stale = _env_float(f"SNAPSHOT_{prefix}_STALE_SEC", stale_default)
    return FreshnessPolicy(skip_refresh_sec=skip, stale_sec=stale)


@dataclass(frozen=True, slots=True)
class SnapshotUpdaterConfig:
    """Единый конфиг snapshot updater и consumer adapters.

    Поля соответствуют env-переменным (см. ``from_env``). Значения по умолчанию
  подобраны для безопасного локального запуска (всё выключено, stub path).
    """

    # --- Режим updater (stub vs live) ---

    use_live_updater: bool = False
    """Если ``False`` (по умолчанию): stub-провайдеры, без реального PG/Redis/CH.

    Если ``True`` (``SNAPSHOT_UPDATER_USE_LIVE=1``): live read-only провайдеры,
    warmup ключей, запись snapshot в Redis. Включать только после GO на shadow/deploy.
    """

    # --- Прогрев calculated_keywords ---

    keywords_policy: FreshnessPolicy = FreshnessPolicy(
        skip_refresh_sec=300.0, stale_sec=900.0
    )
    """Keywords (``calculated_keywords`` + meta): skip refresh / stale при чтении."""

    snapshot_adv_policy: FreshnessPolicy = FreshnessPolicy(
        skip_refresh_sec=300.0, stale_sec=900.0
    )
    """Per-adv snapshot ``collected_at``: skip shop refresh / stale при чтении."""

    shop_policy: FreshnessPolicy = FreshnessPolicy(
        skip_refresh_sec=300.0, stale_sec=0.0
    )
    """Shop batch ``collected_at``: только skip целого ``RefreshShopSnapshotTask``."""

    plan_fact_policy: FreshnessPolicy = FreshnessPolicy(
        skip_refresh_sec=300.0, stale_sec=900.0
    )
    """Plan/fact в snapshot (CH); зарезервировано для section-skip в collector."""

    cluster_texts_policy: FreshnessPolicy = FreshnessPolicy(
        skip_refresh_sec=300.0, stale_sec=900.0
    )
    """Cluster texts (CH); зарезервировано для section-skip."""

    min_bids_policy: FreshnessPolicy = FreshnessPolicy(
        skip_refresh_sec=300.0, stale_sec=900.0
    )
    """Min bids (Redis); зарезервировано для section-skip."""

    keywords_strict_freshness: bool = False
    """Если ``True``: hash ``calculated_keywords:{adv_id}`` без metadata = stale,
    принудительный пересчёт. Если ``False``: hash без metadata можно использовать
    (режим unknown freshness)."""

    cache_max_age_sec: float = 0.0
    """Устаревшее: дублирует ``snapshot_adv_policy.stale_sec`` (legacy env
    ``SNAPSHOT_CACHE_MAX_AGE_SEC``). Предпочтительно ``SNAPSHOT_ADV_STALE_SEC``."""

    # --- Хранилище snapshot ---

    snapshot_ttl_sec: int = 3600
    """TTL ключей snapshot в Redis (секунды)."""

    snapshot_schema_version: int = 1
    """Версия схемы DTO; consumer отклоняет snapshot с другой версией."""

    # --- update_cluster_bids (consumer) ---

    cluster_bids_shadow_compare: bool = False
    """Shadow: сравнить кол-во keywords snapshot vs legacy, только логи."""

    cluster_bids_read_from_snapshot: bool = False
    """Read cutover: при fresh snapshot читать keywords через Redis cache_only
    (после warmup), иначе strict ``adv.get_keywords()`` (Redis)."""

    # --- get_wb_advs_dto / V3 (consumer) ---

    wb_adv_dto_shadow_compare: bool = False
    """Shadow: лог расхождений keywords snapshot vs legacy в WBAdvDTO path."""

    wb_adv_dto_read_from_snapshot: bool = False
    """Зарезервировано для read cutover WBAdvDTO (пока shadow-only в adapter)."""

    # --- Scheduling SnapshotUpdater ---

    refresh_interval_sec: float = 300.0
    """Интервал global tick (сек). На каждом tick — discover shops и shop tasks."""

    tick_policy: str = "skip"
    """Поведение при пересечении global tick: ``skip`` — пропустить tick с warning;
    ``wait`` — дождаться завершения предыдущего tick (блокировка на Lock)."""

    resource_task_timeout_sec: float = 30.0
    """Таймаут задач **Redis**-очереди collector (``ResourceQueue``, сек).

    Env: ``SNAPSHOT_RESOURCE_TASK_TIMEOUT_SEC``. Ограничивает batch min_bids / keywords
    в snapshot tick; не относится к PG/CH/warmup (см. ``resource_queue`` module docstring).
    """

    postgres_task_timeout_sec: float | None = None
    """Зарезервировано. Env: ``SNAPSHOT_PG_TASK_TIMEOUT_SEC``.

    PG в collector не использует ``ResourceQueue`` — лимит запросов через
    ``POSTGRES_QUERY_CONCURRENCY`` и таймауты ``session_maker``. Поле оставлено для
    возможного будущего wiring; на поведение snapshot сейчас не влияет.
    """

    @property
    def keywords_freshness_sec(self) -> float:
        """Обратная совместимость: верхняя граница «свежих» keywords = ``stale_sec``."""
        return self.keywords_policy.stale_sec

    @classmethod
    def from_env(cls) -> SnapshotUpdaterConfig:
        """Собирает конфиг из переменных окружения (вызывается при старте процесса)."""
        legacy_cache_max = _env_float("SNAPSHOT_CACHE_MAX_AGE_SEC", 0.0)
        adv_stale_default = legacy_cache_max if legacy_cache_max > 0 else 900.0
        keywords_policy = _freshness_policy_from_env(
            "KEYWORDS",
            default_skip=300.0,
            default_stale=900.0,
            legacy_stale_env="SNAPSHOT_KEYWORDS_FRESHNESS_SEC",
            legacy_stale_default=900.0,
        )
        snapshot_adv_policy = _freshness_policy_from_env(
            "ADV",
            default_skip=300.0,
            default_stale=adv_stale_default,
            legacy_stale_env="SNAPSHOT_CACHE_MAX_AGE_SEC",
            legacy_stale_default=adv_stale_default,
        )
        return cls(
            use_live_updater=_env_bool("SNAPSHOT_UPDATER_USE_LIVE", False),
            keywords_policy=keywords_policy,
            snapshot_adv_policy=snapshot_adv_policy,
            shop_policy=_freshness_policy_from_env(
                "SHOP", default_skip=300.0, default_stale=0.0
            ),
            plan_fact_policy=_freshness_policy_from_env(
                "PLAN_FACT", default_skip=300.0, default_stale=900.0
            ),
            cluster_texts_policy=_freshness_policy_from_env(
                "CLUSTER_TEXTS", default_skip=300.0, default_stale=900.0
            ),
            min_bids_policy=_freshness_policy_from_env(
                "MIN_BIDS", default_skip=300.0, default_stale=900.0
            ),
            keywords_strict_freshness=_env_bool(
                "SNAPSHOT_KEYWORDS_STRICT_FRESHNESS", False
            ),
            cache_max_age_sec=snapshot_adv_policy.stale_sec,
            snapshot_ttl_sec=_env_int("SNAPSHOT_REDIS_TTL_SEC", 3600),
            snapshot_schema_version=_env_int("SNAPSHOT_SCHEMA_VERSION", 1),
            cluster_bids_shadow_compare=_env_bool(
                "SNAPSHOT_CLUSTER_BIDS_SHADOW", False
            ),
            cluster_bids_read_from_snapshot=_env_bool(
                "SNAPSHOT_CLUSTER_BIDS_READ", False
            ),
            wb_adv_dto_shadow_compare=_env_bool("SNAPSHOT_WB_ADV_DTO_SHADOW", False),
            wb_adv_dto_read_from_snapshot=_env_bool(
                "SNAPSHOT_WB_ADV_DTO_READ", False
            ),
            refresh_interval_sec=_env_float(
                "SNAPSHOT_REFRESH_INTERVAL_SEC", 300.0
            ),
            tick_policy=os.getenv("SNAPSHOT_TICK_POLICY", "skip").strip().lower(),
            resource_task_timeout_sec=_env_float(
                "SNAPSHOT_RESOURCE_TASK_TIMEOUT_SEC", 30.0
            ),
            postgres_task_timeout_sec=_env_optional_float(
                "SNAPSHOT_PG_TASK_TIMEOUT_SEC"
            ),
        )


_cached_config: SnapshotUpdaterConfig | None = None


def get_snapshot_config() -> SnapshotUpdaterConfig:
    """Возвращает конфиг snapshot (кэш на процесс).

    Вызывайте ``reload_snapshot_config()`` после ``dotenv.load_dotenv()`` в entrypoint,
    чтобы подхватить ``SNAPSHOT_*`` из ``.env``.
    """
    global _cached_config
    if _cached_config is None:
        _cached_config = SnapshotUpdaterConfig.from_env()
    return _cached_config


def reload_snapshot_config() -> SnapshotUpdaterConfig:
    """Перечитывает env (после load_dotenv) и сбрасывает кэш."""
    global _cached_config
    _cached_config = SnapshotUpdaterConfig.from_env()
    return _cached_config


def resolve_snapshot_config(
    config: SnapshotUpdaterConfig | None,
) -> SnapshotUpdaterConfig:
    """Возвращает явный конфиг или актуальный из env-кэша."""
    return config if config is not None else get_snapshot_config()


class _SnapshotConfigProxy:
    """Прокси для обратной совместимости с ``DEFAULT_CONFIG.field``."""

    def __getattr__(self, name: str) -> Any:
        return getattr(get_snapshot_config(), name)


DEFAULT_CONFIG = _SnapshotConfigProxy()
