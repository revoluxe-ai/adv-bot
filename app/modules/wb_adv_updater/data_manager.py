import asyncio
import io
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Union, Optional

import aiogram
from aiogram.utils import deep_linking

from app.exc import CardNotFoundInDB
from app.modules.common_slaves.wildberries import exceptions as wb_exc
import pandas as pd
from PIL import Image
from sqlalchemy import and_, func, select, case, cast, Float
from sqlalchemy.orm import selectinload
from app.modules.common_slaves.wildberries import super_cabinet_manager
from app.modules.common_slaves.wildberries.api import WBApi
from app.modules.common_slaves.wildberries.data_classes.card_from_wb import CardFromWB
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword, KeywordStatus
from app.modules.common_slaves.wildberries.data_classes.subcategories import Subcategory
from app.modules.common_slaves.wildberries.exceptions import NotItemsInAdvSetting
from app.modules.common_slaves.wildberries.models import (
    AdvKeyword,
    KeywordSetting,
    WBCabinet,
    WBCard,
    WBCategory,
)
from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
from app.modules.wb_adv_updater.ABC_manager import AbcManager
from app.modules.wb_adv_updater.models import GlobalCategorySetting
from app.my_types import AdvSetting, WBUserCabinet
from app.payments.db.models import Payment
from app.settings import settings
from app.utils.db.models import User, RefLink, user_reflink_association
from app.utils.db.session_maker import get_async_session_maker
from app.utils.NeoDataScience.driver import DataScience
from app.utils import redis_manager

logger = logging.getLogger(__name__)


_sm = get_async_session_maker


async def measure_time(function):
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await function(*args, **kwargs)  # Используйте await для асинхронного вызова
        end_time = time.time()
        print(f"{function.__name__} выполнена за {end_time - start_time} секунд.")
        return result
    return wrapper


async def get_keywords_statistic(adv_setting: AdvSetting,
                                 pass_time: Union[timedelta, None],
                                 hard_statuses: list[int] = None,
                                 cache_timeout = 60*15
                                 ) -> list[CalculatedKeyword]:
    keyword_stats = None
    try:
        keyword_stats = await redis_manager.get_keyword_statistics(adv_setting, pass_time = pass_time)
    except Exception:
        logger.error(f'Ошибка при получении статистики ключевых слов из кэша\n',
                     exc_info=True)

    if keyword_stats:
        return keyword_stats

    base_stmt = (
        select(
            AdvKeyword.text.label("keyword_text"),
            func.sum(AdvKeyword.views).label("total_views"),
            func.sum(AdvKeyword.spend).label("total_spend"),
            func.sum(AdvKeyword.clicks).label("total_clicks"),
            # Используйте total_clicks для суммы кликов
        )
        .join(KeywordSetting, AdvKeyword.keyword_setting_id == KeywordSetting.id)
    )
    if pass_time:
        today = datetime.today()
        base_stmt = base_stmt\
        .where(AdvKeyword.date >= today - pass_time)


    if hard_statuses:
        # Фильтрация по hard_statuses и adv_setting_id и добавление группировки
        stmt = base_stmt.where(
            and_(
                KeywordSetting.hard_status.in_(hard_statuses),
                KeywordSetting.adv_setting_id == adv_setting.id
            )
        )
    else:
        stmt = base_stmt.where(KeywordSetting.adv_setting_id == adv_setting.id)


    # Группировка по тексту ключевых слов и идентификатору настройки рекламной кампании вне зависимости от условия
    stmt = stmt.group_by(AdvKeyword.text, KeywordSetting.adv_setting_id)
    async with _sm() as session:
        result = await session.execute(stmt)
        rows = result.all()  # Получение всех результатов запроса

    keyword_stats = []
    for row in rows:
        text = row.keyword_text
        if text:
            keyword_stat = CalculatedKeyword(
                row.keyword_text,
                min(row.total_clicks, row.total_views) if row.total_clicks and row.total_views else 0,
                row.total_views or 0,
                row.total_spend or 0,
            )
            keyword_stats.append(keyword_stat)

    await redis_manager.set_keyword_statistics(adv_setting, keyword_stats, pass_time, cache_timeout)
    return keyword_stats




