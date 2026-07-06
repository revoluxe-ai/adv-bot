"""Keyword-level data tier и eligibility для V3: FULL / PFO / NO DATA."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Literal

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
    ModeCandidate,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
    KeywordV3DecisionTier,
    keyword_has_own_conv,
    resolve_keyword_v3_decision,
    resolve_no_ch_operational_pay_for_order_cost,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_tier import (
    is_keyword_no_data,
    keyword_pfo_value,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder import (
    mode_level,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
        CampaignV3DecisionCache,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
        KeywordV3Context,
    )
    from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
        PositionProfilePoint,
    )

FallbackKind = Literal["none", "v2_cpo"]

_FULL_LADDER_TARGET_MODES: frozenset[KeywordStrategyMode] = frozenset(
    {
        KeywordStrategyMode.MIN_CPA,
        KeywordStrategyMode.OPTIMUM,
        KeywordStrategyMode.MAX_CONVERSION,
    }
)
_MIN_ONLY_TARGET_MODES: frozenset[KeywordStrategyMode] = frozenset(
    {KeywordStrategyMode.MIN_CPA}
)
_EMPTY_TARGET_MODES: frozenset[KeywordStrategyMode] = frozenset()


class KeywordDataTier(str, Enum):
    """Keyword-level tier: FULL / PFO / NO DATA."""

    KEYWORD_FULL = "keyword_full"
    KEYWORD_PFO = "keyword_pfo"
    KEYWORD_NO_DATA = "keyword_no_data"

    # Legacy aliases (logs/tests migration)
    KEYWORD_NO_CH_PROFILE_WITH_OWN_CONV = "keyword_pfo"
    KEYWORD_INVALID = "keyword_no_data"
    KEYWORD_PESSIMISTIC_FALLBACK = "keyword_pfo"


@dataclass(frozen=True, slots=True)
class KeywordV3Eligibility:
    """Eligibility ключа для ladder-фаз и preamble."""

    data_tier: KeywordDataTier
    allowed_modes: frozenset[KeywordStrategyMode]
    max_allowed_mode: KeywordStrategyMode
    participates_in_ladder: bool
    target_place_fallback_zero: bool
    imputed: bool
    fallback_kind: FallbackKind | None
    decision_tier: KeywordV3DecisionTier


def can_target_mode(
    eligibility: KeywordV3Eligibility,
    mode: KeywordStrategyMode,
) -> bool:
    """UP/realloc target: ``OFF`` всегда False; иначе ``mode in allowed_modes``."""
    if mode == KeywordStrategyMode.OFF:
        return False
    return mode in eligibility.allowed_modes


def _profile_has_ch_observed_usable_points(
    profile: list["PositionProfilePoint"],
) -> bool:
    """Есть ли в профиле CH-наблюдаемая точка с conv и bid (не синтетика ``_fill_positions``)."""
    for point in profile:
        if (
            point.ch_observed
            and point.predicted_conversion is not None
            and point.bid >= 0
        ):
            return True
    return False


def collapsed_ch_ladder_with_pay_for_order(
    ctx: "KeywordV3Context",
    catalog: dict[AggressionTargetMode, ModeCandidate] | None = None,
) -> bool:
    """CH-профиль есть, нет CH-observed M/O/C matrix, operational cost — ``pay_for_order``.

    Не смотрим на prod-каталог с ``include_synthetic_position_profile`` (синтетика
    может дать valid OPT/MAX при ``ch_observed=False``). Stored MIN → PFO в ladder/UI.
    """
    _ = catalog
    profile = ctx.position_profile
    if not profile:
        return False
    if _profile_has_ch_observed_usable_points(profile):
        return False
    return resolve_no_ch_operational_pay_for_order_cost(ctx.keyword) is not None


def min_cpa_operational_via_pay_for_order(
    ctx: "KeywordV3Context",
    eligibility: KeywordV3Eligibility | None,
    catalog: dict[AggressionTargetMode, ModeCandidate] | None = None,
) -> bool:
    """MIN через ``keyword.pay_for_order``: tier PFO или collapsed CH ladder + own PFO."""
    if eligibility is not None and eligibility.data_tier == KeywordDataTier.KEYWORD_PFO:
        return keyword_pfo_value(ctx.keyword) is not None
    if catalog is None:
        return False
    return collapsed_ch_ladder_with_pay_for_order(ctx, catalog)


def clamp_target_mode(
    eligibility: KeywordV3Eligibility,
    mode: KeywordStrategyMode,
) -> KeywordStrategyMode:
    """Ограничить целевой режим ``allowed_modes`` и ``max_allowed_mode``."""
    if not eligibility.allowed_modes:
        return KeywordStrategyMode.OFF
    if not can_target_mode(eligibility, mode):
        return eligibility.max_allowed_mode
    if mode_level(mode) > mode_level(eligibility.max_allowed_mode):
        return eligibility.max_allowed_mode
    return mode


def resolve_keyword_v3_eligibility(
    ctx: "KeywordV3Context",
    contexts: list["KeywordV3Context"],
    *,
    campaign_cache: "CampaignV3DecisionCache | None" = None,
    campaign_orders_per_cart_7d: float | None = None,
) -> KeywordV3Eligibility:
    """Свести данные ключа к ``KeywordDataTier`` FULL / PFO / NO DATA."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
        CampaignV3DecisionCache as _CampaignV3DecisionCache,
    )

    _ = campaign_orders_per_cart_7d
    cache = campaign_cache or _CampaignV3DecisionCache.from_contexts(contexts)
    decision = resolve_keyword_v3_decision(ctx, contexts, campaign_cache=cache)

    if is_keyword_no_data(ctx.keyword):
        return KeywordV3Eligibility(
            data_tier=KeywordDataTier.KEYWORD_NO_DATA,
            allowed_modes=_EMPTY_TARGET_MODES,
            max_allowed_mode=KeywordStrategyMode.OFF,
            participates_in_ladder=False,
            target_place_fallback_zero=True,
            imputed=False,
            fallback_kind=None,
            decision_tier=decision.tier,
        )

    if (
        decision.tier == KeywordV3DecisionTier.FULL
        and decision.effective_conv_views_to_orders is not None
    ):
        return KeywordV3Eligibility(
            data_tier=KeywordDataTier.KEYWORD_FULL,
            allowed_modes=_FULL_LADDER_TARGET_MODES,
            max_allowed_mode=KeywordStrategyMode.MAX_CONVERSION,
            participates_in_ladder=True,
            target_place_fallback_zero=False,
            imputed=False,
            fallback_kind="none",
            decision_tier=decision.tier,
        )

    return KeywordV3Eligibility(
        data_tier=KeywordDataTier.KEYWORD_PFO,
        allowed_modes=_MIN_ONLY_TARGET_MODES,
        max_allowed_mode=KeywordStrategyMode.MIN_CPA,
        participates_in_ladder=True,
        target_place_fallback_zero=True,
        imputed=False,
        fallback_kind="none" if keyword_has_own_conv(ctx.keyword) else "v2_cpo",
        decision_tier=decision.tier,
    )


