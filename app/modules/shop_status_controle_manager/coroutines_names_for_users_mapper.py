from app.modules.shop_runner.service_manager import CoroutinesManager

user_names = {
    CoroutinesManager.update_cpm_bid.__name__: "Обновление ставок CPM",
    CoroutinesManager.adv_settings_auto_update.__name__: "Автообновление настроек рекламы",
    CoroutinesManager.parsing_keywords_run.__name__: "Постановка задач на парсинг ключевых слов",
    CoroutinesManager.update_advs_data_from_wb_to_pg.__name__: "Обновление данных об РК из WB в Бот",
    CoroutinesManager.update_cards_data_from_wb_to_pg.__name__: "Обновление данных о карточках товаров из WB в Бот",
    CoroutinesManager.update_common_sale_stat.__name__: "Обновление общей статистики продаж",
    CoroutinesManager.update_full_adv_stat.__name__: "Обновление полной статистики РК",
    CoroutinesManager.update_top_key_in_advs.__name__: "Обновление верхнего ключевого слова в РК",
}
