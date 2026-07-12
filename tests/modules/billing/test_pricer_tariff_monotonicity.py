import pytest

from app.modules.billing.pricer.tariffs import tariffs_for_auto_setting


def _get_price_per_adv(count: int, tariff: dict[int, int]) -> int:
    for limit, price in sorted(tariff.items()):
        if count <= limit:
            return price

    return tariff[max(tariff)]


def _monthly_total(count: int, tariff: dict[int, int]) -> int:
    return count * _get_price_per_adv(count, tariff)



@pytest.mark.xfail
@pytest.mark.unit
def test_auto_setting_tariff_monthly_total_does_not_drop() -> None:
    previous_count = 1
    previous_price = _get_price_per_adv(previous_count, tariffs_for_auto_setting)
    previous_total = _monthly_total(previous_count, tariffs_for_auto_setting)

    for count in range(2, max(tariffs_for_auto_setting) + 1):
        price = _get_price_per_adv(count, tariffs_for_auto_setting)
        total = _monthly_total(count, tariffs_for_auto_setting)

        assert total >= previous_total, (
            f"Monthly total drops on {previous_count}->{count}: "
            f"{previous_count} * {previous_price} = {previous_total}, "
            f"{count} * {price} = {total}"
        )

        previous_count = count
        previous_price = price
        previous_total = total
