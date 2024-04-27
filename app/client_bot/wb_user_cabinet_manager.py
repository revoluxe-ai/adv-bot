import asyncio
import logging

import aiohttp

import app
from app.modules.common_slaves.wildberries.api_rights import TokenRightChecker
from app.modules.common_slaves.wildberries.exceptions import (
    ApiForbiddenError,
    UnknownApiRequestError,
)
from app.modules.common_slaves.wildberries.models import WBToken
from app.utils.db.session_maker import get_async_session_maker

logger = logging.getLogger(__name__)

_sm = get_async_session_maker()


class CabinetManager:

    @classmethod
    async def check_access(cls, token: WBToken):
        right_checker = TokenRightChecker(token)
        try:
            await asyncio.gather(
                right_checker.adverts(),
                right_checker.content())

        except ApiForbiddenError:
            raise
        except UnknownApiRequestError as e:
            logger.error(e)
        except aiohttp.client_exceptions.ServerDisconnectedError as e:
            logger.error(e)
        except aiohttp.client_exceptions.ClientOSError as e:
            logger.error(e)








