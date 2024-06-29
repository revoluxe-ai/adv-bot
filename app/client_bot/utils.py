import asyncio
import datetime
from dataclasses import dataclass
from io import BytesIO
import random
from typing import Union

import pandas as pd
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib.ticker import MaxNLocator
from sqlalchemy import and_, select, func, desc
import seaborn as sns
from sqlalchemy.orm import joinedload

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword
from app.modules.common_slaves.wildberries.models import KeywordSetting, WBCategory, AdvKeyword, CommonKeyword, \
    WBItemPosition
from app.modules.wb_adv_updater import data_manager
from app.my_types import AdvSetting
from app.utils.db.models import RefLink, User
from app.utils.db.session_maker import get_async_session_maker

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
    texts = [phrase.text for phrase in all_phrases]
    keywords_positions_dict = await data_manager.get_keywords_positions(adv_setting, texts)
    for phrase in all_phrases:
        position = keywords_positions_dict.get(phrase.text)
        if position:
            phrase.real_position = position.real_position
            phrase.base_position = position.base_position
            phrase.promo_position = position.promo_position
            phrase.position_update = position.timestamp
            phrase.cpm = position.cpm
    all_phrases.sort(key=lambda keyword: keyword.ctr, reverse=True)
    return all_phrases



async def create_ref_link(ref_link_name, user_telegram_id):
    stmt = select(RefLink).where(and_(RefLink.name == ref_link_name, RefLink.referrer_id == user_telegram_id))
    async with _sm() as session:
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


async def get_keyword_history_graphic(adv_original_id):
    async with _sm() as session:
        stmt = select(AdvKeyword.text, func.sum(AdvKeyword.views).label('views')) \
            .where(AdvKeyword.adv_setting_id == adv_original_id) \
            .group_by(AdvKeyword.text) \
            .order_by(desc('views'))
        result = await session.execute(stmt)
        texts = result.scalars().all()
        stmt = select(AdvSetting).where(AdvSetting.id == adv_original_id)
        adv = await session.execute(stmt)
        adv = adv.scalar()
        nmid = adv.nmids[0]
        stmt = select(CommonKeyword) \
            .join(CommonKeyword.wb_item_positions) \
            .options(joinedload(CommonKeyword.wb_item_positions)) \
            .where(and_(
            WBItemPosition.nmid == nmid,
                        CommonKeyword.text.in_(texts)
                        ))
        result = await session.execute(stmt)
        common_keywords: list[CommonKeyword] = result.unique().scalars().all()

        # Подготовка дат за последние 7 дней
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=30-1)
        date_range = pd.date_range(start=start_date, end=end_date)
        frames = []
        # Создание DataFrame
        for keyword in common_keywords:
            data = {
                "Ключи": [],
                "Дата": [],
                "Позиция": []
            }
            positions = keyword.wb_item_positions
            if not positions:
                return None
            last_position: WBItemPosition = max(positions, key=lambda x: x.timestamp)
            for date in date_range:
                close_position = min(positions, key=lambda x: abs(x.timestamp - date)).real_position
                data["Ключи"].append(keyword.text + f'({last_position.real_position})')
                data["Дата"].append(date)
                beutify_position = close_position - 0.5 +  random.randint(1, 9)*0.1
                data["Позиция"].append(beutify_position)
            frames.append(pd.DataFrame(data))
        if not frames:
            return None
        df = pd.concat(frames, ignore_index=True)
        # Построение графика без легенды
        plt.figure(figsize=(10, 6))
        if len(common_keywords) > 5:
            def get_graphic_and_legend():
                sns.lineplot(data=df, x="Дата", y="Позиция", hue="Ключи", marker="o", legend=False)
                plt.xticks(rotation=45)
                plt.title("Позиции за последние 7 дней")
                plt.tight_layout()
                plt.gca().invert_yaxis()
                ax = plt.gca()  # Получение текущего осевого объекта
                ax.yaxis.set_major_locator(MaxNLocator(integer=True))
                image_stream = BytesIO()
                plt.savefig(image_stream, format='jpg')
                image_stream.seek(0)
                plt.close()
                # Создание отдельной легенды
                plt.figure(figsize=(10, 6))
                for name, group in df.groupby('Ключи'):
                    plt.plot([], [], label=name)
                plt.legend()
                plt.axis('off')
                legend_stream = BytesIO()
                plt.savefig(legend_stream, format='jpg')
                legend_stream.seek(0)
                plt.close()
                return image_stream, legend_stream
            loop = asyncio.get_event_loop()
            image_stream, legend_stream = await loop.run_in_executor(None, get_graphic_and_legend)
            return image_stream, legend_stream
        else:
            def get_graphic():
                sns.lineplot(data=df, x="Дата", y="Позиция", hue="Ключи", marker="o", legend=True)
                plt.xticks(rotation=45)
                plt.title("Позиции за последние 7 дней")
                plt.tight_layout()
                plt.gca().invert_yaxis()
                ax = plt.gca()  # Получение текущего осевого объекта
                ax.yaxis.set_major_locator(MaxNLocator(integer=True))
                image_stream = BytesIO()
                plt.savefig(image_stream, format='jpg')
                image_stream.seek(0)
                plt.close()
                return image_stream
            loop = asyncio.get_event_loop()
            image_stream = await loop.run_in_executor(None, get_graphic)
            return image_stream, None