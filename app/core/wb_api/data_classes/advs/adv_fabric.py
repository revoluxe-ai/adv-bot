from typing import Optional
import logging
from .base_adv import Adv
from .auto_adv import AutoAdv
from .auction_adv import AuctionAdv
from pydantic import ValidationError
logger = logging.getLogger(__name__)


def get_adv_data_class(data_from_wb: dict) -> Optional[Adv]:
    data = data_from_wb
    _type = data['type']
    if _type == 8:
        try:
            adv = AutoAdv(**data)
        except ValidationError as exc:
            logger.error(f'{exc}', exc_info=True)
            raise
    elif _type == 9:
        try:
            adv = AuctionAdv(**data)
        except ValidationError as exc:
            logger.error(f'{exc}', exc_info=True)
            raise
    else:
        logger.info(f'Неизвестный типа кампании: тип {_type}')
        adv = None
    return adv