async def get_keyword_statistic(keyword_setting: KeywordSetting,
                                pass_days: Union[int, None] = None) -> tuple[int, int, int]:
    today = datetime.now().date()
    async with _sm() as session:
        stmt = (
            select(
                func.coalesce(func.sum(AdvKeyword.clicks), 0).label("total_clicks"),
                func.coalesce(func.sum(AdvKeyword.views), 0).label("total_views"),
                func.coalesce(func.sum(AdvKeyword.spend), 0).label("total_spend"),
                func.greatest(func.sum(AdvKeyword.clicks), func.sum(AdvKeyword.views)).label("adjusted_clicks")
            )
            .join(KeywordSetting, AdvKeyword.keyword_setting_id == KeywordSetting.id)  # Явное указание соединения
        ).where(KeywordSetting.id == keyword_setting.id)

        if pass_days:
            stmt = stmt.where(
                AdvKeyword.date >= today - timedelta(days=pass_days)
            )

        result = await session.execute(stmt)
        total_clicks, total_views, total_spend, adjusted_clicks = result.one()

    # Исправляем клики, если они превышают просмотры
    total_clicks = min(total_clicks, total_views)
    return total_clicks, total_views, total_spend



async def get_global_super_wb_user_cabinet() -> WBUserCabinet:
    async with _sm() as session:
        stmt = select(User).options(selectinload(User.wb_tokens))
        result = await session.execute(stmt)
        users: list[User] = result.unique().scalars().all()
        all_tokens = [wb_token for user in users for wb_token in user.wb_tokens]
        super_user = User()
        super_user.wb_tokens = all_tokens
        wb_user_cabinet = WBUserCabinet()
        wbcabinet = WBCabinet()
        wb_user_cabinet.wb_cabinet = wbcabinet
        wb_user_cabinet.user = super_user
    return wb_user_cabinet





async def get_wb_category_to_keywordstat_list() -> defaultdict[WBCategory, list[CalculatedKeyword]]:
    logger.debug('Начинаю получать статистику ключевых слов для расчета min_ctr')
    stmt = select(AdvSetting).options(
        selectinload(AdvSetting.adv_keywords),
        selectinload(AdvSetting.keyword_settings),
        selectinload(AdvSetting.wb_cards)
    ).where(and_(AdvSetting.bot_active == True, AdvSetting.active_status == 'started'))

    async with _sm() as session:
        result = await session.execute(stmt)
        adv_settings: list[AdvSetting] = result.unique().scalars().all()
    wb_category_to_keywordstat_list = defaultdict(list)
    for adv_setting in adv_settings:
        logger.info(f'Обрабатываю {adv_setting.name} для расчета min_ctr')
        try:
            wb_category: Union[WBCategory, None] = await get_wb_category(adv_setting)
        except (NotItemsInAdvSetting, CardNotFoundInDB) as e:
            logger.debug(f'У кампании {adv_setting.name} нет товаров {e}')
            continue
        wb_category_name = wb_category.wb_category_name
        keyword_stats = await get_keywords_statistic(adv_setting, None, [1, 2])
        for keyword_stat in keyword_stats:
            if keyword_stat.views:
                wb_category_to_keywordstat_list[wb_category_name].append(keyword_stat)
    return wb_category_to_keywordstat_list


async def get_parent_id_categories_subcategories_name_list() -> defaultdict[Any, list[Subcategory]]:
    access = await super_cabinet_manager.get_super_user_access()
    wb_api = WBApi(access)
    subcategories: list[Subcategory] = await wb_api.content.get_subcategories()
    parent_categories = defaultdict(list)
    for category in subcategories:
        parent_categories[category.parentID].append(category.subjectName)
    parent_categories_subcategories_name_list = parent_categories
    return parent_categories_subcategories_name_list


