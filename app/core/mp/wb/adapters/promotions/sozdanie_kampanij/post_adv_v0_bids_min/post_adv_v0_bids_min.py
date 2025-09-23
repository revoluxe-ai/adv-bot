# app/core/mp/wb/adapters/promotions/sozdanie_kampanij/post_adv_v0_bids_min/post_adv_v0_bids_min.py

from typing import Literal, cast

import httpx

from app.core.mp.wb.exceptions import (
    ApiForbiddenError,
    TooManyRequestsError,
    ArgumentsError,
    ApiUnexpectedError,
    ApiTimeoutError,
)
from app.core.mp.wb.generated.promotion.v1.client.api.sozdanie_kampanij import (
    post_adv_v0_bids_min as use_case,
)
from app.core.mp.wb.generated.promotion.v1.client.client import AuthenticatedClient
from app.core.mp.wb.generated.promotion.v1.client.models import (
    PostAdvV0BidsMinBodyPaymentType,
    PostAdvV0BidsMinBodyPlacementTypesItem,
)

MinBidsInAdv = use_case.PostAdvV0BidsMinResponse200


async def post_adv_v0_bids_min(
        *,
        client: AuthenticatedClient,
        adv_id: int,
        nmids: list[int],
        payment_type: Literal[
            PostAdvV0BidsMinBodyPaymentType.CPM.value,
            PostAdvV0BidsMinBodyPaymentType.CPC.value,
        ],
        placement_types: list[
            Literal[
                PostAdvV0BidsMinBodyPlacementTypesItem.SEARCH,
                PostAdvV0BidsMinBodyPlacementTypesItem.RECOMMENDATION,
            ]
        ],
) -> MinBidsInAdv:
    payment_type = PostAdvV0BidsMinBodyPaymentType(payment_type)
    placement_types = [
        PostAdvV0BidsMinBodyPlacementTypesItem(t) for t in placement_types
    ]

    body = use_case.PostAdvV0BidsMinBody(
        advert_id=adv_id,
        nm_ids=nmids,
        payment_type=payment_type,
        placement_types=placement_types,
    )
    try:
        response = await use_case.asyncio_detailed(client=client, body=body)
    except errors.UnexpectedStatus:
        raise ApiUnexpectedError("Unexpected status from promotion API")

    except httpx.TimeoutException:
        raise ApiTimeoutError("Timeout when calling promotion API")

    if isinstance(response, use_case.PostAdvV0BidsMinResponse401):
        raise ApiForbiddenError("Unauthorized access to promotion API")
    if isinstance(response, use_case.PostAdvV0BidsMinResponse429):
        raise TooManyRequestsError("Too many requests to promotion API")

    if isinstance(response, use_case.StandardizedBatchError):
        err: use_case.StandardizedBatchError = cast(
            response, use_case.StandardizedBatchError
        )
        raise ArgumentsError(
            f"Какой-то из артикулов не из этой рекламной кампании: {err.detail}"
        )

    if isinstance(response, use_case.PostAdvV0BidsMinResponse200):
        resp: use_case.PostAdvV0BidsMinResponse200 = cast(response, MinBidsInAdv)
        return resp

    raise ApiUnexpectedError("Unhandled response type from promotion API")
