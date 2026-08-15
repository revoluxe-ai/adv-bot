"""Apply campaign defaults to freshly created or explicitly reset AdvSetting rows."""

from app.client_bot.modules.default_settings.adv_setting_policy.common_mode_defaults_policy import (
    CommonModeDefaultsPolicy,
)
from app.client_bot.modules.default_settings.default_models.common_default import (
    CampaignDefaultsV1,
)

from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet


# TODO: Тут не совершенная логика, есть риск передачи не того кабинета. Сделал, так, чтобы не забывали передать в функцию wb_cabinet (подгружать из базы)
def apply_defaults_to_adv_setting(adv_setting: AdvSetting, wb_cabinet: WBCabinet) -> None:
    """
    Применяет дефолтные настройки к объекту AdvSetting через прямой маппинг свойств.
    Использует явное присваивание свойство в свойство для безопасности типизации.

    ``card_ab_hold_mode`` — из ``CommonModeDefaultsPolicy`` (accepted
    ``mode-defaults-policy-ownership``), не из transition-helper.

    Shared defaults / «Применить дефолты» — **не** enable/disable path A/B Hold
    (spec ``card-ab-hold-mode`` «Shared defaults MUST NOT disable or mutate A/B
    Hold on a held campaign» / decision ``card-ab-hold-write-path-ownership`` §13):
    для кампании в ``PENDING_SETUP`` / ``ACTIVE`` функция — **no-op**, чтобы не
    выполнить un-owned disable (mode→off + stale allowed-set snapshot + сброс V3 /
    structural флагов в обход freeze). Отключение A/B Hold — только owned paid
    Telegram EXIT. Для ``OFF`` дефолты применяются как обычно.

    Args:
        adv_setting: Объект AdvSetting, к которому применяются дефолтные настройки
        wb_cabinet: Объект WBCabinet, из которого берем дефолтные настройки
    """
    # Inline-import (документированное исключение no-inline-imports): этот модуль
    # импортируется очень рано (wb_db_manager / model init), а top-level импорт
    # пакета `auto_updater_v3` вызывает циклический импорт. На runtime (вызов из
    # handler) пакет уже инициализирован.
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
        is_ab_hold_structural_freeze,
    )

    if is_ab_hold_structural_freeze(adv_setting.card_ab_hold_mode):
        return

    defaults_v1 = CampaignDefaultsV1()
    common_mode = CommonModeDefaultsPolicy()

    # Прямой маппинг свойств из CampaignDefaultsV1 в AdvSetting
    adv_setting.bidder_active = defaults_v1.bidder_active
    adv_setting.bidder_for_auto = defaults_v1.bidder_for_auto
    adv_setting.bidder_mode = defaults_v1.bidder_mode
    adv_setting.automatic_version = defaults_v1.automatic_version
    adv_setting.bidder_coroutine_type = defaults_v1.bidder_coroutine_type
    adv_setting.orders_source_for_auto_mode = defaults_v1.orders_source_for_auto_mode
    adv_setting.sales_predict_method = defaults_v1.sales_predict_method
    adv_setting.auto_update_white_list = defaults_v1.auto_update_white_list
    adv_setting.auto_update_minus_phrases = defaults_v1.auto_update_minus_phrases
    adv_setting.auto_update_target_place = defaults_v1.auto_update_target_place
    adv_setting.auto_budget_watchdog_enabled = (
        defaults_v1.auto_budget_watchdog_enabled
    )
    adv_setting.use_common_budget = defaults_v1.use_common_budget
    adv_setting.target_ctr_mode = defaults_v1.target_ctr_mode
    adv_setting.new_auto_min_ctr_mode = defaults_v1.new_auto_min_ctr_mode
    adv_setting.reset_place = defaults_v1.reset_place
    adv_setting.card_ab_hold_mode = common_mode.card_ab_hold_mode
    if adv_setting.max_place is None:
        adv_setting.max_place = 1

    if adv_setting.max_cpm is None:
        adv_setting.max_cpm = wb_cabinet.default_max_cpm
