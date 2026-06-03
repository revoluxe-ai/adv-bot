"""DTO загрузки данных тика V3."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.modules.predict_keywords_target_place.clickhouse_manager.dto import (
    BidPosition,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.plan_fact_change_redis_caches import (
    ChangePlanFact,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    SalesStates,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_step_state_cache import (
    V3CalibrationStepState,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_views_cache import (
    ChangePlanFactViews,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
    KeywordV3Eligibility,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
    LadderInputs,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared.dto import (
    UpdateContextInput,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.tick_ledger import (
    V3TickKeywordLedger,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_campaign_mode import (
    CampaignMode,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv
from app.shared.domains.wb.dto.wb_adv_dto import WBAdvDTO


@dataclass
class TickData:
    """Runtime-состояние тика после ``DataUpdateManager.load``.

    Plan/fact, gate-флаги preamble и policy-параметры — только в ``tick_input``.
    WB-снимок кампании — в ``dto`` (``dto.plan`` / ``dto.fact`` при ``fact_source=dto``).
    """

    complex_adv: ComplexAdv
    ledger: V3TickKeywordLedger
    dto: WBAdvDTO | None
    raw_profiles: dict[str, list[BidPosition]]
    campaign_mode: CampaignMode
    sales_state: SalesStates | None
    contexts: list[KeywordV3Context]
    all_contexts: list[KeywordV3Context]
    tick_input: UpdateContextInput | None = None
    ladder_inputs: LadderInputs | None = None
    eligibility_by_ks_id: dict[int, KeywordV3Eligibility] = field(
        default_factory=dict
    )
    sync_fallback_by_id: dict[int, bool] | None = None
    plan_fact_change: ChangePlanFact | None = None
    views_cache: ChangePlanFactViews | None = None
    calibration_step_cache: V3CalibrationStepState | None = None
    views_resolve_succeeded: bool = False
    current_views: int | None = None
    tick_report_ready: bool = False
    fact_source: str | None = None
