"""Launch-validity soft-gate: предупреждение о низком объёме показов кампании.

Spec ``card-ab-hold-mode`` — Requirement «Enable warns when campaign recent
keyword impressions are too low». Decision ``card-ab-hold-write-path-ownership``
§2c: это **soft-gate** (предупреждение, а не hard block, в отличие от freshness
§2a и пустого allowed-set §8). После прохождения freshness-гейта, но до записи
``PENDING_SETUP`` + Redis ENTER, enable оценивает **campaign-level proxy** Σ
keyword views: реюз ``full_wb_adv_stat.get_keywords_views_by_days`` (MV
``default_db.mv_clusters_daily_agg``) по ``adv_id`` (+ парный ``search_adv_id``).
Зерно окна — **календарные сутки MV**, покрывающие last-24h wall-clock (не true
rolling 24h). При измеренной Σ ниже порога — warn + выбор «всё равно запустить» /
«отмена»; mode ``OFF`` до выбора. При CH error — отдельный soft reason (объём
временно недоступен), без low-impressions copy и без ENTER.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum

from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import (
    full_wb_adv_stat,
)

# Минимальная измеренная Σ campaign-level keyword views (calendar-day MV cover)
# для надёжного A/B (decision §2c). Ниже порога → soft-warning с выбором.
AB_HOLD_MIN_TOTAL_VIEWS_24H = 1000

# Окно last-24h wall-clock; MV агрегирует посуточно → inclusive calendar days.
_RECENT_VIEWS_WINDOW = timedelta(hours=24)


class LaunchViewVolumeOutcome(str, Enum):
    """Результат оценки объёма для enable soft-gate (§2c)."""

    SUFFICIENT = "sufficient"
    LOW = "low"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class LaunchViewVolumeEvaluation:
    """Оценка campaign-level объёма показов для enable (§2c).

    Attributes:
        outcome: достаточный объём, низкий (measured) или CH unavailable.
        total_views: сумма только при measured outcome; иначе 0.
    """

    outcome: LaunchViewVolumeOutcome
    total_views: int = 0

    @property
    def is_sufficient(self) -> bool:
        """True, если measured Σ ≥ порога."""
        return self.outcome == LaunchViewVolumeOutcome.SUFFICIENT

    @property
    def is_unavailable(self) -> bool:
        """True, если CH-запрос не удался (не трактуем как 0 показов)."""
        return self.outcome == LaunchViewVolumeOutcome.UNAVAILABLE


def sum_recent_keyword_views(views_by_day: dict[date, int]) -> int:
    """Суммарные показы keyword-clusters за окно (pure, посуточный CH-агрегат).

    Args:
        views_by_day: ``{дата: показы за календарный день}`` из
            ``get_keywords_views_by_days``.

    Returns:
        Неотрицательная сумма показов за все дни окна.
    """
    return sum(int(v) for v in views_by_day.values())


def is_low_recent_impressions(
    total_views: int,
    *,
    threshold: int = AB_HOLD_MIN_TOTAL_VIEWS_24H,
) -> bool:
    """True, если измеренный объём ниже порога (нужен soft-warning §2c).

    Равенство порогу — достаточный объём (``>= threshold`` → не low), симметрично
    остальным ENTER-критериям режима.
    """
    return int(total_views) < int(threshold)


def candidate_views_adv_ids(adv_setting: AdvSetting | object) -> list[int]:
    """adv_id кампании (+ парный поиск) для CH campaign-level агрегата показов.

    Агрегат ``mv_clusters_daily_agg`` группируется по ``adv_id``; для proxy Σ
    передаём основной и парный поисковый adv.
    """
    ids: list[int] = []
    adv_id = getattr(adv_setting, "adv_id", None)
    if adv_id:
        ids.append(int(adv_id))
    search_adv_id = getattr(adv_setting, "search_adv_id", None)
    if search_adv_id:
        ids.append(int(search_adv_id))
    return sorted(set(ids))


async def fetch_campaign_keyword_views_by_days(
    adv_setting: AdvSetting | object,
    *,
    now: datetime | None = None,
) -> dict[date, int] | None:
    """Посуточный CH-агрегат campaign-level views для soft-gate (read-only reuse).

    Returns:
        ``None`` — CH unavailable / query error (пустой ``{}`` при наличии adv_id).
        ``{}`` — нет adv_id (measured zero без CH).
        Иначе — measured dict (успешный CH, в т.ч. нулевые сутки).
    """
    adv_ids = candidate_views_adv_ids(adv_setting)
    if not adv_ids:
        return {}
    end = now or datetime.now()
    start = end - _RECENT_VIEWS_WINDOW
    views_by_day = await full_wb_adv_stat.get_keywords_views_by_days(
        adv_ids, start, end
    )
    if not views_by_day:
        return None
    return views_by_day


async def aggregate_candidate_views_24h(
    adv_setting: AdvSetting | object,
    *,
    now: datetime | None = None,
) -> int | None:
    """Суммарные measured campaign-level views за calendar-day cover (§2c).

    Returns:
        ``None`` при CH error; иначе неотрицательная сумма (в т.ч. 0 при measured).
    """
    views_by_day = await fetch_campaign_keyword_views_by_days(adv_setting, now=now)
    if views_by_day is None:
        return None
    return sum_recent_keyword_views(views_by_day)


async def evaluate_ab_hold_launch_view_volume(
    adv_setting: AdvSetting | object,
    *,
    threshold: int = AB_HOLD_MIN_TOTAL_VIEWS_24H,
    now: datetime | None = None,
) -> LaunchViewVolumeEvaluation:
    """Оценить campaign-level объём для enable (§2c soft-gate).

    Returns:
        ``LaunchViewVolumeEvaluation``. ``LOW`` → warning с выбором;
        ``UNAVAILABLE`` → distinct soft reason; mode ``OFF`` в обоих случаях.
    """
    views_by_day = await fetch_campaign_keyword_views_by_days(adv_setting, now=now)
    if views_by_day is None:
        return LaunchViewVolumeEvaluation(
            outcome=LaunchViewVolumeOutcome.UNAVAILABLE,
            total_views=0,
        )
    total = sum_recent_keyword_views(views_by_day)
    if is_low_recent_impressions(total, threshold=threshold):
        return LaunchViewVolumeEvaluation(
            outcome=LaunchViewVolumeOutcome.LOW,
            total_views=total,
        )
    return LaunchViewVolumeEvaluation(
        outcome=LaunchViewVolumeOutcome.SUFFICIENT,
        total_views=total,
    )


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
        "Суммарные показы keyword-clusters кампании за календарные сутки MV "
        f"(окно последних 24ч): {int(total_views)} "
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
    """Короткий ``answerCallbackQuery`` (лимит Telegram ≤200) для §2c low warning."""
    text = (
        f"Мало показов (сутки MV / последние 24ч): {int(total_views)} из "
        f"{int(threshold)}. Выберите: запустить всё равно или отменить."
    )
    if len(text) <= 200:
        return text
    return "Мало показов для надёжного A/B. Выберите действие ниже."


def build_ab_hold_views_unavailable_message() -> str:
    """Полный текст soft-reason при недоступности CH-статы объёма (§2c).

    Отдельный от low-impressions warning: пользователь не видит «0 показов».
    """
    return (
        "Статистика показов кампании временно недоступна.\n\n"
        "Не удалось получить объём keyword views из ClickHouse (календарные "
        "сутки MV за последние 24ч). Повторите включение A/B Hold позже.\n\n"
        "Режим не включён. ENTER не отправлен."
    )


def build_ab_hold_views_unavailable_alert() -> str:
    """Короткий alert при CH error на soft-gate (§2c, ≤200 символов)."""
    return (
        "Статистика показов временно недоступна. "
        "Повторите включение позже."
    )
