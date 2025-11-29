from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_api_v1_calendar_promotions_nomenclatures_response_200 import (
    GetApiV1CalendarPromotionsNomenclaturesResponse200,
)
from ...models.get_api_v1_calendar_promotions_nomenclatures_response_400 import (
    GetApiV1CalendarPromotionsNomenclaturesResponse400,
)
from ...models.get_api_v1_calendar_promotions_nomenclatures_response_401 import (
    GetApiV1CalendarPromotionsNomenclaturesResponse401,
)
from ...models.get_api_v1_calendar_promotions_nomenclatures_response_422 import (
    GetApiV1CalendarPromotionsNomenclaturesResponse422,
)
from ...models.get_api_v1_calendar_promotions_nomenclatures_response_429 import (
    GetApiV1CalendarPromotionsNomenclaturesResponse429,
)
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    promotion_id: int,
    in_action: bool = False,
    limit: int | Unset = UNSET,
    offset: int | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["promotionID"] = promotion_id

    params["inAction"] = in_action

    params["limit"] = limit

    params["offset"] = offset

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/calendar/promotions/nomenclatures",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    GetApiV1CalendarPromotionsNomenclaturesResponse200
    | GetApiV1CalendarPromotionsNomenclaturesResponse400
    | GetApiV1CalendarPromotionsNomenclaturesResponse401
    | GetApiV1CalendarPromotionsNomenclaturesResponse422
    | GetApiV1CalendarPromotionsNomenclaturesResponse429
    | None
):
    if response.status_code == 200:
        response_200 = GetApiV1CalendarPromotionsNomenclaturesResponse200.from_dict(
            response.json()
        )

        return response_200

    if response.status_code == 400:
        response_400 = GetApiV1CalendarPromotionsNomenclaturesResponse400.from_dict(
            response.json()
        )

        return response_400

    if response.status_code == 401:
        response_401 = GetApiV1CalendarPromotionsNomenclaturesResponse401.from_dict(
            response.json()
        )

        return response_401

    if response.status_code == 422:
        response_422 = GetApiV1CalendarPromotionsNomenclaturesResponse422.from_dict(
            response.json()
        )

        return response_422

    if response.status_code == 429:
        response_429 = GetApiV1CalendarPromotionsNomenclaturesResponse429.from_dict(
            response.json()
        )

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    GetApiV1CalendarPromotionsNomenclaturesResponse200
    | GetApiV1CalendarPromotionsNomenclaturesResponse400
    | GetApiV1CalendarPromotionsNomenclaturesResponse401
    | GetApiV1CalendarPromotionsNomenclaturesResponse422
    | GetApiV1CalendarPromotionsNomenclaturesResponse429
]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    promotion_id: int,
    in_action: bool = False,
    limit: int | Unset = UNSET,
    offset: int | Unset = UNSET,
) -> Response[
    GetApiV1CalendarPromotionsNomenclaturesResponse200
    | GetApiV1CalendarPromotionsNomenclaturesResponse400
    | GetApiV1CalendarPromotionsNomenclaturesResponse401
    | GetApiV1CalendarPromotionsNomenclaturesResponse422
    | GetApiV1CalendarPromotionsNomenclaturesResponse429
]:
    r"""List of Products for Participating in the Promotion

     Returns a list of products suitable for participation in the promotion.

    Not applicable for auto promotions

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account for all methods in the <strong>Promotions Calendar</strong> category:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 6 seconds | 10 requests | 600 milliseconds | 5 requests |

    </div>

    Args:
        promotion_id (int):  Example: 1.
        in_action (bool):  Default: False. Example: True.
        limit (int | Unset):  Example: 10.
        offset (int | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetApiV1CalendarPromotionsNomenclaturesResponse200 | GetApiV1CalendarPromotionsNomenclaturesResponse400 | GetApiV1CalendarPromotionsNomenclaturesResponse401 | GetApiV1CalendarPromotionsNomenclaturesResponse422 | GetApiV1CalendarPromotionsNomenclaturesResponse429]
    """

    kwargs = _get_kwargs(
        promotion_id=promotion_id,
        in_action=in_action,
        limit=limit,
        offset=offset,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    promotion_id: int,
    in_action: bool = False,
    limit: int | Unset = UNSET,
    offset: int | Unset = UNSET,
) -> (
    GetApiV1CalendarPromotionsNomenclaturesResponse200
    | GetApiV1CalendarPromotionsNomenclaturesResponse400
    | GetApiV1CalendarPromotionsNomenclaturesResponse401
    | GetApiV1CalendarPromotionsNomenclaturesResponse422
    | GetApiV1CalendarPromotionsNomenclaturesResponse429
    | None
):
    r"""List of Products for Participating in the Promotion

     Returns a list of products suitable for participation in the promotion.

    Not applicable for auto promotions

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account for all methods in the <strong>Promotions Calendar</strong> category:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 6 seconds | 10 requests | 600 milliseconds | 5 requests |

    </div>

    Args:
        promotion_id (int):  Example: 1.
        in_action (bool):  Default: False. Example: True.
        limit (int | Unset):  Example: 10.
        offset (int | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetApiV1CalendarPromotionsNomenclaturesResponse200 | GetApiV1CalendarPromotionsNomenclaturesResponse400 | GetApiV1CalendarPromotionsNomenclaturesResponse401 | GetApiV1CalendarPromotionsNomenclaturesResponse422 | GetApiV1CalendarPromotionsNomenclaturesResponse429
    """

    return sync_detailed(
        client=client,
        promotion_id=promotion_id,
        in_action=in_action,
        limit=limit,
        offset=offset,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    promotion_id: int,
    in_action: bool = False,
    limit: int | Unset = UNSET,
    offset: int | Unset = UNSET,
) -> Response[
    GetApiV1CalendarPromotionsNomenclaturesResponse200
    | GetApiV1CalendarPromotionsNomenclaturesResponse400
    | GetApiV1CalendarPromotionsNomenclaturesResponse401
    | GetApiV1CalendarPromotionsNomenclaturesResponse422
    | GetApiV1CalendarPromotionsNomenclaturesResponse429
]:
    r"""List of Products for Participating in the Promotion

     Returns a list of products suitable for participation in the promotion.

    Not applicable for auto promotions

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account for all methods in the <strong>Promotions Calendar</strong> category:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 6 seconds | 10 requests | 600 milliseconds | 5 requests |

    </div>

    Args:
        promotion_id (int):  Example: 1.
        in_action (bool):  Default: False. Example: True.
        limit (int | Unset):  Example: 10.
        offset (int | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetApiV1CalendarPromotionsNomenclaturesResponse200 | GetApiV1CalendarPromotionsNomenclaturesResponse400 | GetApiV1CalendarPromotionsNomenclaturesResponse401 | GetApiV1CalendarPromotionsNomenclaturesResponse422 | GetApiV1CalendarPromotionsNomenclaturesResponse429]
    """

    kwargs = _get_kwargs(
        promotion_id=promotion_id,
        in_action=in_action,
        limit=limit,
        offset=offset,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    promotion_id: int,
    in_action: bool = False,
    limit: int | Unset = UNSET,
    offset: int | Unset = UNSET,
) -> (
    GetApiV1CalendarPromotionsNomenclaturesResponse200
    | GetApiV1CalendarPromotionsNomenclaturesResponse400
    | GetApiV1CalendarPromotionsNomenclaturesResponse401
    | GetApiV1CalendarPromotionsNomenclaturesResponse422
    | GetApiV1CalendarPromotionsNomenclaturesResponse429
    | None
):
    r"""List of Products for Participating in the Promotion

     Returns a list of products suitable for participation in the promotion.

    Not applicable for auto promotions

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account for all methods in the <strong>Promotions Calendar</strong> category:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 6 seconds | 10 requests | 600 milliseconds | 5 requests |

    </div>

    Args:
        promotion_id (int):  Example: 1.
        in_action (bool):  Default: False. Example: True.
        limit (int | Unset):  Example: 10.
        offset (int | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetApiV1CalendarPromotionsNomenclaturesResponse200 | GetApiV1CalendarPromotionsNomenclaturesResponse400 | GetApiV1CalendarPromotionsNomenclaturesResponse401 | GetApiV1CalendarPromotionsNomenclaturesResponse422 | GetApiV1CalendarPromotionsNomenclaturesResponse429
    """

    return (
        await asyncio_detailed(
            client=client,
            promotion_id=promotion_id,
            in_action=in_action,
            limit=limit,
            offset=offset,
        )
    ).parsed
