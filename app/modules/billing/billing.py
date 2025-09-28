"""Billing per-cabinet daily charges with Redis/DB dedup and advisory locks."""

import logging
from datetime import date, datetime

from sqlalchemy import exists, func, select, text
from sqlalchemy.orm import selectinload

from app.modules.billing.pricer import Pricer
from app.modules.common_slaves.wildberries.models import AdvSetting, WBBalancePayment, WBBonusPayment, WBCabinet
from app.modules.wb_adv_updater.models import AdvPayment
from app.utils.db.session_maker import get_async_session_maker as sm

from .redis_manager import RedisManager

logger = logging.getLogger(__name__)


redis_manager = RedisManager()


async def get_active_cabinets_with_data(session) -> list[WBCabinet]:
    """Вернуть кабинеты, у которых есть активные кампании, с подгруженными платежами и платежами кампаний."""
    stmt = (
        select(WBCabinet)
        .options(
            selectinload(WBCabinet.balance_payments),
            selectinload(WBCabinet.bonus_payments),
            selectinload(WBCabinet.adv_settings).selectinload(AdvSetting.payments),
        )
        .where(exists(select(1).where(AdvSetting.wb_cabinet_id == WBCabinet.id, AdvSetting.bot_active)))
    )
    result = await session.execute(stmt)
    cabinets = result.unique().scalars().all()
    return list(cabinets)


def get_count_advs_for_wb_cabinet(wb_cabinet: WBCabinet, adv_settings: list[AdvSetting]) -> int:
    advs_for_wb_cabinet = [adv for adv in adv_settings if adv.wb_cabinet_id == wb_cabinet.id]
    return len(advs_for_wb_cabinet)


