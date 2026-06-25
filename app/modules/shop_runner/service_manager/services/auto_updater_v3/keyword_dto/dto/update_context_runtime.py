"""Runtime-сессия preamble: ledger, profiles, mutating contexts, tick report."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.modules.predict_keywords_target_place.clickhouse_manager.dto import (
    BidPosition,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.update_context_input import (
    UpdateContextInput,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.tick_ledger import (
    V3TickKeywordLedger,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_tick_report import (
    V3TickReportCollector,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
        KeywordV3Context,
    )


def _empty_v3_contexts() -> list[KeywordV3Context]:
    return []


@dataclass
class UpdateContextRuntime:
    """Исполнение NORMAL preamble; живёт в ``UpdateContext.runtime``."""

    adv_id: int
    tick_input: UpdateContextInput
    ledger: V3TickKeywordLedger
    raw_profiles: dict[str, list[BidPosition]]
    tick_report: V3TickReportCollector
    contexts: list[KeywordV3Context] = field(default_factory=_empty_v3_contexts)
    all_contexts: list[KeywordV3Context] = field(default_factory=_empty_v3_contexts)