async def get_category_name_min_ctr_final_data() -> dict[int, float]:
    async with _sm() as session:
        stmt = select(GlobalCategorySetting.category_name, GlobalCategorySetting.min_ctr)
        result = await session.execute(stmt)
        global_category_settings: list[GlobalCategorySetting] = result.all()
    get_category_name_min_ctr = {}
    for row in global_category_settings:
        category_name = row[0]
        min_ctr = row[1]
        get_category_name_min_ctr[category_name] = min_ctr
    return get_category_name_min_ctr



async def get_good_bad_phrases(adv_setting: AdvSetting)->list[CalculatedKeyword]:
    async with _sm() as session:
        stmt = select(KeywordSetting).where(KeywordSetting.adv_setting_id == adv_setting.id)
        result = await session.execute(stmt)
        keyword_settings: list[KeywordSetting] = result.unique().scalars().all()
        min_ctr = await get_min_ctr(adv_setting)
        keyword_stats = await get_keywords_statistic(adv_setting, None)
        keyword_text_to_keyword_setting = {keyword_setting.text: keyword_setting for keyword_setting in keyword_settings}
        for keyword_stat in keyword_stats:
            keyword_setting = keyword_text_to_keyword_setting[keyword_stat.text]
            keyword_stat.hard_status = keyword_setting.hard_status
            keyword_stat.keyword_setting = keyword_setting
            added_views = keyword_setting.added_views
            if not added_views:
                added_views = 0
            added_clicks = keyword_setting.added_clicks
            if not added_clicks:
                added_clicks = 0
            if min_ctr == 0:
                enough_views = 1000
            else:
                enough_views = int(1 / min_ctr)
            views = keyword_stat.views + enough_views + added_views
            clicks = keyword_stat.clicks + 1 + added_clicks
            if views == 0:
                fact_ctr = 0
            else:
                fact_ctr = clicks / views
            predict_ctr = keyword_setting.predict_ctr
            if not predict_ctr:
                predict_ctr = fact_ctr
                keyword_setting.predict_ctr = predict_ctr
            elif fact_ctr > predict_ctr:
                predict_ctr = fact_ctr
            if adv_setting.max_cpc:
                if keyword_stat.cpc > adv_setting.max_cpc:
                    keyword_stat.status = 'bad'
                    keyword_stat.reason = 'max_cpc'
                    await redis_manager.set_auto_block_status(keyword_setting.id, False)
                    continue

            boost = adv_setting.boost
            predict_ctr *= boost
            if keyword_setting.hard_status == 3:
                keyword_stat.status = KeywordStatus.BAD
                keyword_stat.reason = 'turn_off'
                await redis_manager.set_auto_block_status(keyword_setting.id, False)
                continue
            if keyword_setting.hard_status == 2:
               keyword_stat.status = KeywordStatus.GOOD
               keyword_setting.auto_block = False
               await redis_manager.set_auto_block_status(keyword_setting.id, False)
               continue
            elif keyword_setting.hard_status == 0:
                keyword_stat.status = KeywordStatus.BAD
                keyword_stat.reason = 'black_list'
                await redis_manager.set_auto_block_status(keyword_setting.id, False)
                continue
            if min_ctr == 0:
                keyword_stat.status = KeywordStatus.GOOD
                await redis_manager.set_auto_block_status(keyword_setting.id, False)
                continue
            if adv_setting.max_cpc:
                max_cpc = adv_setting.max_cpc
                if keyword_stat.cpc > max_cpc:
                    keyword_stat.status = KeywordStatus.BAD
                    keyword_stat.reason = KeywordStatus.MAX_CPC
                    await redis_manager.set_auto_block_status(keyword_setting.id, True)
                    continue
            if predict_ctr >= min_ctr:
                keyword_stat.status = KeywordStatus.GOOD
                await redis_manager.set_auto_block_status(keyword_setting.id, False)
            else:
                if keyword_stat.views < adv_setting.min_views_for_ml_predict:
                    keyword_stat.status = KeywordStatus.GOOD
                    keyword_stat.reason = KeywordStatus.VIEWS_IS_NOT_ENOUGH
                    await redis_manager.set_auto_block_status(keyword_setting.id, True)
                else:
                    keyword_stat.status = KeywordStatus.BAD
                    keyword_stat.reason = 'min_ctr'
                    await redis_manager.set_auto_block_status(keyword_setting.id, True)

    for keyword_stat in keyword_stats:
        assert keyword_stat.status
        assert keyword_stat.status in ['good', 'bad']
        # assert keyword_stat.reason in ['max_cpc',
        #                                'turn_off',
        #                                'black_list',
        #                                'min_ctr',
        #                                KeywordStatus.VIEWS_IS_NOT_ENOUGH]

    return keyword_stats








