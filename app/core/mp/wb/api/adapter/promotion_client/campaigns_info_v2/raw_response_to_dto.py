from __future__ import annotations

from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models import (
    GetAdvertsAdvertsItem,
)
from app.core.mp.wb.dto.adv_info import (
    AdvInfoNmSetting,
    AdvInfoPlacement,
    AdvInfoSettings,
    AdvInfoSimple,
    AdvInfoTimestamps,
)


def convert(item: GetAdvertsAdvertsItem) -> AdvInfoSimple:
    settings = AdvInfoSettings(
        name=item.settings.name,
        payment_type=item.settings.payment_type.value,
        placements=AdvInfoPlacement(
            search=item.settings.placements.search,
            recommendations=item.settings.placements.recommendations,
        ),
    )

    nmids_settings = [
        AdvInfoNmSetting(
            nmid=nm_setting.nm_id,
            subject_id=nm_setting.subject.id,
            subject_name=nm_setting.subject.name,
            search_bid_kopecks=nm_setting.bids_kopecks.search,
            recommendations_bid_kopecks=nm_setting.bids_kopecks.recommendations,
        )
        for nm_setting in item.nm_settings
    ]

    timestamps = AdvInfoTimestamps(
        created=item.timestamps.created,
        updated=item.timestamps.updated,
        started=item.timestamps.started,
        deleted=item.timestamps.deleted,
    )

    return AdvInfoSimple(
        adv_id=item.id,
        bid_type=item.bid_type,
        status=item.status.value,
        settings=settings,
        nmids_settings=nmids_settings,
        timestamps=timestamps,
    )
