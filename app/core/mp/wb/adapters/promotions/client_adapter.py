from .sozdanie_kampanij.post_adv_v0_bids_min.post_adv_v0_bids_min import (
    post_adv_v0_bids_min,
)


class PromotionsClientAdapter:

    async def get_min_bids_in_adv(
        self,
        adv_id: int,
        nmids: list[int],
        payment_type: str,
        placement_types: list[str],
    ) -> dict:
        client = self._get_authenticated_client(client_type="promotions")
        response = await post_adv_v0_bids_min(
            client=client,
            adv_id=adv_id,
            nmids=nmids,
            payment_type=payment_type,
            placement_types=placement_types,
        )
        return