async def process_payment_for_advs(current_date: date = None, pricer: Pricer = None) -> None:
    """Обработка платежей с группировкой по кабинетам и защитой от дублей на уровне кабинетов."""
    if current_date is None:
        current_date = datetime.now().date()
    if pricer is None:
        pricer = Pricer()

    logger.debug(f"Начинаем обработку платежей за {current_date}")

    async with sm(read_only=False) as session:
        # Получаем кабинеты с активными кампаниями и всеми нужными зависимостями
        cabinets = await get_active_cabinets_with_data(session)
        if not cabinets:
            logger.debug("Нет активных кабинетов с кампаниями")
            return

        processed_cabinet_ids: list[int] = []

        # Обработка по кабинетам
        for cabinet in cabinets:
            cabinet_id = cabinet.id
            # Берем только активные кампании
            cabinet_campaigns: list[AdvSetting] = [adv for adv in cabinet.adv_settings if adv.bot_active]
            logger.debug(f"Кабинет {cabinet_id}: найдено активных кампаний: {len(cabinet_campaigns)}")
            if not cabinet_campaigns:
                logger.debug(f"Кабинет {cabinet_id}: активные кампании отсутствуют, пропуск")
                continue
            try:
                # Advisory-лок на уровне кабинета (предотвращает параллельные списания одной кассеты)
                await session.execute(
                    text("SELECT pg_advisory_lock(:lock_id)"),
                    {"lock_id": cabinet_id + 1_000_000},
                )

                # Защита в Redis на уровне кабинета/дня
                if await redis_manager.get_billing_process_for_day(cabinet_id, current_date):
                    logger.debug(f"Кабинет {cabinet_id} уже обработан за {current_date} (Redis)")
                    continue

                # Доп. проверка в БД: было ли уже списание для кабинета сегодня
                bonus_cnt_res = await session.execute(
                    select(func.count(WBBonusPayment.id)).where(
                        WBBonusPayment.wb_cabinet_id == cabinet_id,
                        func.date(WBBonusPayment.transaction_date_time) == current_date,
                        WBBonusPayment.operation_type == "auto_subtract",
                        WBBonusPayment.amount < 0,
                    )
                )
                balance_cnt_res = await session.execute(
                    select(func.count(WBBalancePayment.id)).where(
                        WBBalancePayment.wb_cabinet_id == cabinet_id,
                        func.date(WBBalancePayment.transaction_date_time) == current_date,
                        WBBalancePayment.operation_type == "auto_subtract",
                        WBBalancePayment.amount < 0,
                    )
                )
                if (bonus_cnt_res.scalar() or 0) > 0 or (balance_cnt_res.scalar() or 0) > 0:
                    logger.debug(f"Кабинет {cabinet_id} уже обработан за {current_date} (DB)")
                    continue

                # Получаем кабинет и рассчитываем общую стоимость
                wb_cabinet = cabinet
                shop_id = str(wb_cabinet.shop_id)
                logger.debug(f"Кабинет {cabinet_id}: расчет стоимости для магазина {shop_id}")
                price_for_shop_for_day = await pricer.get_price_for_day_for_shop(shop_id)
                logger.debug(f"Кабинет {cabinet_id}: price_for_shop_for_day={price_for_shop_for_day}")

                calculated_bonus = float(wb_cabinet.calculated_bonus or 0)
                calculated_balance = float(wb_cabinet.calculated_balance or 0)
                logger.debug(
                    f"Кабинет {cabinet_id}: calculated_bonus={calculated_bonus}, "
                    f"calculated_balance={calculated_balance}"
                )

                if price_for_shop_for_day <= 0:
                    logger.debug(f"Кабинет {cabinet_id}: нулевая сумма списания — пропуск")
                    continue

                payment_successful = False

                # Списание для всего кабинета
                if calculated_bonus >= price_for_shop_for_day:
                    bonus_payment = WBBonusPayment(
                        wb_cabinet_id=cabinet_id,
                        amount=-price_for_shop_for_day,
                        description=f"Ежедневное списание за {len(cabinet_campaigns)} кампаний, дата: {current_date}",
                        operation_type="auto_subtract",
                        transaction_date_time=datetime.now(),
                    )
                    session.add(bonus_payment)
                    logger.debug(f"Кабинет {cabinet_id}: списание бонусов {price_for_shop_for_day}")
                    payment_successful = True
                elif calculated_balance >= price_for_shop_for_day:
                    balance_payment = WBBalancePayment(
                        wb_cabinet_id=cabinet_id,
                        amount=-price_for_shop_for_day,
                        description=f"Ежедневное списание за {len(cabinet_campaigns)} кампаний, дата: {current_date}",
                        operation_type="auto_subtract",
                        transaction_date_time=datetime.now(),
                    )
                    session.add(balance_payment)
                    logger.debug(f"Кабинет {cabinet_id}: списание баланса {price_for_shop_for_day}")
                    payment_successful = True
                elif calculated_bonus + calculated_balance >= price_for_shop_for_day:
                    remaining_amount = price_for_shop_for_day
                    if calculated_bonus > 0:
                        bonus_to_charge = min(calculated_bonus, remaining_amount)
                        bonus_payment = WBBonusPayment(
                            wb_cabinet_id=cabinet_id,
                            amount=-bonus_to_charge,
                            description=f"Ежедневное списание за {len(cabinet_campaigns)} кампаний, дата: {current_date}",
                            operation_type="auto_subtract",
                            transaction_date_time=datetime.now(),
                        )
                        session.add(bonus_payment)
                        remaining_amount -= bonus_to_charge
                        logger.debug(
                            f"Кабинет {cabinet_id}: списание бонусов {bonus_to_charge}, остаток {remaining_amount}"
                        )
                    if remaining_amount > 0:
                        balance_payment = WBBalancePayment(
                            wb_cabinet_id=cabinet_id,
                            amount=-remaining_amount,
                            description=f"Ежедневное списание за {len(cabinet_campaigns)} кампаний, дата: {current_date}",
                            operation_type="auto_subtract",
                            transaction_date_time=datetime.now(),
                        )
                        session.add(balance_payment)
                        logger.debug(
                            f"Кабинет {cabinet_id}: списание баланса {remaining_amount} для остатка платежа"
                        )
                    payment_successful = True
                else:
                    # Недостаточно средств — деактивируем все кампании кабинета
                    for campaign in cabinet_campaigns:
                        campaign.bot_active = False
                        campaign.auto_update_white_list = False
                        campaign.auto_update_target_place = False
                    logger.debug(f"Кабинет {cabinet_id}: деактивировано кампаний: {len(cabinet_campaigns)}")
                else:
                    payment_description = (
                        f"Ежедневное списание за {len(cabinet_campaigns)} кампаний, дата: {current_date}"
                    )
                    now_dt = datetime.now()
                    if bonus_to_use > 0:
                        bonus_payment = WBBonusPayment(
                            wb_cabinet_id=cabinet_id,
                            amount=-bonus_to_use,
                            description=payment_description,
                            operation_type="auto_subtract",
                            transaction_date_time=now_dt,
                        )
                        session.add(bonus_payment)
                        logger.debug(
                            f"Кабинет {cabinet_id}: списание бонусов {bonus_to_use} из {price_for_shop_for_day}"
                        )
                    if balance_to_use > 0:
                        balance_payment = WBBalancePayment(
                            wb_cabinet_id=cabinet_id,
                            amount=-balance_to_use,
                            description=payment_description,
                            operation_type="auto_subtract",
                            transaction_date_time=now_dt,
                        )
                        session.add(balance_payment)
                        logger.debug(
                            f"Кабинет {cabinet_id}: списание баланса {balance_to_use} из {price_for_shop_for_day}"
                        )

                # История по кампаниям: делим общую сумму поровну
                if payment_successful:
                    price_per_campaign = price_for_shop_for_day / len(cabinet_campaigns) if cabinet_campaigns else 0
                    logger.debug(
                        f"Кабинет {cabinet_id}: распределение по {len(cabinet_campaigns)} кампаниям, "
                        f"цена за кампанию={price_per_campaign}"
                    )
                    for campaign in cabinet_campaigns:
                        existing = await session.execute(
                            select(AdvPayment).where(
                                AdvPayment.adv_setting_id == campaign.id,
                                AdvPayment.date == current_date,
                            )
                        )
                        if existing.scalar_one_or_none() is None:
                            payment = AdvPayment(
                                date=current_date,
                                amount=price_per_campaign,
                                adv_setting_id=campaign.id,
                            )
                            session.add(payment)
                            logger.debug(
                                f"Кабинет {cabinet_id}: создан AdvPayment для adv_setting={campaign.id} "
                                f"на сумму {price_per_campaign}"
                            )
                        else:
                            logger.debug(
                                f"Кабинет {cabinet_id}: AdvPayment уже существует для adv_setting={campaign.id}, пропуск"
                            )
                else:
                    logger.debug(
                        f"Кабинет {cabinet_id}: списание не выполнено, AdvPayment создаваться не будет"
                    )

                processed_cabinet_ids.append(cabinet_id)

            except Exception as e:
                logger.error(f"Ошибка при обработке кабинета {cabinet_id}: {e}")
                await session.rollback()
                raise
            finally:
                # Снимаем advisory-лок
                await session.execute(
                    text("SELECT pg_advisory_unlock(:lock_id)"),
                    {"lock_id": cabinet_id + 1_000_000},
                )

        # Один общий commit для всех кабинетов
        try:
            await session.commit()
            logger.debug(f"Успешно обработаны платежи для {len(processed_cabinet_ids)} кабинетов")

            # Отмечаем в Redis по кабинетам после успешного коммита
            for cabinet_id in processed_cabinet_ids:
                try:
                    await redis_manager.set_billing_process_for_day(cabinet_id, current_date)
                except Exception as e:
                    logger.error(f"Не удалось отметить Redis для кабинета {cabinet_id}: {e}")

        except Exception as e:
            logger.error(f"Ошибка при коммите: {e}")
            await session.rollback()
            raise