class DataGetter(AbcManager):
    def __init__(self):
        self._gds = DataScience()

    @staticmethod
    def normalize_df_data(df: pd.DataFrame, param_for_norm: str) -> pd.DataFrame:
        max_ = df[param_for_norm].max()
        min_ = df[param_for_norm].min()
        return (df[param_for_norm] - min_) / (max_ - min_)


    async def get_full_df(self, shops: list[WBUserCabinet]):
        shops_df_tasks = [self.get_df_for_shop(shop) for shop in shops]
        shops_dfs = await asyncio.gather(*shops_df_tasks)
        df = pd.concat(shops_dfs)
        return df


    @staticmethod
    def __get_df_from_date_answer(answer, company):
        data_dict = defaultdict(list)
        for date_data in answer:
            stat = date_data['stat']
            for keyword_stat in stat:
                keyword = keyword_stat['keyword']
                views = keyword_stat['views']
                clicks = keyword_stat['clicks']
                spend = keyword_stat['sum']
                if views > 0:
                    data_dict['keyword'].append(keyword)
                    data_dict['views'].append(views)
                    data_dict['clicks'].append(clicks)
                    data_dict['spend'].append(spend)

        df = pd.DataFrame(data_dict)
        df = df.groupby(['keyword']).agg({'views': 'sum', 'clicks': 'sum', 'spend': 'sum'})
        df = df.reset_index()
        df['adv_id'] = company.advertId
        df['nmids'] = [company.nmids] * (len(df))
        return df


    async def get_df_for_shop(self, shop: WBUserCabinet) -> pd.DataFrame:
        wb_api = WBApi(shop)
        companies = await wb_api.advert.get_all_adv_companies()
        keywords_dfs = []
        for company in companies:
            logger.debug('Начинаю получать ключи')
            answer = await wb_api.advert.get_keywords_stat(company)
            logger.debug('Ключи получены')
            await asyncio.sleep(10)
            if answer == []:
                continue
            df = self.__get_df_from_date_answer(answer, company)
            keywords_dfs.append(df)
        if keywords_dfs == []:
            return pd.DataFrame()
        df = pd.concat(keywords_dfs)
        return df


    async def get_cards_for_shop(self, shop: WBUserCabinet):
        wb_api = WBApi(shop)
        cards: list[CardFromWB] = await wb_api.advert.get_cards()
        for card in cards:
            card.shop_name = shop.name
        return cards

    def get_nmid_offer_id_df(self, cards: list[CardFromWB]) -> pd.DataFrame:
        dict_ = defaultdict(list)
        for card in cards:
            dict_['nmid'].append(card.nmid)
            dict_['offer_id'].append(card.offer_id)
            dict_['shop_name'].append(card.shop_name)
        nmid_offer_id_df = pd.DataFrame(dict_)
        return nmid_offer_id_df

    async def listProgress(self, jobid):
        result = await self._gds.get_status_job(jobid)
        return result


async def get_wb_category(adv_setting: AdvSetting)-> Union[WBCategory, None]:
    try:
         nmid = adv_setting.nmids[0]
    except:
        raise wb_exc.NotItemsInAdvSetting('У кампании в базе нет товаров')
    async with _sm() as session:
        smtp = select(WBCard).where(WBCard.nmid == nmid).options(selectinload(WBCard.wb_category))
        wb_card = await session.execute(smtp)
    wb_card: WBCategory = wb_card.unique().scalar()
    if wb_card:
        wb_category = wb_card.wb_category
    else:
        raise CardNotFoundInDB('В базе не найдена карточка товара: ' + str(nmid))
    return wb_category

