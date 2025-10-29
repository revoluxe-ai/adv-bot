from app.modules.common_slaves.wildberries.data_classes.adv import Adv
from typing import cast


class AuctionAdv(Adv):
  # TODO: Нужно перейти на генерируемые модели
  @property
  def cpm(self) -> int | None:
    # TODO: Временное решение: нужно переделать, чтобы ставка для каждого товара была своей
    try:
        cpm = self._data["auction_multibids"][0]["bid"]
    except KeyError:
      cpm = None
    return cast(int | None, cpm)


__all__ = ["AuctionAdv"]
