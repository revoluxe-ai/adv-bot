import logging

from app.modules.bids_for_positions_manager.dto import BidPositionRow
from ..bids_for_positions_manager.bids_for_positions_manager import BidsForPositionsManager

from ..common_slaves.wildberries.models.enums.strategy import Strategy
from ...settings import settings
from ...shared.domains.wb.dto.wb_adv_dto import WBAdvDTO

from .clickhouse_manager import ClickHouseManager
from .clickhouse_manager.dto import ConvCartToViewsOnPosition
from .clickhouse_manager.dto.bid_position import BidPosition

logger = logging.getLogger(__name__)


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
        assert positions_size <= 300, "Количество позиций не может быть больше 300"
        nmid = adv.main_nmid
        try:
            min_bid = adv.search_adv_min_bids[nmid]
        except KeyError:
            raise
        convs_carts_to_views: dict[str, list[ConvCartToViewsOnPosition]] = (
            await self._clickhouse_manager.get_conv_cart_to_views(
                nmid=nmid, positions_size=positions_size
            )
        )
        rows: dict[str, list[BidPositionRow]] = (
            await self._bids_for_positions_manager.get_bid_positions_normalized(
                nmid=nmid, min_bid=min_bid, positions_size=positions_size
            )
        )
        bids_with_convs = self._map_rows_to_bid_positions(rows, convs_carts_to_views)
        strategy = adv.strategy
        return self._get_target_positions(bids_with_convs, strategy)

    def _map_rows_to_bid_positions(
        self,
        rows: dict[str, list[BidPositionRow]],
        convs: dict[str, list[ConvCartToViewsOnPosition]],
    ) -> dict[str, list[BidPosition]]:
        """Map BidPositionRow + convs to dict[keyword, list[BidPosition]] with conv filled."""
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
                continue
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
                logger.error("Пустой список позиций для прогноза целевой позиции")
                result_target_positions[keyword] = (
                    settings.GLOBAL_DEFAULT_KEYWORD_TARGET_PLACE
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

    @staticmethod
    def _fill_positions_convs(
        positions: list[BidPosition],
        convs: list[ConvCartToViewsOnPosition],
    ) -> list[BidPosition]:
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
