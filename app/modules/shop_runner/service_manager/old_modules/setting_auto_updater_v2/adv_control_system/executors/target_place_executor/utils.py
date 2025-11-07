from dependency_injector.wiring import inject, Provide


from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword
from app.modules.shop_runner.modules.max_auto_bid_manager.auto_max_bid_manager import AutoMaxBidManager
from app.modules.shop_runner.modules.max_auto_bid_manager.di import AutoMaxCpmContainer
from app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager import ComplexAdv
from app.modules.wb_adv_updater import data_manager


def get_current_cpm(complex_adv: ComplexAdv) -> int | None:
    """Возвращает текущий CPM для комплексной рекламы."""
    if complex_adv.is_bidder_for_search_adv_active and complex_adv.is_bidder_for_auto_cpm_active:
        cpms: set[int] = set()
        if cpm := complex_adv.current_cpms.search_cpm:
            cpms.add(cpm)
        if cpm  := complex_adv.current_cpms.auto_cpm:
            cpms.add(cpm)
        return max(cpms) if cpms else None

    elif not complex_adv.is_bidder_for_search_adv_active and not complex_adv.is_bidder_for_auto_cpm_active:
        return None
    elif complex_adv.is_bidder_for_search_adv_active:
        return complex_adv.current_cpms.search_cpm
    else:
        return complex_adv.current_cpms.auto_cpm


# TODO: На Smoke тестах упала функция ниже, не сварилась зависимость

@inject
async def get_max_cpm(complex_adv: ComplexAdv,
                     auto_max_bid_manager: "AutoMaxBidManager" = Provide[AutoMaxCpmContainer.auto_max_cpm_bid_manager]
                      ) -> int | None:
    main_adv_setting = complex_adv.adv_setting
    keywords = await complex_adv.get_keywords()
    max_user_cpm = complex_adv.max_user_cpm
    max_cpm = await auto_max_bid_manager.get_max_cpm(main_adv_setting, keywords, max_user_cpm)
    return max_cpm


async def get_best_keyword(complex_adv: ComplexAdv) -> CalculatedKeyword | None:
    keywords = await complex_adv.get_keywords()
    keyword = data_manager.get_best_keyword(keywords)
    return keyword