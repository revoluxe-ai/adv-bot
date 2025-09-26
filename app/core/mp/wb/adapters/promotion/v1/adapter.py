from .methods.sozdanie_kampanij.post_adv_v0_bids_min import PostAdvV0BidsMinResponse200
from ...base_adapter import WBBaseAdapters
from ....decorators.auth import auth_for_adapter

class PromotionAdapterV1(WBBaseAdapters):
    section = "promotion"
    version = 1


    def __init__(self, ...):
        self.rate_limit_manager = RateLimitManager(
            requests_per_interval=20,)
            interval_seconds=1,
            max_delay=60,
            max_attempts=5,
        )


    @auth_for_adapter(section = 'promotion', version = 1)
    async def get_min_bids(self,
                           client: UserAuthClient,
                           get_min_bids_command: GetMinBidsCommand) -> dict[int, int]:
        from .methods.sozdanie_kampanij import post_adv_v0_bids_min
        response: PostAdvV0BidsMinResponse200 = await post_adv_v0_bids_min(client,
                                                                           adv_id=get_min_bids_command.adv_id,
                                                                           nmids=get_min_bids_command.nmids,
                                                                           payment_type=get_min_bids_command.payment_type,
                                                                           placement_types=get_min_bids_command.placement_types,
                                                                           )
        return response