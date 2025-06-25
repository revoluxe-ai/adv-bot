import dotenv

dotenv.load_dotenv()
from datetime import datetime, timedelta

import aiofiles
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.utils.click_house.client import get_clickhouse_client
from app.utils.db.session_maker import get_async_session_maker as sm
from app.modules.common_slaves.wildberries.models import (
    User,
    WBCabinet,
    WBUserCabinet,
    AdvSetting,
)

end_date = datetime.now().date()
start_date = end_date - timedelta(days=30)


async def get_total_spend(adv_ids: list[int]) -> float:
    start_date_str = start_date.strftime("%Y-%m-%d 00:00:00")
    end_date_str = end_date.strftime("%Y-%m-%d 23:59:59")  # конец дня

    async with get_clickhouse_client() as ch_client:
        query = f"""
            SELECT SUM(spend)
            FROM default_db.advkeyword
            WHERE date BETWEEN '{start_date_str}' AND '{end_date_str}'
            AND adv_id IN {adv_ids}
        """
        try:
            result = await ch_client.query(query)
        except Exception as e:
            print(e)
            del e
            return 0.0
        result = result.result_rows

    # Возврат суммы расходов
    return result[0][0] if result and result[0][0] is not None else 0.0


async def get_clients_to_file():
    stmt = select(User).where(User.username is not None)

    async with sm() as session:
        users = await session.execute(stmt)
        users = users.scalars().all()

        file = "users.csv"
        async with aiofiles.open(file, "w") as f:
            await f.write(
                "id, username, shop_ids, total_spend,total_advs,active_advs_with_bot,total_balance\n"
            )

            for user in users:
                total_spend = 0
                total_advs = 0
                active_advs_with_bot = 0
                total_balance = 0
                total_bonus = 0
                username = user.username

                if username:
                    stmt = (
                        select(WBUserCabinet)
                        .join(WBCabinet, WBUserCabinet.wb_cabinet_id == WBCabinet.id)
                        .options(joinedload(WBUserCabinet.wb_cabinet))
                        .where(WBUserCabinet.user_id == user.id)
                    )

                    wb_user_cabinets = await session.execute(stmt)
                    wb_user_cabinets = wb_user_cabinets.scalars().all()

                    for wb_user_cabinet in wb_user_cabinets:
                        wb_cabinet = wb_user_cabinet.wb_cabinet
                        total_balance += wb_cabinet.balance or 0
                        total_bonus += wb_cabinet.bonus or 0

                        stmt = select(AdvSetting.adv_id).where(
                            AdvSetting.wb_cabinet_id == wb_cabinet.id
                        )

                        adv_ids = await session.execute(stmt)
                        adv_ids = adv_ids.scalars().all()
                        adv_ids = [adv_id for adv_id in adv_ids if adv_id]

                        spend = await get_total_spend(adv_ids)
                        total_spend += spend

                        stmt = select(AdvSetting).where(
                            AdvSetting.adv_id.in_(adv_ids),
                            AdvSetting.active_status == "started",
                        )

                        advs = await session.execute(stmt)
                        advs = advs.scalars().all()

                        total_advs += len(advs)
                        active_advs_with_bot += len(
                            [adv for adv in advs if adv.bot_active]
                        )
                    shop_ids = "; ".join(
                        [
                            wb_user_cabinet.wb_cabinet.shop_id
                            for wb_user_cabinet in wb_user_cabinets
                        ]
                    )
                    row = (
                        f"{user.id},"
                        f"@{username},"
                        f"{shop_ids},"
                        f"{total_spend},"
                        f"{total_advs},"
                        f"{active_advs_with_bot},"
                        f"{total_balance + total_bonus}\n"
                    )
                    await f.write(row)
                    print(row)


if __name__ == "__main__":
    import asyncio

    asyncio.run(get_clients_to_file())