class DataSetter:
    def __init__(self, access: WBCabinetAccess):
        self._wb_api = WBApi(access)
        self._wb_cabinet = access.wb_cabinet

    async def update_minus_keywords(self, adv_settings: list[AdvSetting]):
        for adv_setting in adv_settings:
            keywords: list[CalculatedKeyword] = await get_good_bad_phrases(adv_setting)
            good_phrases = []
            bad_phrases = []
            for keyword in keywords:
                if keyword.status == KeywordStatus.GOOD:
                    good_phrases.append(keyword.text)
                else:
                    bad_phrases.append(keyword.text)
            if bad_phrases and not settings.test_mode:
                await self._wb_api.advert.set_minus_phrases(adv_setting, bad_phrases)
                logger.info(f'Обновил минус слова {adv_setting.name} {bad_phrases}')
                logger.info(f'Позитивные слова {good_phrases}')
            else:
                logger.info(f'Нет минус слов для {adv_setting.name}')
        return


    def _print_keywords(self, df: pd.DataFrame, df_fact: pd.DataFrame, nmid, min_ctr: float):
        full_goods = []
        full_bads = []
        for _, row in df.iterrows():
            keyword = row.keyword
            clicks = df_fact.loc[(df_fact['keyword'] == keyword) & (df_fact['nmid'] == nmid), 'clicks'].item()
            views = df_fact.loc[(df_fact['keyword'] == keyword) & (df_fact['nmid'] == nmid), 'views'].item()
            nmid = row.nmid
            predict_ctr = row.predict_ctr
            real_ctr = round(clicks / views, 2)
            str_ = f'{keyword} ({clicks}) ({views}) ({real_ctr}) ({round(predict_ctr, 3)})'
            if predict_ctr >= min_ctr:
                full_goods.append(str_)
            else:
                full_bads.append(str_)
        goods = ', '.join(full_goods)
        bads = ', '.join(full_bads)

        logger.info(f'{str(nmid)} Позитивные ключи: {goods}')
        logger.info(f'{str(nmid)} Негативные ключи: {bads}')


async def get_main_photos(nmids: list[int]):
    async with _sm() as session:
        smtp = (select(WBCard).where(WBCard.nmid.in_(nmids)))
        result = await session.execute(smtp)
        wb_cards: list[WBCard] = result.unique().scalars().all()
    main_photos: list[str] = [wb_card.photos[0] for wb_card in wb_cards]
    return main_photos



async def __download_and_resize_image(url, session, max_size=1280):
    while True:
        async with session.get(url) as response:
            if response.status != 200:
                await asyncio.sleep(1)
                continue
            image_data = await response.read()
            # Открываем изображение используя BytesIO
            with io.BytesIO(image_data) as image_file:
                with Image.open(image_file) as img:
                    # Масштабируем изображение, сохраняя пропорции
                    img.thumbnail((max_size, max_size))

                    # Сохраняем изображение в BytesIO объект
                    with io.BytesIO() as output:
                        img.save(output, format="JPEG")
                        return output.getvalue()


async def get_adv_keyword_text_in_black_list()-> list[tuple[int, str]]:
    async with _sm() as session:
        stmt = select(KeywordSetting)\
            .options(selectinload(KeywordSetting.adv_setting))\
        .where(KeywordSetting.hard_status == 0)
        result = await session.execute(stmt)
        keyword_settings: list[KeywordSetting] = result.unique().scalars().all()
    adv_keyword_text_in_black_list = []
    for keyword_setting in keyword_settings:
        adv_setting = keyword_setting.adv_setting
        adv_keyword_text_in_black_list.append((adv_setting.adv_id, keyword_setting.text))

    return adv_keyword_text_in_black_list

