"""Launch-validity soft-gate: предупреждение о низком объёме показов за 24ч.

Spec ``card-ab-hold-mode`` — Requirement «Enable warns when candidate test
keywords have too few recent impressions». Decision
``card-ab-hold-write-path-ownership`` §2c: это **soft-gate** (предупреждение, а не
hard block, в отличие от freshness §2a и пустого allowed-set §8). После
прохождения freshness-гейта, но до записи ``PENDING_SETUP`` + Redis ENTER, enable
оценивает суммарные показы ключей-кандидатов теста за окно последних 24ч. Если
сумма ниже порога — пользователю показывается причина (мало показов для надёжного
A/B), рекомендация поднять план max CPO и повторить, и явный выбор «всё равно
запустить» / «отмена»; mode остаётся ``OFF`` до выбора.

Источник показов — существующий CH-агрегат
``full_wb_adv_stat.get_keywords_views_by_days`` (MV ``default_db.mv_clusters_daily_agg``),
что избегает нового ClickHouse-контракта. Кандидаты — ключи кампании, несущие
тест (те же adv, что участвуют в setup); агрегат берётся на уровне кампании.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import (
    full_wb_adv_stat,
)

# Минимальный суммарный объём показов ключей-кандидатов за 24ч для надёжного A/B
# (decision §2c). Ниже порога → soft-warning с выбором «запустить / отмена».
AB_HOLD_MIN_TOTAL_VIEWS_24H = 1000

# Окно оценки объёма теста — последние сутки (MV агрегирует посуточно).
_RECENT_VIEWS_WINDOW = timedelta(hours=24)


def sum_recent_keyword_views(views_by_day: dict[date, int]) -> int:
    """Суммарные показы ключей за окно (pure, из посуточного CH-агрегата).

    Args:
        views_by_day: ``{дата: показы за день}`` из ``get_keywords_views_by_days``.

    Returns:
        Неотрицательная сумма показов за все дни окна.
    """
    return sum(int(v) for v in views_by_day.values())


def is_low_recent_impressions(
    total_views: int,
    *,
    threshold: int = AB_HOLD_MIN_TOTAL_VIEWS_24H,
) -> bool:
    """True, если объём показов ниже порога (нужен soft-warning §2c).

    Равенство порогу — достаточный объём (``>= threshold`` → не low), симметрично
    остальным ENTER-критериям режима.
    """
    return int(total_views) < int(threshold)


def candidate_views_adv_ids(adv_setting: AdvSetting | object) -> list[int]:
    """adv_id кампании (+ парный поиск) для CH-агрегата показов кандидатов.

    Ключи-кандидаты теста живут в кампании и её парном поисковом adv; агрегат
    ``mv_clusters_daily_agg`` группируется по ``adv_id``, поэтому передаём оба id.
    """
    ids: list[int] = []
    adv_id = getattr(adv_setting, "adv_id", None)
    if adv_id:
        ids.append(int(adv_id))
    search_adv_id = getattr(adv_setting, "search_adv_id", None)
    if search_adv_id:
        ids.append(int(search_adv_id))
    return sorted(set(ids))


async def aggregate_candidate_views_24h(
    adv_setting: AdvSetting | object,
    *,
    now: datetime | None = None,
) -> int:
    """Суммарные показы ключей-кандидатов за последние 24ч (read-only CH reuse).

    Реюз ``get_keywords_views_by_days`` (MV ``mv_clusters_daily_agg``) — без нового
    CH-контракта. При отсутствии adv_id или ошибке CH (пустой dict) вернёт 0.

    Args:
        adv_setting: кампания, для которой оценивается объём теста.
        now: точка отсчёта окна (для тестов); по умолчанию ``datetime.now()``.

    Returns:
        Суммарные показы ключей за окно последних 24ч.
    """
    adv_ids = candidate_views_adv_ids(adv_setting)
    if not adv_ids:
        return 0
    end = now or datetime.now()
    start = end - _RECENT_VIEWS_WINDOW
    views_by_day = await full_wb_adv_stat.get_keywords_views_by_days(
        adv_ids, start, end
    )
    return sum_recent_keyword_views(views_by_day)


async def evaluate_ab_hold_launch_view_volume(
    adv_setting: AdvSetting | object,
    *,
    threshold: int = AB_HOLD_MIN_TOTAL_VIEWS_24H,
    now: datetime | None = None,
) -> tuple[bool, int]:
    """Оценить объём теста для enable (§2c soft-gate).

    Returns:
        ``(sufficient, total_views)``. ``sufficient=False`` → показать warning с
        выбором; mode остаётся ``OFF`` до подтверждения «всё равно запустить».
    """
    total = await aggregate_candidate_views_24h(adv_setting, now=now)
    return (not is_low_recent_impressions(total, threshold=threshold)), total


def build_ab_hold_low_views_warning_message(
    total_views: int,
    *,
    threshold: int = AB_HOLD_MIN_TOTAL_VIEWS_24H,
) -> str:
    """Полный текст soft-warning: причина + рекомендация + выбор (spec §2c).

    Внутри лимита sendMessage (4096); проверяется payload-limit тестом.
    """
    return (
        "Мало показов для надёжного A/B-теста.\n\n"
        f"Суммарные показы ключей за последние 24 часа: {int(total_views)} "
        f"(рекомендуется от {int(threshold)}).\n\n"
        "На таком объёме результат теста статистически ненадёжен. "
        "Рекомендуем поднять план max CPO и немного подождать — тогда больше "
        "ключей наберут показы, — и повторить включение.\n\n"
        "Можно всё равно запустить тест (на ваш риск) или отменить включение."
    )


def build_ab_hold_low_views_alert(
    total_views: int,
    *,
    threshold: int = AB_HOLD_MIN_TOTAL_VIEWS_24H,
) -> str:
    """Короткий ``answerCallbackQuery`` (лимит Telegram ≤200) для §2c warning."""
    text = (
        f"Мало показов за 24ч ({int(total_views)} из {int(threshold)}). "
        "Выберите: запустить всё равно или отменить."
    )
    if len(text) <= 200:
        return text
    return "Мало показов за 24ч для надёжного A/B. Выберите действие ниже."
