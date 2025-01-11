import csv
from io import StringIO
from typing import Union
from sqlalchemy import and_, select
from app.client_bot.const import BLACK_LIST, TURN_OFF, WHITE_LIST, AUTO_MODE
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword, KeywordStatus
from app.modules.wb_adv_updater import data_manager
from app.my_types import AdvSetting
from dataclasses import dataclass
from app.modules.common_slaves.wildberries.models import  KeywordSetting
from app.utils.db.models import RefLink, User
from app.utils.db.session_maker import get_async_session_maker
import logging


logger = logging.getLogger(__name__)


_sm = get_async_session_maker

@dataclass
class KeywordForKeyboard:
    text: str
    good: bool
    statistic: CalculatedKeyword
    keyword_settings: KeywordSetting
    adv_setting: AdvSetting
    turn_on: bool
    bad_reason: Union[str, None] = None


async def get_keywords_for_keyboard( adv_setting: AdvSetting)-> list[CalculatedKeyword]:
    all_phrases: list[CalculatedKeyword] = await data_manager.get_good_bad_phrases(adv_setting)
    return all_phrases



async def get_csv_file(adv_setting: AdvSetting):
    keywords: list[CalculatedKeyword] = await get_keywords_for_keyboard(adv_setting)
    csv_output = StringIO()
    csv_writer = csv.writer(csv_output,
                            delimiter=';',
                            quotechar='"',
                            quoting=csv.QUOTE_MINIMAL,
                            lineterminator='\n')
    rows = []
    # Заголовки столбцов
    rows.append([
        'Запрос(вхождение)',
        'Запрос(точное соответствие)',
        'Клики',
        'Просмотры',
        "Количество запросов",
        'CTR',
        'Прогнозируемый CTR',
        'Включен-Выключен',
        "Статус",
        'Начальная позиция',
        'Текущая позиция',
        'Дополнительные клики',
        'Рейтинг'
    ])

    for keyword in keywords:
        clicks = keyword.clicks
        views = keyword.views
        ctr = round(keyword.ctr * 100, 2)
        if keyword.reason == 'max_position':
            hard_status = 'ЦП'
        elif keyword.reason == KeywordStatus.VIEWS_IS_NOT_ENOUGH:
            hard_status = 'МП'
        elif keyword.hard_status == BLACK_LIST:
            hard_status = 'НРФ'
        elif keyword.reason == 'max_cpc':
            hard_status = 'МС'
        elif keyword.hard_status == TURN_OFF:
            hard_status = 'О'
        elif keyword.hard_status == WHITE_LIST:
            hard_status = 'БС'
        elif keyword.hard_status == AUTO_MODE:
            hard_status = 'А'
        else:
            raise ValueError(f'Unknown hard_status: {keyword.hard_status}')

        turn_on = '✅Включен' if keyword.status == KeywordStatus.GOOD else '❌Выключен'

        # Определение позиций
        first_position = ''
        second_position = ''
        if adv_setting.parsing_active:
            if keyword.cpm:
                first_position = keyword.base_position
                second_position = keyword.promo_position
            elif keyword.real_position:
                first_position = keyword.real_position
            elif keyword.real_position == 0:
                first_position = ">i"
            else:
                first_position = '?'

        rows.append([
        keyword.text,
        '"' + keyword.text + '"',
        clicks,
        views,
        keyword.query,
        str(ctr).replace('.', ','),
        str(round(keyword.predict_ctr * 100, 2)).replace('.', ','),
        turn_on,
        hard_status,
        first_position,
        second_position,
        keyword.keyword_setting.added_clicks or 0,
        str(round(keyword.rating_by_predict_ctr*100, 4)).replace('.', ',')
        ])

    rows.sort(key=lambda row: row[-1], reverse=True)

    for row in rows:
        logger.debug(row)
        csv_writer.writerow(row)
    csv_string = csv_output.getvalue()
    csv_output.close()

    return csv_string

async def create_ref_link(ref_link_name, user_telegram_id):
    stmt = select(RefLink).where(and_(RefLink.name == ref_link_name, RefLink.referrer_id == user_telegram_id))
    async with _sm(read_only=False) as session:
        result = await session.execute(stmt)
        ref_link = result.scalar_one_or_none()
        if ref_link:
            return False
        stmt = select(User.id).where(User.user_telegram_id == user_telegram_id)
        result = await session.execute(stmt)
        user_id = result.scalar_one()
        ref_link = RefLink(name=ref_link_name, referrer_id=user_id)
        session.add(ref_link)
        await session.commit()
        return ref_link





