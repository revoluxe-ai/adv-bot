from collections.abc import Sequence
from typing import Any

import pytest

from app.modules.billing.pricer.pricer import Pricer, TariffMode
from app.modules.billing.pricer.tariffs import tariffs, tariffs_for_auto_setting


class DummyAdv:
    """Минимальный объект с нужными атрибутами вместо SQLAlchemy модели."""

    def __init__(
        self,
        *,
        id: int = 1,
        adv_id: int = 100,
        bot_active: bool = True,
        active_status: str = "started",
        search_adv_id: int | None,
        auto_update_white_list: bool | None = None,
        auto_update_target_place: bool | None = None,
        auto_update_exponent: bool | None = None,
        individual_keywords_target_place_mode: bool | None = None,
    ):
        self.id = id
        self.adv_id = adv_id
        self.bot_active = bot_active
        self.active_status = active_status
        self.search_adv_id = search_adv_id
        self.auto_update_white_list = auto_update_white_list
        self.auto_update_target_place = auto_update_target_place
        self.auto_update_exponent = auto_update_exponent
        self.individual_keywords_target_place_mode = individual_keywords_target_place_mode


def _patch_metering_advs(
    monkeypatch: pytest.MonkeyPatch, advs: Sequence[DummyAdv]
) -> None:
    async def _fake_fetch_bot_active_advs(
        session: Any, shop_id: str
    ) -> Sequence[DummyAdv]:
        return [a for a in advs if a.bot_active]

    async def _fake_fetch_cabinet_advs(
        session: Any, shop_id: str
    ) -> Sequence[DummyAdv]:
        return list(advs)

    monkeypatch.setattr(
        Pricer, "fetch_bot_active_advs", staticmethod(_fake_fetch_bot_active_advs)
    )
    monkeypatch.setattr(
        "app.modules.billing.pricer.pricer.fetch_cabinet_adv_settings_for_metering",
        _fake_fetch_cabinet_advs,
    )


class TestPricerTariffs:
    def test_zero_campaigns_have_zero_price(self):
        pricer = Pricer()
        assert pricer.get_price_for_count_advs_in_cabinet_for_month(0) == 0.0

    def test_old_tariff_table_applies_limit_price(self):
        pricer = Pricer()
        total = pricer.get_price_for_count_advs_in_cabinet_for_month(5)
        assert total == 5 * tariffs[5]

    #TODO: СРОЧНО ВЕРНУТЬ ЭТОТ ТЕСТ
    # @pytest.skip
    # def test_auto_tariff_table_caps_at_max_limit(self):
    #     pricer = Pricer()
    #     total = pricer.get_price_for_count_advs_in_cabinet_for_month(
    #         120, tariff_table=tariffs_for_auto_setting
    #     )
    #     assert total == 120 * tariffs_for_auto_setting[100]

    @pytest.mark.asyncio
    async def test_context_no_bot_active_advs_means_zero_and_old(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        async def _fake_fetch_bot_active_advs(
            session: Any, shop_id: str
        ) -> Sequence[DummyAdv]:
            return []

        async def _fake_fetch_active_search_adv_ids(
            session: Any, search_adv_ids: Sequence[int]
        ) -> set[int]:
            return set()

        monkeypatch.setattr(
            Pricer, "fetch_bot_active_advs", staticmethod(_fake_fetch_bot_active_advs)
        )
        monkeypatch.setattr(
            "app.modules.billing.pricer.pricer.fetch_cabinet_adv_settings_for_metering",
            _fake_fetch_bot_active_advs,
        )

        details = await Pricer().get_tariff_details(session=None, shop_id="s")  # type: ignore[arg-type]
        assert details.mode == TariffMode.OLD
        assert details.count == 0
        assert details.total_per_month == 0.0

    @pytest.mark.asyncio
    async def test_context_counts_all_advs_with_search_adv_id(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        advs = [
            DummyAdv(id=1, adv_id=101, search_adv_id=10, bot_active=True, auto_update_white_list=True),
            DummyAdv(id=2, adv_id=102, search_adv_id=11, bot_active=True, auto_update_white_list=False),
            DummyAdv(id=3, adv_id=103, search_adv_id=None, bot_active=True, auto_update_white_list=True),
            DummyAdv(id=4, adv_id=104, search_adv_id=12, bot_active=True, auto_update_white_list=True),
        ]

        _patch_metering_advs(monkeypatch, advs)
        details = await Pricer().get_tariff_details(session=None, shop_id="s")  # type: ignore[arg-type]
        assert details.count == 2.0

    @pytest.mark.asyncio
    async def test_mode_switches_to_auto_if_any_part_auto_enabled(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        advs = [
            DummyAdv(id=1, adv_id=101, search_adv_id=10, bot_active=True, auto_update_white_list=False, auto_update_target_place=False),
            DummyAdv(id=2, adv_id=102, search_adv_id=11, bot_active=True, auto_update_white_list=True, auto_update_target_place=False),
        ]

        _patch_metering_advs(monkeypatch, advs)
        details = await Pricer().get_tariff_details(session=None, shop_id="s")  # type: ignore[arg-type]
        assert details.mode == TariffMode.AUTO
        assert details.count == 1.0
        assert details.price_per_adv == float(tariffs_for_auto_setting[1])
        assert details.total_per_month == float(tariffs_for_auto_setting[1])

    @pytest.mark.asyncio
    async def test_mode_stays_old_if_no_part_auto_enabled(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        advs = [
            DummyAdv(
                id=1,
                adv_id=101,
                active_status="paused",
                search_adv_id=10,
                bot_active=False,
                auto_update_white_list=False,
                auto_update_target_place=False,
            ),
            DummyAdv(
                id=2,
                adv_id=102,
                active_status="paused",
                search_adv_id=11,
                bot_active=False,
                auto_update_white_list=False,
                auto_update_target_place=False,
            ),
        ]

        _patch_metering_advs(monkeypatch, advs)
        details = await Pricer().get_tariff_details(session=None, shop_id="s")  # type: ignore[arg-type]
        assert details.mode == TariffMode.OLD
        assert details.count == 0.0
        assert details.total_per_month == 0.0

    @pytest.mark.asyncio
    async def test_mode_auto_when_auto_settings_configured_but_search_not_started(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        advs = [
            DummyAdv(
                id=1,
                adv_id=101,
                active_status="paused",
                search_adv_id=10,
                bot_active=True,
                auto_update_white_list=True,
                auto_update_target_place=False,
            ),
        ]

        _patch_metering_advs(monkeypatch, advs)
        details = await Pricer().get_tariff_details(session=None, shop_id="s")  # type: ignore[arg-type]
        assert details.mode == TariffMode.AUTO
        assert details.count == 0.0
        assert details.total_per_month == 0.0

    @pytest.mark.asyncio
    async def test_exponent_does_not_switch_to_auto_mode(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        advs = [
            DummyAdv(
                id=1,
                adv_id=101,
                active_status="paused",
                search_adv_id=10,
                bot_active=False,
                auto_update_white_list=False,
                auto_update_target_place=False,
                auto_update_exponent=True,
            ),
        ]

        _patch_metering_advs(monkeypatch, advs)
        details = await Pricer().get_tariff_details(session=None, shop_id="s")  # type: ignore[arg-type]
        assert details.mode == TariffMode.OLD
        assert details.count == 0.0

