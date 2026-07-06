from typing import TYPE_CHECKING, Literal, get_args

from aiogram import Bot
from aiohttp import ClientSession
from sqlalchemy import and_, or_, select, update
from sqlalchemy.dialects.postgresql import insert  # Добавляем импорт insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only, selectinload

from app.core.di.app_container import AppContainer
from app.core.di.di_manager import DIManager
from app.core.wb_api.data_classes.advs.other_classes import Balances
from app.client_bot.user_interface.services.auto_management_mode import (
    apply_new_campaign_free_defaults,
)
from app.core.wb_api.mixins.excs import CardNotFoundInWB

from ...common_slaves.wildberries.models.wb_cabinet import WBCabinet

from app.modules.common_slaves.wildberries import wb_db_manager
from app.shared.domains.wb.exceptions import NotEnoughBalanceOnShopError
from app.utils.db.session_maker import get_async_session_maker as sm
from .exc import (
    CardsNotFoundForShopError,
    AdvExistsForNmidError,
)
from .wb_api import WBApi
from ...common_slaves.wildberries.models import AdvSetting


from app.shared.domains.wb.utils.balance_source import (
    select_balance_source_from_response,
)

if TYPE_CHECKING:
    from ...common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
import logging

logger = logging.getLogger(__name__)

AdvType = Literal["auto", "auction", "complex"]


def get_name_for_adv(nmid: int, card_name: str, adv_type: AdvType) -> str:
    """Имя РК по шаблону (до 128 символов).

    - auto/auction: «Артикул Авто|Аукцион Название карточки» — для кампаний на стороне WB.
    - complex: «Артикул Название карточки» — для сущности бота (комплексная РК, объединяющая
      Авто и Аукцион); без слова Авто/Аукцион в середине.
    """
    if adv_type not in get_args(AdvType):
        raise ValueError(f"adv_type must be one of {get_args(AdvType)}")
    if adv_type == "auto":
        type_name = "Авто"
    elif adv_type == "auction":
        type_name = "Аукцион"
    elif adv_type == "complex":
        type_name = ""
    else:
        type_name = "НеизвестныйТипРК"
    full_name = f"{nmid}{' ' + type_name if type_name else ''} {card_name}"[:128]
    return full_name


