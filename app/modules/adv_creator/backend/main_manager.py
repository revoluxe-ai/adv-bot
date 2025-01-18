import asyncio

from aiogram import Bot
from sqlalchemy import select, or_, and_, exists
from app.utils.db.session_maker import get_async_session_maker as sm
from app.core.wb_api.data_classes.card_from_wb import CardFromWB
from app.core.wb_api.mixins.excs import NotCanDeleteAllProductsError, ItemCategoryNotInStockError, NotChangeError, \
    AdvNotFoundInWBError
from app.modules.common_slaves.wildberries import wb_db_manager
from app.core.wb_api.data_classes.adv import Balances
from .exc import CardsNotFoundForShopError, ComplexAdvsExistsError, NotEnoughBalanceOnShopError, StartComplexAdvError
from .wb_api import WBApi
from ...common_slaves.wildberries.models import WBCard, AdvSetting, WBCabinet
from ...common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
from app.client_bot.bot import bot
import logging


logger = logging.getLogger(__name__)


class MainAdvManager:
    def __init__(self, access: WBCabinetAccess):
        self.access = access
        self.wb_api = WBApi(access)

    async def _create_search_adv(self,  nmid: int, name) -> int:
        adv_name = name
        adv_adv = await self.wb_api.create_search_adv([nmid], adv_name)
        await self.wb_api.rename_adv(adv_adv, new_name = adv_name)

        return adv_adv

    async def _create_auto_adv(self, name, SubjectID: int, balance_type: int, start_status: bool) -> int:
        return await self.wb_api.create_auto_adv(name, SubjectID, balance_type, start_status)


    async def create_complex_advs(self, nmid: int, hard_mode) -> (int, int):
        exist_adv: AdvSetting = await self.get_adv_setting_by_nmid(nmid)
        if not exist_adv or hard_mode is True:
            balances = await self.wb_api.get_adv_balances()

            target_card = await self.wb_api.get_card_by_text(nmid)
            await wb_db_manager.update_cards_in_db([target_card], self.access.wb_cabinet)

            name = target_card.name
            new_adv_name = str(nmid) + ' ' + name
            new_adv_name = new_adv_name[:128]

            balance_type_int, balance_property_str = self._get_balance_type(balances)
            subjectID = target_card.subjectID
            try:
                auto_adv_id: int = await self._create_auto_adv(
                    new_adv_name,
                    subjectID,
                    balance_type_int,
                    start_status=False)
            except ItemCategoryNotInStockError as e:
                logger.error('Нет остатков в данной категории')
                raise e

            setattr(balances, balance_property_str, getattr(balances, balance_property_str) - 1000)

            search_adv_id = await self._create_search_adv(nmid, new_adv_name)
            result: int = await self.wb_api.add_to_balance(search_adv_id, balance_type_int, 1000)
            logger.debug(f'Баланс успешно пополнен, новый баланс: {result}')

            setattr(balances, balance_property_str, getattr(balances, balance_property_str) - 1000)
            async with sm(read_only=False) as session:
                stmt = select(WBCabinet).where(WBCabinet.id == self.access.wb_cabinet.id)
                wb_cabinet: WBCabinet = (await session.execute(stmt)).scalar()
                new_adv = AdvSetting()
                new_adv.adv_id = auto_adv_id
                new_adv.search_adv_id = search_adv_id
                new_adv.max_place = 1
                new_adv.name = new_adv_name
                new_adv.bidder_active = True
                new_adv.wb_cabinet = wb_cabinet
                new_adv.parsing_active = True
                new_adv.bot_active = True
                new_adv.active_status = 'created_by_bot'
                new_adv.type = 8
                new_adv.nmids = [nmid]
                new_adv.hard_min_ctr = 0.1
                session.add(new_adv)
                await session.commit()

            logger.info('Выжидаю 3 минуты перед обновлением артикулов РК')
            await asyncio.sleep(60*3)
        else:
            auto_adv_id = exist_adv.adv_id
            search_adv_id = exist_adv.search_adv_id
            logger.info(f'Кампания {auto_adv_id}, {search_adv_id} уже существует')

        try:
             advs = (await self.wb_api.get_advs([auto_adv_id]))
        except AdvNotFoundInWBError:
            logger.info(f'Кампания {auto_adv_id} не найдена после создания')
            raise AdvNotFoundInWBError(f'Кампания {auto_adv_id} не найдена после создания')
        adv = advs[0]
        nmids_in_adv = adv.nmids
        if nmids_in_adv != [nmid]:
            logger.error(f'Не соответствует цель ({nmid}) и факт: {nmids_in_adv}' )
            nmids_for_add = list({nmid} - set(nmids_in_adv))
            nmids_for_del = list(set(nmids_in_adv) - {nmid})
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
            await asyncio.sleep(60*3)
            await self.start_complex_advs(nmid, auto_adv_id, search_adv_id)
            return advs
        else:
            await self.start_complex_advs(nmid, auto_adv_id, search_adv_id)
            return advs


    async def start_complex_advs(self, nmid,  auto_adv_id, search_adv_id):
        advs = await self.wb_api.get_advs([auto_adv_id, search_adv_id])
        auto_adv = advs[0]
        if auto_adv.nmids != [nmid]:
            raise NotChangeError('Артикулы не соответствуют')
        advs_to_start = [adv for adv in advs if adv.status_native != 'started']
        for adv in advs_to_start:
            try:
                await self.wb_api.start_adv(adv.advertId)
            except:
                logger.error('Ошибка запуска РК', exc_info=True)
                continue
        advs = await self.wb_api.get_advs([auto_adv_id, search_adv_id])

        if any([adv.status_native != 'started' for adv in advs]):
            raise StartComplexAdvError(f'Не удалось запустить Комплекс РК для артикула {nmid}'
                                 f'Кампания {auto_adv_id}, {search_adv_id} не запущена')
        else:
            async with sm(read_only=False) as session:
                stmt = select(AdvSetting).where(AdvSetting.adv_id == auto_adv_id)
                result = await session.execute(stmt)
                adv_setting: AdvSetting = result.scalar()
                adv_setting.active_status = 'started'
                await session.commit()




    async def get_adv_setting_by_nmid(self, nmid: int) -> AdvSetting:
        async with sm() as session:
            stmt = select(AdvSetting) \
                .where(
                and_(
                    AdvSetting.active_status.not_in(['refused', 'done']),
                    or_(
                        and_(
                            AdvSetting.name.regexp_match(r'.*<!-\[\d+]-!>.*'),  # Проверяем первый паттерн
                            AdvSetting.name.regexp_match(fr'.*{nmid}.*')  # Проверяем второй паттерн
                        ),
                        # Дополнительно можно вернуть этот блок, если нужно
                        and_(
                            AdvSetting.nmids == [nmid],
                            AdvSetting._search_adv_id != None
                        )
                    )))


            result = await session.execute(stmt)
            adv_settings = result.all()
            if adv_settings:
                return adv_settings[0][0]


    def _check_enough_balance(self, balances: Balances) -> bool:
        balance = balances.balance
        net = balances.net
        bonus = balances.bonus
        full_balance: list[int] = [balance, net, bonus]
        if sum(full_balance) >= 2000 or len(list(filter(lambda x: x >= 1000, full_balance))) >= 2:
            return True
        return False

    def _get_balance_type(self, balances: Balances) -> (int, str):
        is_balance_enough: bool = self._check_enough_balance(balances)

        if not is_balance_enough:
            raise NotEnoughBalanceOnShopError()

        balance_rows = [(balances.balance, 'balance'), (balances.net, 'net'), (balances.bonus, 'bonus')]

        min_balance_property_name = min(list(filter(lambda row: row[0] > 1000, balance_rows)))[1]

        if min_balance_property_name == 'balance':
            balance_type = 0
        elif min_balance_property_name == 'net':
            balance_type = 1
        elif min_balance_property_name == 'bonus':
            balance_type = 3
        else:
            raise Exception('Неизвестный тип баланса')
        return balance_type, min_balance_property_name




