import asyncio
from typing import TYPE_CHECKING

from aiogram import Bot
from aiohttp import ClientSession
from sqlalchemy import and_, or_, select

from app.core.wb_api.data_classes.adv import Balances
from app.core.wb_api.mixins.excs import (
    AdvNotFoundInWBError,
    CardNotFoundInWB,
    NotChangeError,
)
from app.modules.common_slaves.wildberries import wb_db_manager
from app.settings import settings
from app.utils.db.session_maker import get_async_session_maker as sm

from ...common_slaves.wildberries.models import AdvSetting, WBCabinet
from .exc import (
    CardsNotFoundForShopError,
    NotEnoughBalanceOnShopError,
    StartComplexAdvError,
)
from .wb_api import WBApi

if TYPE_CHECKING:
    from ...common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
import logging

logger = logging.getLogger(__name__)


class MainAdvManager:
    def __init__(self, access: "WBCabinetAccess", client_session: ClientSession):
        self.access = access
        self.wb_api = WBApi(access, client_session)

    async def _create_search_adv(self, nmid: int, name: str) -> int:
        adv_name = name
        adv_adv = await self.wb_api.create_search_adv([nmid], adv_name)
        await self.wb_api.rename_adv(adv_adv, new_name=adv_name)

        return adv_adv

    async def _create_auto_adv(
        self, name: str, SubjectID: int, balance_type: int, start_status: bool
    ) -> int:
        return await self.wb_api.create_auto_adv(name, SubjectID, balance_type, start_status)

    async def upcast_auto_adv(self, nmid: int, auto_adv_id: int, user_telegram_id: int, bot: Bot):
        await bot.send_message(
            user_telegram_id, f"Пытаюсь найти и настроить Авто-РК для артикула {nmid}"
        )
        start_delay = 10 * 60
        global_max_attempts = 10
        for attempt in range(global_max_attempts):
            max_attempts = 3
            for _ in range(max_attempts):
                try:
                    advs = await self.wb_api.get_advs([auto_adv_id])
                    break
                except AdvNotFoundInWBError:
                    logger.info(
                        f"Кампания {auto_adv_id} не найдена после создания,"
                        f" следующая попытка через {start_delay} секунд"
                    )
                    await asyncio.sleep(start_delay)
                    start_delay *= 2
            else:
                raise AdvNotFoundInWBError(
                    f"Кампания {auto_adv_id} не найдена после создания в API,"
                    f" проверьте ее наличие в рекламном кабинете WB"
                )

            adv = advs[0]
            nmids_in_adv = adv.nmids
            if nmids_in_adv != [nmid]:
                await bot.send_message(
                    user_telegram_id,
                    f"Артикулы в РК {adv.advertId},"
                    f" не соответствуют артикулу {nmid}, "
                    f" обновляю артикулы в РК {adv.advertId}",
                )
                nmids_for_add = list({nmid} - set(nmids_in_adv))
                nmids_for_del = list(set(nmids_in_adv) - {nmid})
                if len(nmids_for_del) >= 100:
                    nmids_for_del = nmids_for_del[:99]
                    nmids_for_add = []

                if nmid not in nmids_in_adv:
                    try:
                        await self.wb_api.update_nmids_in_adv(auto_adv_id, nmids_for_add, [])
                    except Exception as exc:
                        logger.error(exc, exc_info=True)
                        pass
                try:
                    await self.wb_api.update_nmids_in_adv(auto_adv_id, [], nmids_for_del)
                except Exception as exc:
                    logger.error(exc, exc_info=True)
                    pass
                await asyncio.sleep(60 * 3)
            else:
                await bot.send_message(
                    user_telegram_id,
                    f"Артикулы в РК {adv.advertId},"
                    f" соответствуют артикулу {nmid} согласно данным API "
                    f"Проверьте правильность в кабинете WB",
                )
                break

    async def create_complex_advs(
        self, bot: Bot, user_telegram_id, nmid: int, hard_mode
    ) -> tuple[int, int]:
        exist_adv: AdvSetting = await self.get_adv_setting_by_nmid(nmid)
        if not exist_adv or hard_mode is True or exist_adv.active_status in ["refused", "done"]:
            balances = await self.wb_api.get_adv_balances()
            try:
                target_card = await self.wb_api.get_card_by_text(nmid)
            except CardNotFoundInWB:
                raise CardsNotFoundForShopError(
                    f"Карточка с артикулом {nmid} не найдена на Wildberries"
                )
            wb_cabinet = self.access.wb_cabinet
            assert wb_cabinet is not None
            async with sm() as session:
                await wb_db_manager.update_cards_in_db(
                    [target_card],
                    wb_cabinet,
                )
            name = target_card.name
            new_adv_name = str(nmid) + " " + name
            new_adv_name = new_adv_name[:128]
            try:
                balance_type_int, balance_property_str = self._get_balance_type(balances)
            except NotEnoughBalanceOnShopError as exc:
                raise exc

            subjectID = target_card.subjectID
            auto_adv_id: int = await self._create_auto_adv(
                new_adv_name, subjectID, balance_type_int, start_status=False
            )

            setattr(
                balances,
                balance_property_str,
                getattr(balances, balance_property_str) - 1000,
            )

            search_adv_id = await self._create_search_adv(nmid, new_adv_name)
            result: int = await self.wb_api.add_to_balance(search_adv_id, balance_type_int, 1000)
            logger.debug(f"Баланс успешно пополнен, новый баланс: {result}")

            setattr(
                balances,
                balance_property_str,
                getattr(balances, balance_property_str) - 1000,
            )
            async with sm(read_only=False) as session:
                assert self.access.wb_cabinet is not None
                wb_cabinet_original_id: int = self.access.wb_cabinet.id
                stmt = select(WBCabinet).where(WBCabinet.id == wb_cabinet_original_id)
                wb_cabinet: WBCabinet = (await session.execute(stmt)).scalar()
                new_adv = AdvSetting()
                new_adv.adv_id = auto_adv_id
                new_adv.search_adv_id = search_adv_id
                new_adv.max_place = 1
                new_adv.max_cpm = 250
                new_adv.reset_place = True
                new_adv.name = new_adv_name
                new_adv.bidder_active = False
                new_adv.wb_cabinet = wb_cabinet
                new_adv.parsing_active = False
                new_adv.bot_active = True
                new_adv.auto_adv_target_status = False
                new_adv.auto_update_white_list = False
                new_adv.auto_update_target_place = False
                new_adv.active_status = "created_by_bot"
                new_adv.type = 8
                new_adv.nmids = [nmid]
                new_adv.hard_min_ctr = 0.1
                session.add(new_adv)
                await session.commit()

            logger.info("Выжидаю 3 минуты перед обновлением артикулов РК")
            await asyncio.sleep(60 * 3)
        else:
            auto_adv_id = exist_adv.adv_id
            search_adv_id = exist_adv.search_adv_id
            await bot.send_message(
                user_telegram_id,
                f"Кампания для артикула {nmid} уже существует :"
                f" Авто: {auto_adv_id}, Аукцион {search_adv_id},"
                f"Делаю попытку правильно настроить и запустить РК",
            )
        try:
            await self.upcast_auto_adv(nmid, auto_adv_id, user_telegram_id, bot)
        except AdvNotFoundInWBError as exc:
            exc.auto_adv_id = auto_adv_id
            exc.search_adv_id = search_adv_id
            raise exc

        await bot.send_message(
            user_telegram_id,
            f"Авто-РК для артикула {nmid} настроен, запускаю комплексную кампанию",
        )
        try:
            await self.start_complex_advs(nmid, auto_adv_id, search_adv_id)
            await bot.send_message(
                user_telegram_id,
                f"Отправлены запросы на запуск РК для артикула {nmid},"
                f" проверьте правильность запуска в кабинете WB: "
                f"ID Авто-РК: {auto_adv_id}, ID Поисковой РК: {search_adv_id}",
            )
        except StartComplexAdvError as exc:
            exc.auto_adv_id = auto_adv_id
            exc.search_adv_id = search_adv_id
            raise exc
        return auto_adv_id, search_adv_id

    async def start_complex_advs(self, nmid, auto_adv_id, search_adv_id):
        advs_for_start = [auto_adv_id]
        if settings.START_AUCTION_ON_CREATING_ADV:
            advs_for_start.append(search_adv_id)

        advs = await self.wb_api.get_advs(advs_for_start)
        auto_adv = advs[0]
        if auto_adv.nmids != [nmid]:
            raise NotChangeError("Артикулы не соответствуют")
        advs_to_start = [adv for adv in advs if adv.status_native != "started"]
        for adv in advs_to_start:
            try:
                await self.wb_api.start_adv(adv.advertId)
            except:
                logger.error("Ошибка запуска РК", exc_info=True)
                continue
        async with sm(read_only=False) as session:
            stmt = select(AdvSetting).where(AdvSetting.adv_id == auto_adv_id)
            result = await session.execute(stmt)
            adv_setting: AdvSetting = result.scalar()
            adv_setting.active_status = "started"
            await session.commit()

    @staticmethod
    async def get_adv_setting_by_nmid(nmid: int) -> AdvSetting:
        async with sm() as session:
            stmt = select(AdvSetting).where(
                and_(
                    AdvSetting.active_status.not_in(["refused", "done"]),
                    or_(
                        and_(
                            AdvSetting.name.regexp_match(
                                r".*<!-\[\d+]-!>.*"
                            ),  # Проверяем первый паттерн
                            AdvSetting.name.regexp_match(
                                rf".*{nmid}.*"
                            ),  # Проверяем второй паттерн
                        ),
                        # Дополнительно можно вернуть этот блок, если нужно
                        and_(
                            AdvSetting.nmids == [nmid],
                            AdvSetting._search_adv_id != None,
                        ),
                    ),
                )
            )

            result = await session.execute(stmt)
            adv_settings = result.all()
            if adv_settings:
                return adv_settings[0][0]

    @staticmethod
    def _check_enough_balance(balances: Balances) -> bool:
        balance = balances.balance
        net = balances.net
        bonus = balances.bonus
        full_balance: list[int] = [balance, net, bonus]
        logger.debug(f"Балансы: {full_balance}")
        if sum(full_balance) >= 2000 or len(list(filter(lambda x: x >= 1000, full_balance))) >= 2:
            return True
        return False

    def _get_balance_type(self, balances: Balances) -> (int, str):
        is_balance_enough: bool = self._check_enough_balance(balances)

        if not is_balance_enough:
            raise NotEnoughBalanceOnShopError()

        balance_rows = [
            (balances.balance, "balance"),
            (balances.net, "net"),
            (balances.bonus, "bonus"),
        ]

        min_balance_property_name = min(list(filter(lambda row: row[0] > 1000, balance_rows)))[1]

        if min_balance_property_name == "balance":
            balance_type = 0
        elif min_balance_property_name == "net":
            balance_type = 1
        elif min_balance_property_name == "bonus":
            balance_type = 3
        else:
            raise Exception("Неизвестный тип баланса")
        return balance_type, min_balance_property_name
