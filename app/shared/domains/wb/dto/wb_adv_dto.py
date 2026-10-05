from attr import define, field
import typing

from app.core.mp.wb.dto import AdvMinNmidsBids
from app.modules.common_slaves.wildberries.models.enums.strategy import Strategy
from app.modules.common_slaves.wildberries.models.enums.target_position_mode import TargetPositionMode
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import PlanData, FactData

from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword


if typing.TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv



@define
class WBAdvDTO:
    _complex_adv: "ComplexAdv" = field(alias='complex_adv')
    _plan: PlanData = field(alias='plan')
    _fact: FactData = field(alias='fact')
    keywords: list[CalculatedKeyword]
    _min_bids: AdvMinNmidsBids = field(alias='min_bids')
    _current_common_bids_in_search_adv: dict[int, int] | None = field(
        alias='current_common_bids_in_search_adv', default=None
    )  # артикул -> ставка

    @property
    def plan(self)-> PlanData:
        return self._plan

    @property
    def fact(self) -> FactData:
        """Факт кампании, собранный при построении DTO (plan/fact из ``get_wb_advs_dto``)."""
        return self._fact

    @property
    def target_position_mode(self) -> TargetPositionMode:
        return self._complex_adv.target_position_mode

    @property
    def strategy(self) -> Strategy:
        return self._complex_adv.strategy

    @property
    def min_target_position(self) -> int:
        return self._complex_adv.min_target_position

    @property
    def adv_id(self) -> int:
        return self._complex_adv.adv_id

    @property
    def adv_setting_original_id(self) -> int:
        return self._complex_adv.adv_setting_original_id


    @property
    def main_nmid(self) -> int:
        return self._complex_adv.main_nmid


    @property
    def updater_common_bid_in_search_adv_active_status(self) -> bool:
        return self._complex_adv.updater_common_bid_in_search_adv_active_status


    @property
    def bidder_active(self) -> bool:
        return self._complex_adv.bidder_active

    @property
    def bot_active(self) -> bool:
        return self._complex_adv.bot_active


    @property
    def nmids(self) -> list[int]:
        return self._complex_adv.nmids


    @property
    def complex_adv(self) -> "ComplexAdv":
        return self._complex_adv

    @property
    def max_user_cpm_bid(self) -> int:
        return self._complex_adv.max_user_cpm

    @property
    def search_adv_min_bids(self) -> dict[int, int]: # nmid to bid
        return self._min_bids.search

    @property
    def result_target_pay_for_order(self) -> int:
        fact_orders = self._fact.predict_orders
        plan_orders = self._plan.orders
        if fact_orders >= plan_orders:
            return self._plan.target_pay_for_order
        else:
            return self._plan.max_pay_for_order


    @property
    def fact_pay_for_order(self) -> float | None:
        """Aggregate plan/fact CPO; leg-level consumers используют explicit поля."""
        return self._fact.pay_for_order

    @property
    def auto_fact_cpo(self) -> float | None:
        """Spec leg-cpo-economics: CPO structural Auto leg без fallback."""
        return self._complex_adv.auto_fact_cpo

    @property
    def search_fact_cpo(self) -> float | None:
        """Spec leg-cpo-economics: CPO structural Search leg без fallback."""
        return self._complex_adv.search_fact_cpo


    @property
    def current_common_bids_in_search_adv(self) -> dict[int, int] | None:
        return self._current_common_bids_in_search_adv


    @property
    def bid_step(self) -> int:
        return self._complex_adv.bid_cpm_step



