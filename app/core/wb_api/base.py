from abc import ABC, abstractmethod
from .interface import InterfaceWBAPI

class BaseAPI(ABC, InterfaceWBAPI):


    @property
    @abstractmethod
    def _rights(self) -> set[str]:
        pass

    @property
    @abstractmethod
    def _only_read(self):
        pass

    @staticmethod
    def chunks(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    async def set_next_token(self):
        if self._free_tokens:
            self.headers = Headers(self._free_tokens.pop())
        else:
            wb_cabinet: WBCabinet = self.access.wb_cabinet
            try:
                async with sm(read_only=False) as session:
                    fresh_cabinet = await session.get(WBCabinet, wb_cabinet.id)
                    if fresh_cabinet:
                        fresh_cabinet.active = False
                        await session.commit()
            except Exception as e:
                logger.error(f'Ошибка при отключении кабинета {wb_cabinet.shop_id}: {e}', exc_info=True)
                raise e
            # try:
            #     await events.NotValidTokens(wb_cabinet.id,
            #                                 wb_cabinet.shop_id).send_all_users()
            # except Exception as e:
            #     logger.error(f'Ошибка при отправке сообщения о невалидных токенах: {e}', exc_info=True)
            raise exceptions.ApiForbiddenError('Нет свободных токенов',
                                               wb_user_cabinet=self.access.wb_cabinet)
