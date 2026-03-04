

from app.modules.calculated_keywords_redis_cache_manager.redis_manager import (
    RedisCalculatedKeywordsCacheManager,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv

from app.utils.db.session_maker import get_async_session_maker
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword

import logging


logger = logging.getLogger(__name__)

_sm = get_async_session_maker

#
# def _set_predict_ctr(
#     keyword_stats: list[CalculatedKeyword], min_ctr: float, adv_setting: AdvSetting
# ) -> list[CalculatedKeyword]:
#     for keyword_stat in keyword_stats:
#         keyword_stat.predict_ctr_exponent = adv_setting.exponent_predict_ctr
#         original_predict_ctr = keyword_stat.original_predict_ctr
#         if not original_predict_ctr:
#             original_predict_ctr = keyword_stat.predict_ctr
#         logger.debug("Обрабатываю ключевое слово %s", keyword_stat.text)
#         if min_ctr == 0:
#             enough_views_calc = 100
#         else:
#             enough_views_calc = int(1 / min_ctr)
#         keyword_stat.enough_views = enough_views_calc
#         views = keyword_stat.views
#         clicks = keyword_stat.clicks
#         if clicks == 0:
#             clicks += 1
#             views += enough_views_calc
#         if views == 0:
#             views = 1
#         original_baes_ctr = clicks / views
#         keyword_stat.baes_ctr = original_baes_ctr
#         added_clicks = keyword_stat.added_clicks
#         if added_clicks:
#             clicks += added_clicks
#         if original_predict_ctr:
#             predicted_views = int(clicks + 1 / original_predict_ctr)
#             predicted_clicks = int(predicted_views * original_predict_ctr)
#             views += predicted_views
#             clicks += predicted_clicks + 1
#         # TODO: тут вылетает ошибка деления  на ноль временно делаю views = 1 если 0
#         if views == 0:
#             views = 1
#         baes_predict_ctr = clicks / views
#         keyword_stat.predict_ctr = baes_predict_ctr
#         keyword_stat.baes_predict_ctr = baes_predict_ctr
#         keyword_stat.calculated_clicks = clicks
#         keyword_stat.calculated_views = views
#     return keyword_stats

#
# async def _get_good_bad_phrases_for_min_ctr(
#     adv_setting: AdvSetting,
#     max_cpc: int | None = None,
#     pass_time: timedelta | None = timedelta(days=7),
#     min_ctr: float | None = None,
# ) -> list[CalculatedKeyword]:
#     from . import get_text_to_predict_ctr_dict
#
#     if min_ctr is None:
#         min_ctr = await get_min_ctr(adv_setting)
#     logger.debug("Минимальный ctr получен")
#     keyword_stats = await get_keywords_statistic_clickhouse(
#         adv_setting,
#         pass_time,
#     )
#     async with _sm() as session:
#         logger.debug("Начинаю получать фразы")
#         stmt = select(KeywordSetting).where(
#             KeywordSetting.adv_setting_id == adv_setting.id
#         )
#         result = await session.execute(stmt)
#         keyword_settings: list[KeywordSetting] = list(result.unique().scalars().all())
#         logger.debug("Получил ключи")
#     texts_to_keyword_setting: dict[str, KeywordSetting] = {
#         str(kws.text): kws for kws in keyword_settings
#     }
#     texts_in_keyword_stat = {kw.text for kw in keyword_stats}
#     text_to_keyword_setting: dict[str, KeywordSetting] = {
#         str(kw.text): kw for kw in keyword_settings
#     }
#
#     if adv_setting.clusters_mode:
#         logger.debug("Начинаю конвертацию в кластеры")
#         keyword_stats = await convert_keyword_stats_in_clusters(keyword_stats)
#         logger.debug("В кластеры сконвертировали")
#     logger.debug("Начинаю установку позиций")
#     try:
#         keyword_stats_positioned: list[CalculatedKeyword] = await set_positions(
#             keyword_stats, adv_setting
#         )
#     except Exception as exc:
#         raise exc
#     async with _sm(read_only=False) as session:
#         for keyword_stat in keyword_stats_positioned:
#             keyword_text = keyword_stat.text
#             keyword_setting = texts_to_keyword_setting.get(keyword_text)
#             if not keyword_setting:
#                 clusters = keyword_stat.childs_keywords or []
#                 clusters.append(keyword_stat)
#
#                 stat_hard_statuses: dict[int, int] = defaultdict(int)
#                 for kw in clusters:
#                     original_text = kw.text
#                     if keyword := texts_to_keyword_setting.get(original_text):
#                         stat_hard_statuses[keyword.hard_status] += 1
#
#                 result_hard_status = (
#                     max(stat_hard_statuses.items(), key=lambda x: x[1])[0]
#                     if stat_hard_statuses
#                     else 1
#                 )
#
#                 insert_stmt = (
#                     insert(KeywordSetting)
#                     .values(
#                         text=keyword_text,
#                         adv_setting_id=adv_setting.id,
#                         hard_status=result_hard_status,
#                     )
#                     .on_conflict_do_nothing(index_elements=["text", "adv_setting_id"])
#                 )
#                 await session.execute(insert_stmt)
#
#                 # теперь получаем из БД (он там точно есть: либо только что вставили, либо уже был)
#                 keyword_setting = await session.scalar(
#                     select(KeywordSetting).where(
#                         and_(
#                             KeywordSetting.text == keyword_text,
#                             KeywordSetting.adv_setting_id == adv_setting.id,
#                         )
#                     )
#                 )
#
#                 assert keyword_setting is not None
#                 text_to_keyword_setting[keyword_text] = keyword_setting
#
#         await session.commit()
#
#     for keyword_setting in keyword_settings:
#         text = str(keyword_setting.text)
#         if text not in texts_in_keyword_stat:
#             keyword_setting_for_text = text_to_keyword_setting[text]
#
#             keyword_new = CalculatedKeyword(
#                 text=text,
#                 clicks=0,
#                 views=0,
#                 spend=0,
#                 keyword_setting_original_id=keyword_setting_for_text.id,
#             )
#             position = await redis_manager.get_keyword_position(
#                 text, adv_setting.nmids[0]
#             )
#             if position:
#                 keyword_new.position = position
#             keyword_new.query = keywords_query.get_queries_of_keyword(text)
#             keyword_stats.append(keyword_new)
#
#     texts = [kw.text for kw in keyword_stats]
#     try:
#         text_to_predict_ctr: dict[str, float | None] = (
#             await get_text_to_predict_ctr_dict.get(adv_setting, texts)
#         )
#     except Exception as e:
#         logger.error("Ошибка получения предикта", exc_info=True)
#         raise e
#     try:
#         cpm_now = await get_cpm(adv_setting)
#     except Exception as e:
#         logger.error("Ошибка при получении cpm %s", e, exc_info=True)
#         cpm_now = None
#
#     for keyword_stat in keyword_stats:
#         text = keyword_stat.text
#         keyword_setting = text_to_keyword_setting[text]
#         if keyword_setting.added_clicks is None:  # Added check for None
#             added_clicks: int = 0
#         else:
#             added_clicks: int = keyword_setting.added_clicks
#         keyword_stat.relevant = keyword_setting.relevant
#         keyword_stat.added_clicks = added_clicks
#         keyword_stat.keyword_setting_original_id = keyword_setting.id
#         keyword_stat.adv_id = adv_setting.adv_id
#         original_hard_status: int = int(keyword_setting.hard_status)
#         keyword_stat.hard_status = original_hard_status
#         original_predict_ctr: float | None = text_to_predict_ctr.get(text, None)
#         keyword_stat.original_predict_ctr = original_predict_ctr
#
#     keyword_stats: list[CalculatedKeyword] = _set_predict_ctr(
#         keyword_stats, min_ctr, adv_setting
#     )
#
#     best_keyword: CalculatedKeyword | None = get_best_keyword(keyword_stats)
#     if best_keyword:
#         best_keyword.best_keyword_status = True
#
#     for keyword_stat in keyword_stats:
#         clicks = keyword_stat.calculated_clicks
#         assert clicks is not None
#         views = keyword_stat.calculated_views
#         assert views is not None
#         enough_views = keyword_stat.enough_views
#         assert enough_views is not None
#         original_predict_ctr = keyword_stat.original_predict_ctr
#         assert keyword_stat.hard_status is not None
#         hard_status = int(keyword_stat.hard_status)
#         keyword_setting = text_to_keyword_setting.get(keyword_stat.text)
#         """TODO: Выпилить из кода reason max_position, т.е. больше функции отключения позиции, если база больше
#          или равна целевой - нет. """
#         if max_cpc:
#             if cpm_now:
#                 assert keyword_stat.predict_ctr is not None
#                 cpc = (cpm_now / 1000) / keyword_stat.predict_ctr
#             elif clicks > 0:
#                 cpc = views / clicks
#             else:
#                 cpc = None
#             if cpc and cpc > max_cpc:
#                 keyword_stat.status = KeywordStatus.BAD
#                 keyword_stat.reason = "max_cpc"
#                 if keyword_setting and keyword_setting.id:
#                     await redis_manager.set_auto_block_status(
#                         int(keyword_setting.id), True  # type: ignore
#                     )
#                 continue
#         if (
#             not original_predict_ctr
#             and enough_views / 2 > keyword_stat.views
#             and not adv_setting.min_views_for_ml_predict
#             and keyword_stat.hard_status in [1, 2]
#         ):
#             keyword_stat.status = KeywordStatus.GOOD
#             keyword_stat.reason = KeywordStatus.VIEWS_IS_NOT_ENOUGH
#             continue
#
#         if hard_status == 3:
#             keyword_stat.status = KeywordStatus.BAD
#             keyword_stat.reason = "turn_off"
#             continue
#         if hard_status == 2:
#             keyword_stat.status = KeywordStatus.GOOD
#             keyword_stat.reason = "white_list"
#             continue
#         elif hard_status == 0:
#             keyword_stat.status = KeywordStatus.BAD
#             keyword_stat.reason = "black_list"
#             continue
#         if min_ctr == 0:
#             keyword_stat.status = KeywordStatus.GOOD
#             keyword_stat.reason = "min_ctr_is_zero"
#             continue
#         baes_predict_ctr = keyword_stat.baes_predict_ctr
#         assert baes_predict_ctr is not None
#         if baes_predict_ctr >= min_ctr:
#             keyword_stat.status = KeywordStatus.GOOD
#             keyword_stat.reason = "baes_ctr_more_than_min_ctr"
#         else:
#             assert keyword_stat.views is not None
#             if adv_setting.min_views_for_ml_predict and keyword_stat.views < adv_setting.min_views_for_ml_predict:
#                 keyword_stat.status = KeywordStatus.GOOD
#                 keyword_stat.reason = KeywordStatus.VIEWS_IS_NOT_ENOUGH
#             else:
#                 keyword_stat.status = KeywordStatus.BAD
#                 keyword_stat.reason = "min_ctr"
#         assert keyword_stat.predict_ctr
#     logger.debug("Проверяю статусы ключевых слов с assert")
#
#     for keyword_stat in keyword_stats:
#         try:
#             assert keyword_stat.status
#             assert keyword_stat.status in [
#                 KeywordStatus.GOOD,
#                 KeywordStatus.BAD,
#                 KeywordStatus.VIEWS_IS_NOT_ENOUGH,
#                 KeywordStatus.MAX_CPC,
#             ]
#         except Exception as e:
#             raise e
#     # TODO: Тут вообще не понятно что это и зачем
#     for keyword_stat in keyword_stats:
#         for property_ in keyword_stat.__dict__:
#             if property_ in [
#                 "position_update",
#                 "k",
#                 "k",
#                 "best_keyword_status",
#                 "childs_keywords",
#                 "cpm",
#                 "promo_position",
#                 "original_predict_ctr",
#                 "real_position",
#                 "base_position",
#                 "cluster_name",
#                 "preset",
#                 "position",
#             ]:
#                 continue
#             # TODO: Критичный код, не стал трогать, так то надо переделать, чтобы не было shadow  переменных  property
#             value = getattr(keyword_stat, property_)  # type: ignore
#             try:
#                 assert value is not None
#             except AssertionError:
#                 # TODO: Удалить из всего проекта f-строки из логирования
#                 logger.error(
#                     "Ошибка в значении %s для %s: %s",
#                     property_,
#                     keyword_stat.text,
#                     value,
#                 )
#
#     logger.debug("Слова по assert проверены")
#     logger.debug("Возвращаю итоговую статистику")
#     return keyword_stats




async def get_good_bad_phrases(complex_adv: ComplexAdv) -> list[CalculatedKeyword]:

    from .calculated_keywords_manager import CalculatedKeywordsManager
    keyword_manager = CalculatedKeywordsManager()
    # TODO: Вроде как сейчас WB позволяет внутри РК управлять каждым артикулом отдельно
    keywords: list[CalculatedKeyword]  = await keyword_manager.get_calculated_keywords(complex_adv)
    keywords = sorted(keywords, key=lambda kw: kw.rating or 0, reverse=True)
    keywords_redis_cache_manager = RedisCalculatedKeywordsCacheManager()
    await keywords_redis_cache_manager.set_calculated_keywords(
        keywords, complex_adv.adv_id
    )
    return keywords


def get_white_list(
    keywords: list[CalculatedKeyword],
) -> list[CalculatedKeyword] | None:
    """За один проход по белому списку: (мин. зак. на 1000₽, мин. конверсия показы→заказы)."""
    white_list = [kw for kw in keywords if kw.hard_status == 2]
    if not white_list:
        return None
    return white_list


def get_min_orders_per_1000_rub(keywords: list[CalculatedKeyword]) -> float | None:
    """Минимум заказов на 1000₽ среди ключей в белом списке."""
    white_list = get_white_list(keywords)
    if not white_list:
        return None
    result = min(kw.orders_per_1000_rub for kw in white_list)
    return result


def get_min_conv_views_to_orders(keywords: list[CalculatedKeyword]) -> float | None:
    """Минимум конверсии показы→заказы (доля) среди ключей в белом списке. Для «зак. на 1000 показов» умножать на 1000."""
    white_list = get_white_list(keywords)
    if not white_list:
        return None
    result = min(kw.conv_views_to_orders for kw in white_list)
    return result