class MainAdvManager:
    def __init__(self, access: "WBCabinetAccess", client_session: ClientSession):
        self.access = access
        self.wb_api = WBApi(access, client_session)

    async def _create_search_adv(self, nmid: int, name: str) -> int:
        adv_name = name
        adv_id: int = await self.wb_api.create_search_adv([nmid], adv_name)
        return adv_id

    async def _create_auto_adv(self, name: str, nmids: list[int]) -> int:
        return await self.wb_api.create_auto_adv(nmids, name)

    @staticmethod
    async def _apply_default_settings_to_adv(adv_id: int) -> None:
        async with sm(read_only=False) as session:
            stmt = (
                select(AdvSetting)
                .options(selectinload(AdvSetting.wb_cabinet))
                .where(AdvSetting.adv_id == adv_id)
                .with_for_update()
            )
            adv_setting: AdvSetting = (await session.execute(stmt)).scalar_one()
            # TODO(strategy-transition): Вынести переключение стратегий в общий хелпер!
            apply_new_campaign_free_defaults(adv_setting, adv_setting.wb_cabinet)
            await session.commit()

    @staticmethod
    async def _get_wb_cabinet_from_session(
        session: AsyncSession, wb_cabinet_id: int
    ) -> WBCabinet:
        stmt = select(WBCabinet).where(WBCabinet.id == wb_cabinet_id)
        wb_cabinet: WBCabinet = (await session.execute(stmt)).scalar_one()
        return wb_cabinet

    @staticmethod
    async def _perform_adv_setting_upsert(
        session: AsyncSession, adv_data: dict
    ) -> None:
        insert_stmt = insert(AdvSetting).values(adv_data)
        on_conflict_stmt = insert_stmt.on_conflict_do_update(
            index_elements=["adv_id"],
            set_={k: v for k, v in adv_data.items() if k != "adv_id"},
        )
        await session.execute(on_conflict_stmt)
        await session.commit()

    async def _create_search_adv_with_balance(
        self,
        nmid: int,
        card_name: str,
        balances: Balances,
        balance_type_int: int,
        balance_property_str: str,
    ) -> int:
        auction_name = get_name_for_adv(nmid, card_name, adv_type="auction")
        search_adv_id = await self._create_search_adv(nmid, auction_name)
        await self.wb_api.add_to_balance(search_adv_id, balance_type_int, 1000)
        setattr(
            balances,
            balance_property_str,
            getattr(balances, balance_property_str) - 1000,
        )
        return search_adv_id

    async def _create_auto_adv_with_balance(
        self,
        nmid: int,
        card_name: str,
        balances: Balances,
        balance_type_int: int,
        balance_property_str: str,
    ) -> int:
        auto_name = get_name_for_adv(nmid, card_name, adv_type="auto")
        auto_adv_id = await self._create_auto_adv(auto_name, [nmid])
        await self.wb_api.add_to_balance(auto_adv_id, balance_type_int, 1000)
        setattr(
            balances,
            balance_property_str,
            getattr(balances, balance_property_str) - 1000,
        )
        return auto_adv_id

    @staticmethod
    async def get_all_adv_ids_for_nmid(wb_cabinet_id: int, nmid: int) -> set[int]:
        """Возвращает adv_id всех РК по артикулу (включая авто-only без search_adv_id)."""
        async with sm() as session:
            stmt = select(AdvSetting.adv_id).where(
                and_(
                    AdvSetting.wb_cabinet_id == wb_cabinet_id,
                    AdvSetting.nmids == [nmid],
                    AdvSetting.active_status.not_in(["refused", "done"]),
                    AdvSetting.type.in_([8, 9]),
                )
            )
            result = await session.execute(stmt)
            out = {row[0] for row in result.all()}
        return out

    async def _create_complex_advs(self, nmid: int) -> tuple[int, int]:
        wb_cabinet = self.access.wb_cabinet
        assert wb_cabinet is not None
        shop_id = str(wb_cabinet.shop_id)

        balances = await self.wb_api.get_adv_balances()
        try:
            async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
                factory = (
                    container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
                )
                hub = factory.get_wb_manager_hub(shop_id)
                _card_info, target_card = (
                    await hub.wb_data_manager.products_manager.get_card_by_nmid_for_db(
                        nmid
                    )
                )
        except CardNotFoundInWB:
            raise CardsNotFoundForShopError(
                f"Карточка с артикулом {nmid} не найдена на Wildberries"
            )
        await wb_db_manager.update_cards_in_db(
            [target_card],
            wb_cabinet,
        )
        try:
            balance_type_int, balance_property_str = self._get_balance_type(
                balances, min_required=2000
            )
        except NotEnoughBalanceOnShopError as exc:
            raise exc
        card_name = target_card.name

        auto_adv_id: int = await self._create_auto_adv_with_balance(
            nmid, card_name, balances, balance_type_int, balance_property_str
        )
        logger.debug("Авто-РК создана и пополнена, ID: %s", auto_adv_id)

        search_adv_id = await self._create_search_adv_with_balance(
            nmid, card_name, balances, balance_type_int, balance_property_str
        )
        logger.debug("Поисковая РК создана и пополнена, ID: %s", search_adv_id)

        complex_adv_name = get_name_for_adv(nmid, card_name, adv_type="complex")

        async with sm(read_only=False) as session:
            assert self.access.wb_cabinet is not None
            wb_cabinet_original_id: int = self.access.wb_cabinet.id
            wb_cabinet = await self._get_wb_cabinet_from_session(
                session, wb_cabinet_original_id
            )

            # Подготавливаем данные для upsert
            # TODO(strategy-transition): Вынести переключение стратегий в общий хелпер!
            adv_data = {
                "adv_id": auto_adv_id,
                "_search_adv_id": search_adv_id,  # Исправлено на _search_adv_id
                "max_place": 1,
                "max_cpm": wb_cabinet.default_max_cpm,
                "reset_place": True,
                "name": complex_adv_name,
                "bidder_active": False,
                "wb_cabinet_id": wb_cabinet.id,
                "parsing_active": False,
                "bot_active": False,
                "auto_adv_target_status": False,
                "auto_update_white_list": False,
                "auto_update_target_place": False,
                "active_status": "created_by_bot",
                "type": 9,
                "nmids": [nmid],
                "hard_min_ctr": 0.1,
            }
            await self._perform_adv_setting_upsert(session, adv_data)

        await self._apply_default_settings_to_adv(auto_adv_id)

        return auto_adv_id, search_adv_id

    async def create_complex_advs(
        # TODO: Бот не видит, что РК завершены и не дает создать новую РК по тому же артикулу
        self,
        bot: Bot,
        user_telegram_id,
        nmid: int,
        hard_mode: bool,
    ) -> tuple[int, int] | None:
        assert self.access.wb_cabinet is not None
        wb_cabinet_id = self.access.wb_cabinet.id
        all_adv_ids = await self.get_all_adv_ids_for_nmid(wb_cabinet_id, nmid)
        exist_adv_ids_rows = [(aid, None) for aid in all_adv_ids]
        if not hard_mode and all_adv_ids:
            raise AdvExistsForNmidError(exist_adv_ids_rows)

        if all_adv_ids:
            await self.__turn_off_advs(bot, user_telegram_id, all_adv_ids)

        # Кампаний не найдено - создавать новую
        auto_adv_id, search_adv_id = await self._create_complex_advs(nmid)

        return auto_adv_id, search_adv_id

    async def create_search_only(
        self,
        bot: Bot,
        user_telegram_id: int,
        nmid: int,
        existing_auto_adv_id: int,
        hard_mode: bool = True,
    ) -> int:
        """Создать только поисковую РК и привязать к существующей авто-кампании (1000 ₽)."""
        wb_cabinet = self.access.wb_cabinet
        assert wb_cabinet is not None
        wb_cabinet_id = wb_cabinet.id
        shop_id = str(wb_cabinet.shop_id)

        balances = await self.wb_api.get_adv_balances()
        try:
            async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
                factory = (
                    container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
                )
                hub = factory.get_wb_manager_hub(shop_id)
                _card_info, target_card = (
                    await hub.wb_data_manager.products_manager.get_card_by_nmid_for_db(
                        nmid
                    )
                )
        except CardNotFoundInWB:
            raise CardsNotFoundForShopError(
                f"Карточка с артикулом {nmid} не найдена на Wildberries"
            )
        await wb_db_manager.update_cards_in_db([target_card], wb_cabinet)

        try:
            balance_type_int, balance_property_str = self._get_balance_type(
                balances, min_required=1000
            )
        except NotEnoughBalanceOnShopError as exc:
            raise exc

        if hard_mode:
            all_adv_ids = await self.get_all_adv_ids_for_nmid(wb_cabinet_id, nmid)
            if all_adv_ids:
                await self.__turn_off_advs(bot, user_telegram_id, all_adv_ids)

        card_name = target_card.name
        auto_name = get_name_for_adv(nmid, card_name, adv_type="auto")[:100]
        advs = await self.wb_api.get_advs([existing_auto_adv_id])
        current_auto_name = advs[0].name if advs else ""
        if current_auto_name.strip() != auto_name.strip():
            await self.wb_api.rename_adv(existing_auto_adv_id, auto_name)

        search_adv_id = await self._create_search_adv_with_balance(
            nmid, card_name, balances, balance_type_int, balance_property_str
        )

        complex_adv_name = get_name_for_adv(nmid, card_name, adv_type="complex")
        async with sm(read_only=False) as session:
            wb_cabinet_from_db = await self._get_wb_cabinet_from_session(
                session, wb_cabinet_id
            )
            # TODO(strategy-transition): Вынести переключение стратегий в общий хелпер!
            adv_data = {
                "adv_id": existing_auto_adv_id,
                "_search_adv_id": search_adv_id,
                "max_place": 1,
                "max_cpm": wb_cabinet_from_db.default_max_cpm,
                "reset_place": True,
                "name": complex_adv_name,
                "bidder_active": False,
                "wb_cabinet_id": wb_cabinet_from_db.id,
                "parsing_active": False,
                "bot_active": False,
                "auto_adv_target_status": False,
                "auto_update_white_list": False,
                "auto_update_target_place": False,
                "active_status": "created_by_bot",
                "type": 9,
                "nmids": [nmid],
                "hard_min_ctr": 0.1,
            }
            await self._perform_adv_setting_upsert(session, adv_data)

        await self._apply_default_settings_to_adv(existing_auto_adv_id)

        return search_adv_id

    async def create_auto_only(
        self,
        bot: Bot,
        user_telegram_id: int,
        nmid: int,
        existing_search_adv_id: int,
        hard_mode: bool = True,
    ) -> int:
        """Создать только авто-РК и привязать к существующей поисковой (1000 ₽)."""
        wb_cabinet = self.access.wb_cabinet
        assert wb_cabinet is not None
        wb_cabinet_id = wb_cabinet.id
        shop_id = str(wb_cabinet.shop_id)

        balances = await self.wb_api.get_adv_balances()
        try:
            async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
                factory = (
                    container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
                )
                hub = factory.get_wb_manager_hub(shop_id)
                _card_info, target_card = (
                    await hub.wb_data_manager.products_manager.get_card_by_nmid_for_db(
                        nmid
                    )
                )
        except CardNotFoundInWB:
            raise CardsNotFoundForShopError(
                f"Карточка с артикулом {nmid} не найдена на Wildberries"
            )
        await wb_db_manager.update_cards_in_db([target_card], wb_cabinet)

        try:
            balance_type_int, balance_property_str = self._get_balance_type(
                balances, min_required=1000
            )
        except NotEnoughBalanceOnShopError as exc:
            raise exc

        if hard_mode:
            all_adv_ids = await self.get_all_adv_ids_for_nmid(wb_cabinet_id, nmid)
            if all_adv_ids:
                await self.__turn_off_advs(bot, user_telegram_id, all_adv_ids)

        card_name = target_card.name
        auction_name = get_name_for_adv(nmid, card_name, adv_type="auction")[:100]
        advs = await self.wb_api.get_advs([existing_search_adv_id])
        current_search_name = advs[0].name if advs else ""
        if current_search_name.strip() != auction_name.strip():
            await self.wb_api.rename_adv(existing_search_adv_id, auction_name)

        auto_adv_id = await self._create_auto_adv_with_balance(
            nmid, card_name, balances, balance_type_int, balance_property_str
        )

        complex_adv_name = get_name_for_adv(nmid, card_name, adv_type="complex")
        async with sm(read_only=False) as session:
            wb_cabinet_from_db = await self._get_wb_cabinet_from_session(
                session, wb_cabinet_id
            )
            # TODO(strategy-transition): Вынести переключение стратегий в общий хелпер!
            adv_data = {
                "adv_id": auto_adv_id,
                "_search_adv_id": existing_search_adv_id,
                "max_place": 1,
                "max_cpm": wb_cabinet_from_db.default_max_cpm,
                "reset_place": True,
                "name": complex_adv_name,
                "bidder_active": False,
                "wb_cabinet_id": wb_cabinet_from_db.id,
                "parsing_active": False,
                "bot_active": False,
                "auto_adv_target_status": False,
                "auto_update_white_list": False,
                "auto_update_target_place": False,
                "active_status": "created_by_bot",
                "type": 9,
                "nmids": [nmid],
                "hard_min_ctr": 0.1,
            }
            await self._perform_adv_setting_upsert(session, adv_data)

        await self._apply_default_settings_to_adv(auto_adv_id)

        return auto_adv_id

    @staticmethod
    async def get_adv_ids_rows_by_nmid(nmid: int) -> list[tuple[int, int | None]]:
        async with sm() as session:
            stmt = (
                select(AdvSetting)
                .options(
                    load_only(
                        AdvSetting.adv_id,
                        AdvSetting._search_adv_id,  # noqa E1101
                        AdvSetting.name,
                    )
                )
                .where(
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
                                AdvSetting._search_adv_id is not None,  # noqa E1101
                            ),
                        ),
                        # TODOД не правильныый синтаксис условий in, ошибка попала в прод
                        AdvSetting.type.in_([8, 9]),  # Без устаревших типов РК
                    )
                )
            )

            result = await session.scalars(stmt)
            adv_settings = result.all()
            adv_ids_rows: list[tuple[int, int]] = []
            if adv_settings:
                for adv in adv_settings:
                    auto_adv_id = adv.adv_id
                    if search_adv_id := adv.search_adv_id:
                        adv_ids_rows.append(
                            (
                                auto_adv_id,
                                search_adv_id,
                            )
                        )
                return adv_ids_rows
            else:
                return []

    @staticmethod
    def _get_balance_type(
        balances: Balances, *, min_required: int = 2000
    ) -> tuple[int, str]:
        return select_balance_source_from_response(balances, min_required=min_required)

    async def _upcast_target_placement(self, adv_id, /, search, recommendations):
        await self.wb_api.upcast_target_placement(adv_id, search, recommendations)

    @staticmethod
    async def __turn_off_advs(bot, user_telegram_id, complex_adv_ids: set[int]):
        # TODO: Добавить логику остановки РК в кабинете WB через wb_api

        message = "Отключаю существующие для этого артикула кампании"
        await bot.send_message(user_telegram_id, message)

        stmt = (
            update(AdvSetting)
            .where(AdvSetting.adv_id.in_(complex_adv_ids))
            .values(
                bidder_active=False,
            )
        )
        async with sm(read_only=False) as session:
            await session.execute(stmt)
            await session.commit()
