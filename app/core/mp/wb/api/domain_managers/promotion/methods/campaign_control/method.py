from app.core.mp.wb.api.adapter.promotion_client.campaigns_management.adapter import (
    CampaignsManagementAdapter,
)


async def start_adv(
    campaigns_management_adapter: CampaignsManagementAdapter,
    adv_id: int,
) -> None:
    await campaigns_management_adapter.start_adv(adv_id)


async def pause_adv(
    campaigns_management_adapter: CampaignsManagementAdapter,
    adv_id: int,
) -> None:
    await campaigns_management_adapter.pause_adv(adv_id)


async def stop_adv(
    campaigns_management_adapter: CampaignsManagementAdapter,
    adv_id: int,
) -> None:
    await campaigns_management_adapter.stop_adv(adv_id)
