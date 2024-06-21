from sqlalchemy import select, func, and_, text
from sqlalchemy.orm import selectinload

from app.utils.db.models import User
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet, WBUserCabinet, AdvKeyword
from app.utils.db.session_maker import get_async_session_maker

sm = get_async_session_maker

period = 30

async def calculate_active_advs_in_shops():
    async with sm() as session:
        stmt = select(WBCabinet).options(selectinload(WBCabinet.wb_user_cabinets)\
                                         .selectinload(WBUserCabinet.user),
                                         selectinload(WBCabinet.adv_settings))
        result = await session.execute(stmt)
        cabinets: list[WBCabinet] = result.scalars().all()
        cab_cabinets = {}
        for cab in cabinets:
            active_adv = []
            adv_settings: list[AdvSetting] = cab.adv_settings
            for adv in adv_settings:
                if adv.bot_active is True:
                    active_adv.append(adv)
            cab_cabinets[cab] = active_adv

        sorted_cab_cabinets = dict(sorted(cab_cabinets.items(), key=lambda item: len(item[1]), reverse=True))
        all_result = []

        for cab, advs in sorted_cab_cabinets.items():
            count_advs = len(advs)
            advs_ids = [adv.id for adv in advs]
            if count_advs > 0:
                stmt = select(func.sum(AdvKeyword.spend)) \
                    .where(and_(AdvKeyword.adv_setting_id.in_(advs_ids),
                                AdvKeyword.date >= func.current_date() - text(f"interval '{period} day'")))
                result = await session.execute(stmt)
                spend = result.scalar()
                if spend is None:
                    spend = 0
                wb_cabinets = cab.wb_user_cabinets
                for wb_cabinet in wb_cabinets:
                    user = wb_cabinet.user
                    username = f'@{user.username}'
                    # print(f'Пользователь: {username},'
                    #       f' Количество активных объявлений: {count_advs},'
                    #       f' Расход за {period} дней: {spend}')
                    all_result.append((cab.shop_id, username, count_advs, spend))
        all_result = sorted(all_result, key=lambda x: x[2], reverse=True)
        advs_count = 0
        all_advs = 0
        pass_shop_ids = set()
        for res in all_result:
            print(res)
            if res[0] in pass_shop_ids:
                continue
            advs_count += res[2]
            all_advs += 1
            pass_shop_ids.add(res[0])
        print(f'Общее количество активных объявлений: {advs_count}')
        print('Кампаний на магазин в среднем: ', advs_count / all_advs)



if __name__ == '__main__':
    import asyncio
    asyncio.run(calculate_active_advs_in_shops())

