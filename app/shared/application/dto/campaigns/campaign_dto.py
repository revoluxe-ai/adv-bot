from dataclasses import dataclass


@dataclass
class CampaignDTO:
    """DTO для рекламной кампании."""

    advert_id: int
    name: str
    status: int
    type: int
    create_time: str
    change_time: str
    start_time: str | None = None
    end_time: str | None = None
    daily_budget: int | None = None
    nmids: list[int] | None = None
    payment_type: str | None = None

    # Расширенные поля для авто-кампаний (type=8)
    auto_active: dict[str, bool] | None = None
    auto_subject_id: int | None = None
    auto_subject_name: str | None = None
    auto_sets: list[dict[str, int | str]] | None = None
    # Карта ставок по карточкам: {nmid: cpm}
    bids: dict[int, int] | None = None


@dataclass
class CampaignsListDTO:
    """DTO для списка кампаний."""

    shop_id: int
    campaigns: list[CampaignDTO]
