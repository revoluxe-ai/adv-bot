import asyncio
from typing import TYPE_CHECKING, Literal, get_args

from aiogram import Bot
from aiohttp import ClientSession
from sqlalchemy import and_, or_, select, update
from sqlalchemy.orm import load_only

from app.client_bot import const
from app.core.wb_api.data_classes.advs.other_classes import Balances
from app.core.wb_api.mixins.excs import (
    CardNotFoundInWB,
)
from app.modules.common_slaves.wildberries import wb_db_manager
from app.utils.db.session_maker import get_async_session_maker as sm
from .exc import (
    CardsNotFoundForShopError,
    NotEnoughBalanceOnShopError, AdvExistsForNmidError,
)
from .wb_api import WBApi
from ...common_slaves.wildberries.models import AdvSetting, WBCabinet


if TYPE_CHECKING:
    from ...common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
import logging

logger = logging.getLogger(__name__)

AdvType = Literal["auto", "auction", 'complex']

class MainAdvManager:
    def __init__(self, access: "WBCabinetAccess", client_session: ClientSession):
        self.access = access
        self.wb_api = WBApi(access, client_session)

    async def _create_search_adv(self, nmid: int, name: str) -> int:
        adv_name = name
        adv_id: int = await self.wb_api.create_search_adv([nmid], adv_name)
        return adv_id

    async def _create_auto_adv(
        self, name: str, nmids: list[int]
    ) -> int:
        return await self.wb_api.create_auto_adv(
            nmids,
            name
        )

    async def __create_complex_advs(           
                self,
                nmid: int) -> tuple[int, int, bool]:

        balances = await self.wb_api.get_adv_balances()
        try:
            target_card = await self.wb_api.get_card_by_text(nmid)
        except CardNotFoundInWB:
            raise CardsNotFoundForShopError(
                f"Карточка с артикулом {nmid} не найдена на Wildberries"
            )
        wb_cabinet = self.access.wb_cabinet
        assert wb_cabinet is not None
        await wb_db_manager.update_cards_in_db(
            [target_card],  # type: ignore[list-item]
            wb_cabinet,
        )
        try:
            balance_type_int, balance_property_str = self._get_balance_type(
                balances
            )
        except NotEnoughBalanceOnShopError as exc:
            raise exc
        auto_name = self.__get_name_for_adv(nmid, target_card, adv_type="auto")
        auto_adv_id: int = await self._create_auto_adv(
            auto_name,  [nmid]
        )

        result: int = await self.wb_api.add_to_balance(
            auto_adv_id, balance_type_int, 1000
        )
        logger.debug("Баланс успешно пополнен, новый баланс: %s", result)
        setattr(
            balances,
            balance_property_str,
            getattr(balances, balance_property_str) - 1000,
        )
        auction_name = self.__get_name_for_adv(nmid, target_card, adv_type="auction")
        search_adv_id = await self._create_search_adv(nmid, auction_name)
        result: int = await self.wb_api.add_to_balance(
            search_adv_id, balance_type_int, 1000
        )
        logger.debug("Баланс успешно пополнен, новый баланс: %s", result)

        setattr(
            balances,
            balance_property_str,
            getattr(balances, balance_property_str) - 1000,
        )

        complex_adv_name = self.__get_name_for_adv(nmid, target_card, adv_type="complex")

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
            new_adv.name = complex_adv_name
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

        task_update_cpm_auto = self.wb_api.update_cpm(
            auto_adv_id,
            nmid,
            10,)

        task_update_cpm_auction = self.wb_api.update_cpm(
            search_adv_id,
            nmid,
            10, )

        try:
            await asyncio.gather(task_update_cpm_auto,
                                 task_update_cpm_auction)
            update_cpm_status = True
        except Exception as exc:
            logger.error(exc, exc_info=True)
            update_cpm_status = False

        return auto_adv_id, search_adv_id, update_cpm_status
    

    async def create_complex_advs(
        # TODO: Бот не видит, что РК завершены и не дает создать новую РК по тому же артикулу
        self,
        bot: Bot,
        user_telegram_id,
        nmid: int,
        hard_mode: bool,
    ) -> tuple[int, int] | None:
        exist_adv_ids_rows: list[tuple[int, int]] = await self.get_adv_ids_rows_by_nmid(nmid)
        if not hard_mode and exist_adv_ids_rows:
                raise AdvExistsForNmidError(exist_adv_ids_rows)

        if exist_adv_ids_rows:
            complex_adv_ids = {row[0] for row in exist_adv_ids_rows}
            await self.__turn_off_advs(bot, user_telegram_id, complex_adv_ids)

        # Кампаний не найдено - создавать новую
        auto_adv_id, search_adv_id, update_cpm_status = await self.__create_complex_advs(
           nmid
        )
        if not update_cpm_status:
            await bot.send_message(
                user_telegram_id,
                f"но не удалось установить стартовые ставки. "
                f"Пожалуйста, проверьте и установите ставки вручную. "
                f"ID Авто-РК: {auto_adv_id},"
                f" ID Поисковой РК: {search_adv_id}. "
                f"Если проблема повторится, обратитесь в поддержку {const.SUPPORT_LINK}."
            )

        return auto_adv_id, search_adv_id


    @staticmethod
    async def get_adv_ids_rows_by_nmid(nmid: int) -> list[tuple[int, int]]:
        async with sm() as session:
            stmt = select(AdvSetting)\
                .options(load_only(AdvSetting.adv_id,
                                   AdvSetting._search_adv_id, # noqa E1101
                                   AdvSetting.name)
                         ).where(
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
                            AdvSetting._search_adv_id is not None, # noqa E1101
                        ),
                    ),

                    AdvSetting.type in [8, 9]  # Без устаревших типов РК

                )
            )

            result = await session.scalars(stmt)
            adv_settings = result.all()
            adv_ids_rows: list[tuple[int, int]] = []
            if adv_settings:
                for adv in adv_settings:
                    auto_adv_id = adv.adv_id
                    search_adv_id = adv.search_adv_id
                    adv_ids_rows.append((auto_adv_id, search_adv_id,))
                return adv_ids_rows
            else:
                return []


    @staticmethod
    def _check_enough_balance(balances: Balances) -> bool:
        balance = balances.balance
        net = balances.net
        bonus = balances.bonus
        full_balance: list[int] = [balance, net, bonus]
        logger.debug(f"Балансы: {full_balance}")
        if (
            sum(full_balance) >= 2000
            or len(list(filter(lambda x: x >= 1000, full_balance))) >= 2
        ):
            return True
        return False

    def _get_balance_type(self, balances: Balances) -> tuple[int, str]:
        is_balance_enough: bool = self._check_enough_balance(balances)

        if not is_balance_enough:
            raise NotEnoughBalanceOnShopError()

        balance_rows = [
            (balances.balance, "balance"),
            (balances.net, "net"),
            (balances.bonus, "bonus"),
        ]

        min_balance_property_name = min(
            list(filter(lambda row: row[0] > 1000, balance_rows))
        )[1]

        if min_balance_property_name == "balance":
            balance_type = 0
        elif min_balance_property_name == "net":
            balance_type = 1
        elif min_balance_property_name == "bonus":
            balance_type = 3
        else:
            raise Exception("Неизвестный тип баланса")
        return balance_type, min_balance_property_name

    async def _upcast_target_placement(self, adv_id, /, search, recommendations):
        await self.wb_api.upcast_target_placement(adv_id, search, recommendations)

    @staticmethod
    async def __turn_off_advs(
                              bot,
                              user_telegram_id,
                              complex_adv_ids: set[int]):
        # TODO: Добавить логику остановки РК в кабинете WB через wb_api

        message = (
            "Отключаю существующие для этого артикула кампании"
        )
        await bot.send_message(
            user_telegram_id,
            message)


        stmt = update(AdvSetting).where(
            AdvSetting.adv_id.in_(complex_adv_ids)
        ).values(
            bidder_active=False,
        )
        async with sm(read_only=False) as session:
            await session.execute(stmt)
            await session.commit()

    @staticmethod
    def __get_name_for_adv(nmid, target_card, adv_type: AdvType):
        if adv_type not in get_args(AdvType):
            raise ValueError(f"adv_type must be one of {get_args(AdvType)}")
        base_name = target_card.name
        if adv_type == "auto":
            type_name = 'Авто'
        elif adv_type == "auction":
            type_name = 'Аукцион'
        elif adv_type == 'complex':
            type_name = ''
        else:
            type_name = 'НеизвестныйТипРК'
        full_name = f'{nmid} {type_name} {base_name}'[:128]
        return full_name

