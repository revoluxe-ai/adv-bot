import logging
import math

from app.modules.bids_for_positions_manager.dto import BidPositionRow
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from ..bids_for_positions_manager.bids_for_positions_manager import (
    BidsForPositionsManager,
)

from ..common_slaves.wildberries.models.enums.strategy import Strategy
from ...shared.domains.wb.dto.wb_adv_dto import WBAdvDTO

from .clickhouse_manager import ClickHouseManager
from .clickhouse_manager.dto import ConvCartToViewsOnPosition
from .clickhouse_manager.dto.bid_position import BidPosition

logger = logging.getLogger(__name__)

# Контракт get_keywords_target_position:
# - В результат попадают только ключи, по которым есть данные по конверсиям (get_conv_cart_to_views).
# - Ключи с нормализованными ставками (rows), но без conv (нет в clusters_adv_deltas_5m), в словарь
#   не включаются — без conv нельзя посчитать MIN_CPO (pay_for_cart) или MAX_CONV.
# - Вызывающий код (KeywordTargetPlaceUpdater._set_new_target_places) при отсутствии ключа в
#   результате оставляет KeywordSetting.target_place = NULL и логирует отсутствие данных.


class PredictKeywordsTargetPlace:
    def __init__(
        self,
        clickhouse_manager: ClickHouseManager,
        bids_for_positions_manager: BidsForPositionsManager,
    ) -> None:
        self._clickhouse_manager = clickhouse_manager
        self._bids_for_positions_manager = bids_for_positions_manager

    async def get_keywords_target_position(
        self, adv: WBAdvDTO, positions_size: int
    ) -> dict[str, int]:
        bids_with_convs: dict[
            str, list[BidPosition]
        ] = await self._load_bids_with_convs(adv, positions_size)
        strategy = adv.strategy
        return self._get_target_positions(bids_with_convs, strategy)

    async def get_keyword_bid_profiles(
        self, adv: WBAdvDTO, positions_size: int
    ) -> dict[str, list[BidPosition]]:
        """Per-keyword bid+conv curves (no strategy collapse). Same contract as mapping step in get_keywords_target_position."""
        return await self._load_bids_with_convs(adv, positions_size)

    async def _load_bids_with_convs(
        self, adv: WBAdvDTO, positions_size: int
    ) -> dict[str, list[BidPosition]]:
        assert positions_size <= 300, "Количество позиций не может быть больше 300"
        nmid = adv.main_nmid
        min_bid = adv.search_adv_min_bids.get(nmid)
        if min_bid is None:
            logger.error(
                "Нет min_bid для nmid=%s в search_adv_min_bids (adv_id=%s); "
                "профили ставок не загружаются",
                nmid,
                adv.adv_id,
            )
            return {}
        convs_carts_to_views: dict[
            str, list[ConvCartToViewsOnPosition]
        ] = await self._clickhouse_manager.get_conv_cart_to_views(
            nmid=nmid, positions_size=positions_size
        )
        rows: dict[
            str, list[BidPositionRow]
        ] = await self._bids_for_positions_manager.get_bid_positions_normalized(
            nmid=nmid, min_bid=min_bid, positions_size=positions_size
        )
        return self._map_rows_to_bid_positions(rows, convs_carts_to_views)

    def _map_rows_to_bid_positions(
        self,
        rows: dict[str, list[BidPositionRow]],
        convs: dict[str, list[ConvCartToViewsOnPosition]],
    ) -> dict[str, list[BidPosition]]:
        """Map BidPositionRow + convs to dict[keyword, list[BidPosition]] with conv filled.
        Ключи без conv (convs.get(key) пусто) намеренно не попадают в result — см. контракт вверху модуля.
        """
        result: dict[str, list[BidPosition]] = {}
        for key, row_list in rows.items():
            positions = [
                BidPosition(
                    keyword=r.keyword,
                    position=r.position,
                    bid=r.bid,
                    timestamp=r.timestamp,
                )
                for r in row_list
            ]
            convs_for_keyword = convs.get(key)
            if not convs_for_keyword:
                continue  # Ключ без данных по конверсиям — не включаем; апдейтер оставит target_place NULL
            result[key] = self._fill_positions_convs(positions, convs_for_keyword)
        return result

    def _get_target_positions(
        self,
        bids_for_positions: dict[str, list[BidPosition]],
        strategy: Strategy,
    ) -> dict[str, int]:
        """Expects already normalized bids with conv_carts_to_views filled."""
        result_target_positions: dict[str, int] = {}
        for keyword, positions in bids_for_positions.items():
            if not positions:
                logger.error(
                    "Пустой список позиций для прогноза целевой позиции, keyword=%s — ключ не попадёт в результат",
                    keyword,
                )
                continue
            if strategy == Strategy.MIN_CPO:
                best_position: BidPosition = min(
                    positions, key=lambda p: p.pay_for_cart
                )
            elif strategy == Strategy.MAX_CONV:
                best_position = max(
                    positions, key=lambda p: p.conv_carts_to_views or 0.0
                )
            else:
                raise NotImplementedError(
                    f"Неизвестная стратегия выбора целевой позиции: {strategy}"
                )
            result_target_positions[keyword] = max(1, best_position.position)
        return result_target_positions

    def get_target_position_for_strategy_mode(
        self,
        positions: list[BidPosition],
        strategy_mode: KeywordStrategyMode,
    ) -> int | None:
        """Per-keyword target position for V3 strategy ladder mode."""
        if not positions:
            logger.error("Пустой список позиций для прогноза целевой позиции")
            return None

        if strategy_mode == KeywordStrategyMode.MIN_CPA:
            best_position: BidPosition = min(positions, key=lambda p: p.pay_for_cart)
            return max(1, best_position.position)

        if strategy_mode == KeywordStrategyMode.MAX_CONVERSION:
            best_position = max(positions, key=lambda p: p.conv_carts_to_views or 0.0)
            return max(1, best_position.position)

        if strategy_mode == KeywordStrategyMode.OPTIMUM:
            best_position = max(positions, key=self._optimum_score)
            return max(1, best_position.position)

        raise NotImplementedError(
            f"Неизвестная стратегия выбора целевой позиции для key-mode: {strategy_mode}"
        )

    @staticmethod
    def _optimum_score(position: BidPosition) -> float:
        conv = float(position.conv_carts_to_views or 0.0)
        pay = position.pay_for_cart
        if not math.isfinite(pay) or pay <= 0:
            return -1.0
        return conv / (1.0 + pay)

    @staticmethod
    def _fill_positions_convs(
        positions: list[BidPosition],
        convs: list[ConvCartToViewsOnPosition],
    ) -> list[BidPosition]:
        """Заполняет conv_carts_to_views у позиций и возвращает только те, для которых есть conv.
        При текущем SQL get_conv_cart_to_views по каждому ключу приходят все позиции 1..positions_size,
        поэтому отсечение по position обычно не срабатывает; при разреженных conv часть позиций отбрасывается.
        """
        assert (
            len(
                set(pos.keyword for pos in positions)
                | set(conv.keyword for conv in convs)
            )
            == 1
        )
        positions_filled: list[BidPosition] = []
        convs_dict = {conv.position: conv for conv in convs}
        for position in positions:
            conv = convs_dict.get(position.position)
            if conv is not None:
                position.conv_carts_to_views = conv.conv_cart_to_views
                positions_filled.append(position)
        return positions_filled