async def get_adv_keyword_text_in_white_list():
    async with _sm() as session:
        stmt = select(KeywordSetting) \
            .options(selectinload(KeywordSetting.adv_setting)) \
            .where(KeywordSetting.hard_status.in_([2, 3]))
        result = await session.execute(stmt)
        keyword_settings: list[KeywordSetting] = result.unique().scalars().all()
    adv_keyword_text_in_white_list = []
    for keyword_setting in keyword_settings:
        adv_setting = keyword_setting.adv_setting
        adv_keyword_text_in_white_list.append((adv_setting.adv_id, keyword_setting.text))

    return adv_keyword_text_in_white_list




async def get_all_users()-> list[User]:
    async with _sm() as session:
        stmt = select(User)
        result = await session.execute(stmt)
        users: list[User] = result.unique().scalars().all()
    return users


async def get_all_shops_for_user(user:User):
    async with _sm() as session:
        stmt = select(WBUserCabinet).where(WBUserCabinet.user_id == user.id)
        result = await session.execute(stmt)
        wb_user_cabinets = result.scalar()
        if wb_user_cabinets:
            return  wb_user_cabinets.all()
        else:
            return []


async def get_adv_id_to_min_ctr(adv_ids: list[int])-> dict[int, float]:
    async with _sm() as session:
        stmt = select(GlobalCategorySetting.category_name, GlobalCategorySetting.min_ctr)
        result = await session.execute(stmt)
        category_name_to_min_ctr = dict(result.all())
    async with _sm() as session:
        stmt = select(AdvSetting).where(AdvSetting.adv_id.in_(adv_ids))
        result = await session.execute(stmt)
        adv_settings: list[AdvSetting] = result.unique().scalars()
    adv_id_to_min_ctr = {}

    for adv_setting in adv_settings:
        wb_category = await get_wb_category(adv_setting)
        wb_category_name = wb_category.wb_category_name
        min_ctr = category_name_to_min_ctr.get(wb_category_name, 0)
        min_ctr = min_ctr * adv_setting.boost
        adv_id_to_min_ctr[adv_setting.adv_id] = min_ctr
    return adv_id_to_min_ctr


async def get_adv_id_keyword_text_to_status(adv_ids: int):
    async with _sm() as session:
        stmt = select(AdvSetting.adv_id, KeywordSetting.text, KeywordSetting.hard_status)\
            .join(KeywordSetting, AdvSetting.id == KeywordSetting.adv_setting_id)\
        .where(AdvSetting.adv_id.in_(adv_ids))
        result = await session.execute(stmt)
        result = result.all()
    adv_id_keyword_text_to_status = {}
    for row in result:
        adv_id = row[0]
        text = row[1]
        status = row[2]
        adv_id_keyword_text_to_status[(adv_id, text)] = status
    return adv_id_keyword_text_to_status



@dataclass
class ReferralStatistic:
    name: str
    referrals_count: int
    total_payments: float

async def get_ref_statistic(user_telegram_id: int) -> Optional[list[ReferralStatistic]]:
    """Получить статистику по рефералам пользователя: количество приведенных пользователей и сумму их платежей."""
    async with _sm() as session:
        # Сначала найдем пользователя по telegram_id
        user_query = select(User.id).where(User.user_telegram_id == user_telegram_id)
        result = await session.execute(user_query)
        user_id = result.scalar() # Используйте scalar_one_or_none для обработки случая, когда пользователь не найден

        # Теперь получим статистику по реферальным ссылкам
        statistics_query = select(
            RefLink.name,
            func.count(user_reflink_association.c.user_id).label("referrals_count"),
            func.coalesce(func.sum(Payment.amount), 0).label("total_payments")
        ).select_from(RefLink) \
         .outerjoin(user_reflink_association, RefLink.id == user_reflink_association.c.reflink_id) \
         .outerjoin(User, user_reflink_association.c.user_id == User.id) \
         .outerjoin(Payment, Payment.user_id == User.id) \
         .where(RefLink.referrer_id == user_id) \
         .group_by(RefLink.name)

        result = await session.execute(statistics_query)
        stats = result.fetchall()

        if not stats:
            return None

        # Возвращаем результаты в удобном для использования виде
        return [ReferralStatistic(name=row[0], referrals_count=row[1], total_payments=row[2]) for row in stats]


@dataclass
class ReferralLink:
    name: str
    link: str



