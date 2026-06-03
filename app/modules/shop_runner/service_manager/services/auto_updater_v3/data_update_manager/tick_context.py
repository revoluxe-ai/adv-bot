"""Пересборка operable-контекстов и prepared после apply фазы."""

from __future__ import annotations

from app.modules.predict_keywords_target_place.clickhouse_manager.dto import BidPosition
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_contexts import (
    build_keyword_v3_contexts,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
    KeywordV3Eligibility,
    build_eligibility_map,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
    LadderInputs,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.tick_ledger import (
    V3TickKeywordLedger,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    PreparedList,
    build_prepared_from_contexts,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_operable_keywords import (
    filter_operable_v3_contexts,
)


def apply_v3_phase(
    ledger: V3TickKeywordLedger,
    actions: list[V3Action],
    raw_profiles: dict[str, list[BidPosition]],
) -> list[KeywordV3Context]:
    """Применить фазу in-memory и пересобрать контексты (все ключи)."""
    if actions:
        ledger.apply_in_memory(actions)
    return build_keyword_v3_contexts(ledger.keywords, raw_profiles)


def apply_v3_phase_operable(
    ledger: V3TickKeywordLedger,
    actions: list[V3Action],
    raw_profiles: dict[str, list[BidPosition]],
) -> tuple[list[KeywordV3Context], list[KeywordV3Context]]:
    """Применить фазу; вернуть (operable_contexts, all_contexts)."""
    all_contexts = apply_v3_phase(ledger, actions, raw_profiles)
    return filter_operable_v3_contexts(all_contexts), all_contexts


def prepare_v3_operable_ladder_contexts(
    ledger: V3TickKeywordLedger,
    raw_profiles: dict[str, list[BidPosition]],
    all_contexts: list[KeywordV3Context],
) -> tuple[list[KeywordV3Context], list[KeywordV3Context]]:
    """Filter operable (1|2) и rebuild contexts."""
    _ = ledger
    _ = filter_operable_v3_contexts(all_contexts)
    all_contexts = build_keyword_v3_contexts(ledger.keywords, raw_profiles)
    operable_contexts = filter_operable_v3_contexts(all_contexts)
    return operable_contexts, all_contexts


def refresh_v3_tick_state(
    contexts: list[KeywordV3Context],
    *,
    campaign_orders_per_cart_7d: float | None,
    rec_orders_per_view: float | None,
) -> tuple[PreparedList, dict[int, KeywordV3Eligibility], LadderInputs]:
    """Пересобрать prepared, eligibility и ladder_inputs после preamble-фазы."""
    eligibility = build_eligibility_map(
        contexts,
        campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
    )
    prepared = build_prepared_from_contexts(contexts)
    ladder_inputs = LadderInputs.from_contexts(
        contexts,
        campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
        rec_orders_per_view=rec_orders_per_view,
    )
    return prepared, eligibility, ladder_inputs