def build_eligibility_map(
    contexts: list["KeywordV3Context"],
    *,
    campaign_orders_per_cart_7d: float | None = None,
) -> dict[int, KeywordV3Eligibility]:
    """Индекс eligibility по ``keyword_setting_original_id``."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
        CampaignV3DecisionCache,
    )

    campaign_cache = CampaignV3DecisionCache.from_contexts(contexts)
    result: dict[int, KeywordV3Eligibility] = {}
    for ctx in contexts:
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id <= 0:
            continue
        result[ks_id] = resolve_keyword_v3_eligibility(
            ctx,
            contexts,
            campaign_cache=campaign_cache,
            campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
        )
    return result


def build_target_place_fallback_zero_by_keyword_id(
    contexts: list["KeywordV3Context"],
    *,
    campaign_orders_per_cart_7d: float | None = None,
) -> dict[int, bool]:
    """Построить карту принудительного сброса ``target_place`` в 0 по ключам V3.

    Используется на этапе подготовки тика V3 (``orchestrator``, ``DataUpdateManager``,
    ``ApplyManager``) и передаётся в ``sync_keyword_target_places_v3`` как
    ``target_place_fallback_zero_by_keyword_id`` при режиме кампании
    ``CampaignMode.NORMAL`` (в отличие от ``force_all_target_place_zero`` для
    ``CampaignMode.NO_DATA``).

    Для каждого ключа с ``keyword_setting_original_id > 0`` вычисляет, нужно ли при
    синхронизации в PostgreSQL записать ``KeywordSetting.target_place = 0``
    (``NO_DATA_TARGET_PLACE_FALLBACK``) вместо расчёта по ladder-профилю позиций.
    Значение ``True`` означает «force 0» только для **управляемых** ключей
    (``hard_status`` managed) — фильтр применяется уже в ``sync_keyword_target_places_v3``.

    После рефакторинга NF bootstrap эта карта больше не является местом, где
    no-CH ключи получают стартовый ``target_place``. Для PFO/GAP ключей карта
    всегда возвращает ``False``: bootstrap и дальнейшая коррекция происходят в
    preamble-фазах ``NotFullValidateExecutor`` → ``NotFullTargetPlaceMigrateExecutor``
    → ``NotFullTargetPlacePlanFactExecutor``.

    То есть sync-слой здесь выполняет только сохранение уже подготовленного
    состояния. Он не должен заново инициализировать no-CH ключ, не должен
    подменять bootstrap-логику NF и не должен делать overspend-reset в 0 для
    PFO/GAP.

    Алгоритм (по приоритету для одного ``KeywordV3Context``):

    1. **Пропуск** — ``ks_id <= 0`` не попадает в результат.
    2. **PFO/GAP active** — есть operational ``pay_for_order`` без
       ``position_profile`` либо нет operational ``pay_for_order`` вообще, но
       ``strategy_mode != OFF``:
       всегда ``False`` — sync **не** форсит 0; ``target_place`` для PFO/GAP
       управляется отдельно в preamble (validate → migrate → plan-fact), а sync
       только уважает уже подготовленное значение из ledger/Redis. Это ключевой
       контракт: bootstrap no-CH ключа больше не происходит на стадии sync.
    3. **Остальные случаи** — ``elig.target_place_fallback_zero`` из
       ``resolve_keyword_v3_eligibility``, но только если ``strategy_mode != OFF``:

       - ``KeywordV3DecisionTier.FULL`` → ``target_place_fallback_zero=False`` →
         ``False`` в карте: позиция считается по полному CH-профилю;
       - ``KEYWORD_PFO`` / ``KEYWORD_NO_DATA`` → ``target_place_fallback_zero=True`` →
         ``True`` в карте: нет достаточных данных для ladder, min-bid fallback;
       - ``OFF`` → всегда ``False``, даже если tier NO_DATA/PFO в eligibility
         (ключ выключен — sync не перезаписывает ``target_place`` через fallback).

    Карта согласована с ``build_eligibility_map`` для контекстов **с** профилем
    (FULL/PFO/NO_DATA без ветки PFO/GAP active). Для PFO/GAP поведение
    намеренно расходится: eligibility может давать ``target_place_fallback_zero=True``,
    но sync не должен сбрасывать такой ключ в ``0`` — этот контур обслуживается
    отдельно NF pipeline-ом. Это сделано специально, чтобы один и тот же
    bootstrap-контракт не реализовывался в двух местах с разной семантикой.

    Args:
        contexts: Все ``KeywordV3Context`` тика (managed + operable); общий
            ``CampaignV3DecisionCache`` строится один раз на список.
        campaign_orders_per_cart_7d: Пробрасывается в ``resolve_keyword_v3_eligibility``
            (зарезервировано для campaign-level CPO; сейчас не меняет tier внутри
            eligibility, но сохраняет единый контракт вызова с preamble/sync).
    Returns:
        Словарь ``keyword_setting_original_id → force_zero``. Отсутствующий ``ks_id``
        в sync трактуется как ``False`` (``.get(ks_id, False)``). Побочных эффектов
        нет (только чтение контекстов и eligibility).

    См. также:
        ``sync_keyword_target_places_v3`` — потребитель карты при ``CAMPAIGN_NORMAL``;
        ``KeywordV3Eligibility.target_place_fallback_zero`` — источник флага для
        ключей с профилем.
    """
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
        CampaignV3DecisionCache,
    )

    campaign_cache = CampaignV3DecisionCache.from_contexts(contexts)
    out: dict[int, bool] = {}
    for ctx in contexts:
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id <= 0:
            continue
        elig = resolve_keyword_v3_eligibility(
            ctx,
            contexts,
            campaign_cache=campaign_cache,
            campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
        )
        mode = ctx.keyword.keyword_setting.strategy_mode
        if (
            mode != KeywordStrategyMode.OFF
            and (
                not bool(ctx.position_profile)
                or is_keyword_no_data(ctx.keyword)
            )
        ):
            out[int(ks_id)] = False
            continue
        out[int(ks_id)] = (
            elig.target_place_fallback_zero and mode != KeywordStrategyMode.OFF
        )
    return out