async def get_ref_names_and_links(user_telegram_id: int, bot:aiogram.Bot):
    async with _sm() as session:
        stmt = select(User.id).where(User.user_telegram_id == user_telegram_id)
        result = await session.execute(stmt)
        user_id = result.scalar()
        stmt = select(RefLink.name, RefLink.id).where(RefLink.referrer_id == user_id)
        result = await session.execute(stmt)
        refs = result.fetchall()

    ref_links = []
    for ref in refs:
        link = await deep_linking.create_start_link(bot, ref[1])
        ref_links.append(ReferralLink(name=ref[0], link= link))
    return ref_links


async def get_mean_ctr(adv: AdvSetting):
    keywords: list[CalculatedKeyword] = await get_good_bad_phrases(adv)
    goods = [kw for kw in keywords if kw.status == 'good']
    goods = [kw.text for  kw in goods]
    async with _sm() as session:
        stmt = (
            select(
                case(
                    (func.sum(AdvKeyword.views) == 0, 0),  # Условие, если показов нет, возвращаем 0
                    else_=cast(func.sum(AdvKeyword.clicks) / func.sum(AdvKeyword.views), Float)  # Иначе вычисляем CTR
                ).label("average_ctr")
            )
        ).where(and_(AdvKeyword.adv_setting_id == adv.id,
                     AdvKeyword.text.in_(goods)))
        result = await session.execute(stmt)
        mean_ctr = result.scalar_one()
        return mean_ctr  # Возвращаем значение mean_ctr вместо pass


async def get_min_ctr(adv: AdvSetting):
    category = await get_wb_category(adv)
    category_name = category.wb_category_name
    async with _sm() as session:
        stmt = select(GlobalCategorySetting.min_ctr).where(GlobalCategorySetting.category_name == category_name)
        result = await session.execute(stmt)
        min_ctr = result.scalar_one()
    min_ctr *= adv.boost
    return min_ctr


async def get_needs_nmids():
    async with _sm() as session:
        stmt = select(AdvSetting)
        result = await session.execute(stmt)
        adv_settings: list[AdvSetting] = result.unique().scalars().all()
    nmids = []
    for adv_setting in adv_settings:
        if adv_setting.nmids:
            nmids.extend(adv_setting.nmids)
    return nmids


async def get_all_keywords()-> list[str]:
    async with _sm() as session:
        stmt = select(KeywordSetting)
        result = await session.execute(stmt)
        keyword_settings: list[KeywordSetting] = result.unique().scalars().all()
    keywords = []
    for keyword_setting in keyword_settings:
        keywords.append(keyword_setting.text)
    return keywords


async def clear_cards(need_nmids: list[int]):
    async with _sm() as session:
        stmt = select(WBCard).where(WBCard.nmid.notin_(need_nmids))
        result = await session.execute(stmt)
        wb_cards: list[WBCard] = result.unique().scalars().all()
        await session.delete(wb_cards)
        await session.commit()


async def clear_keywords(need_keywords):
    async with _sm() as session:
        stmt = select(KeywordSetting).where(KeywordSetting.text.notin_(need_keywords))
        result = await session.execute(stmt)
        keyword_settings: list[KeywordSetting] = result.unique().scalars().all()
        await session.delete(keyword_settings)
        await session.commit()


async def get_expired_cabinets(session):
    delete_expired_time = datetime.now() - timedelta(days=30)
    stmt = select(WBCabinet).options(
        selectinload(WBCabinet.adv_settings)
    ).where(WBCabinet.expiration_time < delete_expired_time)
    result = await session.execute(stmt)
    wb_cabinets: list[WBCabinet] = result.unique().scalars().all()
    return wb_cabinets

async def clear_cards_in_db(nmids: list[int]):
    async with _sm() as session:
        stmt = select(WBCard).where(WBCard.nmid.notin_(nmids))
        result = await session.execute(stmt)
        wb_cards: list[WBCard] = result.unique().scalars().all()
        for card in wb_cards:
             await session.delete(card)
             await session.commit()
             await asyncio.sleep(0)

