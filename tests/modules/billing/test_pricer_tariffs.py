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
        search_adv_id: int | None,
        automatic_version: int | None,
        auto_update_white_list: bool | None = None,
        auto_update_target_place: bool | None = None,
        auto_update_exponent: bool | None = None,
    ):
        self.search_adv_id = search_adv_id
        self.automatic_version = automatic_version
        self.auto_update_white_list = auto_update_white_list
        self.auto_update_target_place = auto_update_target_place
        self.auto_update_exponent = auto_update_exponent


class TestPricerTariffs:
    def test_zero_campaigns_have_zero_price(self):
        pricer = Pricer()
        assert pricer.get_price_for_count_advs_in_cabinet_for_month(0) == 0.0

    def test_old_tariff_table_applies_limit_price(self):
        pricer = Pricer()
        total = pricer.get_price_for_count_advs_in_cabinet_for_month(5)
        assert total == 5 * tariffs[5]

    def test_auto_tariff_table_caps_at_max_limit(self):
        pricer = Pricer()
        total = pricer.get_price_for_count_advs_in_cabinet_for_month(
            120, tariff_table=tariffs_for_auto_setting
        )
        assert total == 120 * tariffs_for_auto_setting[100]

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
        # search ids getter может быть переименован в публичный — поддержим оба варианта
        if hasattr(Pricer, "fetch_active_search_adv_ids"):
            monkeypatch.setattr(
                Pricer,
                "fetch_active_search_adv_ids",
                staticmethod(_fake_fetch_active_search_adv_ids),
            )
        else:
            monkeypatch.setattr(
                Pricer,
                "_fetch_active_search_adv_ids",
                staticmethod(_fake_fetch_active_search_adv_ids),
            )

        details = await Pricer().get_tariff_details(session=None, shop_id="s")  # type: ignore[arg-type]
        assert details.mode == TariffMode.OLD
        assert details.count == 0
        assert details.total_per_month == 0.0

    @pytest.mark.asyncio
    async def test_context_counts_only_advs_with_started_search(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        advs = [
            DummyAdv(search_adv_id=10, automatic_version=1, auto_update_white_list=True),
            DummyAdv(search_adv_id=11, automatic_version=1, auto_update_white_list=False),
            DummyAdv(search_adv_id=None, automatic_version=1, auto_update_white_list=True),
            DummyAdv(search_adv_id=12, automatic_version=1, auto_update_white_list=True),
        ]

        async def _fake_fetch_bot_active_advs(
            session: Any, shop_id: str
        ) -> Sequence[DummyAdv]:
            return advs

        async def _fake_fetch_active_search_adv_ids(
            session: Any, search_adv_ids: Sequence[int]
        ) -> set[int]:
            # started только для 10 и 12
            return {10, 12}

        monkeypatch.setattr(
            Pricer, "fetch_bot_active_advs", staticmethod(_fake_fetch_bot_active_advs)
        )
        if hasattr(Pricer, "fetch_active_search_adv_ids"):
            monkeypatch.setattr(
                Pricer,
                "fetch_active_search_adv_ids",
                staticmethod(_fake_fetch_active_search_adv_ids),
            )
        else:
            monkeypatch.setattr(
                Pricer,
                "_fetch_active_search_adv_ids",
                staticmethod(_fake_fetch_active_search_adv_ids),
            )

        details = await Pricer().get_tariff_details(session=None, shop_id="s")  # type: ignore[arg-type]
        assert details.count == 2

    @pytest.mark.asyncio
    async def test_mode_switches_to_auto_if_any_part_auto_enabled(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        advs = [
            DummyAdv(search_adv_id=10, automatic_version=1, auto_update_white_list=False, auto_update_target_place=False),
            DummyAdv(search_adv_id=11, automatic_version=2, auto_update_white_list=True, auto_update_target_place=False),
        ]

        async def _fake_fetch_bot_active_advs(
            session: Any, shop_id: str
        ) -> Sequence[DummyAdv]:
            return advs

        async def _fake_fetch_active_search_adv_ids(
            session: Any, search_adv_ids: Sequence[int]
        ) -> set[int]:
            return {10, 11}

        monkeypatch.setattr(
            Pricer, "fetch_bot_active_advs", staticmethod(_fake_fetch_bot_active_advs)
        )
        if hasattr(Pricer, "fetch_active_search_adv_ids"):
            monkeypatch.setattr(
                Pricer,
                "fetch_active_search_adv_ids",
                staticmethod(_fake_fetch_active_search_adv_ids),
            )
        else:
            monkeypatch.setattr(
                Pricer,
                "_fetch_active_search_adv_ids",
                staticmethod(_fake_fetch_active_search_adv_ids),
            )

        details = await Pricer().get_tariff_details(session=None, shop_id="s")  # type: ignore[arg-type]
        assert details.mode == TariffMode.AUTO
        # count=2 => берём цену по лимиту 3 (5000)
        assert details.price_per_adv == float(tariffs_for_auto_setting[3])
        assert details.total_per_month == 2 * tariffs_for_auto_setting[3]

    @pytest.mark.asyncio
    async def test_mode_stays_old_if_no_part_auto_enabled(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        advs = [
            DummyAdv(search_adv_id=10, automatic_version=1, auto_update_white_list=False, auto_update_target_place=False),
            DummyAdv(search_adv_id=11, automatic_version=2, auto_update_white_list=False, auto_update_target_place=False),
        ]

        async def _fake_fetch_bot_active_advs(
            session: Any, shop_id: str
        ) -> Sequence[DummyAdv]:
            return advs

        async def _fake_fetch_active_search_adv_ids(
            session: Any, search_adv_ids: Sequence[int]
        ) -> set[int]:
            return {10, 11}

        monkeypatch.setattr(
            Pricer, "fetch_bot_active_advs", staticmethod(_fake_fetch_bot_active_advs)
        )
        if hasattr(Pricer, "fetch_active_search_adv_ids"):
            monkeypatch.setattr(
                Pricer,
                "fetch_active_search_adv_ids",
                staticmethod(_fake_fetch_active_search_adv_ids),
            )
        else:
            monkeypatch.setattr(
                Pricer,
                "_fetch_active_search_adv_ids",
                staticmethod(_fake_fetch_active_search_adv_ids),
            )

        details = await Pricer().get_tariff_details(session=None, shop_id="s")  # type: ignore[arg-type]
        assert details.mode == TariffMode.OLD
        assert details.total_per_month == 2 * tariffs[2]

    @pytest.mark.asyncio
    async def test_mode_auto_when_auto_settings_configured_but_no_active_search(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        advs = [
            DummyAdv(
                search_adv_id=10,
                automatic_version=1,
                auto_update_white_list=True,
                auto_update_target_place=False,
            ),
        ]

        async def _fake_fetch_bot_active_advs(
            session: Any, shop_id: str
        ) -> Sequence[DummyAdv]:
            return advs

        async def _fake_fetch_active_search_adv_ids(
            session: Any, search_adv_ids: Sequence[int]
        ) -> set[int]:
            return set()

        monkeypatch.setattr(
            Pricer, "fetch_bot_active_advs", staticmethod(_fake_fetch_bot_active_advs)
        )
        if hasattr(Pricer, "fetch_active_search_adv_ids"):
            monkeypatch.setattr(
                Pricer,
                "fetch_active_search_adv_ids",
                staticmethod(_fake_fetch_active_search_adv_ids),
            )
        else:
            monkeypatch.setattr(
                Pricer,
                "_fetch_active_search_adv_ids",
                staticmethod(_fake_fetch_active_search_adv_ids),
            )

        details = await Pricer().get_tariff_details(session=None, shop_id="s")  # type: ignore[arg-type]
        assert details.mode == TariffMode.AUTO
        assert details.count == 0
        assert details.total_per_month == 0.0

    @pytest.mark.asyncio
    async def test_exponent_does_not_switch_to_auto_mode(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        advs = [
            DummyAdv(
                search_adv_id=10,
                automatic_version=2,
                auto_update_white_list=False,
                auto_update_target_place=False,
                auto_update_exponent=True,
            ),
        ]

        async def _fake_fetch_bot_active_advs(
            session: Any, shop_id: str
        ) -> Sequence[DummyAdv]:
            return advs

        async def _fake_fetch_active_search_adv_ids(
            session: Any, search_adv_ids: Sequence[int]
        ) -> set[int]:
            return {10}

        monkeypatch.setattr(
            Pricer, "fetch_bot_active_advs", staticmethod(_fake_fetch_bot_active_advs)
        )
        if hasattr(Pricer, "fetch_active_search_adv_ids"):
            monkeypatch.setattr(
                Pricer,
                "fetch_active_search_adv_ids",
                staticmethod(_fake_fetch_active_search_adv_ids),
            )
        else:
            monkeypatch.setattr(
                Pricer,
                "_fetch_active_search_adv_ids",
                staticmethod(_fake_fetch_active_search_adv_ids),
            )

        details = await Pricer().get_tariff_details(session=None, shop_id="s")  # type: ignore[arg-type]
        assert details.mode == TariffMode.OLD

