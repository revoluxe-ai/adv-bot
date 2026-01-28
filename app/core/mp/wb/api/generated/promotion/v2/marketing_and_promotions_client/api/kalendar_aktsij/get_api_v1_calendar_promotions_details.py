from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_api_v1_calendar_promotions_details_response_200 import (
    GetApiV1CalendarPromotionsDetailsResponse200,
)
from ...models.get_api_v1_calendar_promotions_details_response_400 import (
    GetApiV1CalendarPromotionsDetailsResponse400,
)
from ...models.get_api_v1_calendar_promotions_details_response_401 import (
    GetApiV1CalendarPromotionsDetailsResponse401,
)
from ...models.get_api_v1_calendar_promotions_details_response_429 import (
    GetApiV1CalendarPromotionsDetailsResponse429,
)
from ...types import UNSET, Response


def _get_kwargs(
    *,
    promotion_i_ds: str,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["promotionIDs"] = promotion_i_ds

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/calendar/promotions/details",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    GetApiV1CalendarPromotionsDetailsResponse200
    | GetApiV1CalendarPromotionsDetailsResponse400
    | GetApiV1CalendarPromotionsDetailsResponse401
    | GetApiV1CalendarPromotionsDetailsResponse429
    | None
):
    if response.status_code == 200:
        response_200 = GetApiV1CalendarPromotionsDetailsResponse200.from_dict(
            response.json()
        )

        return response_200

    if response.status_code == 400:
        response_400 = GetApiV1CalendarPromotionsDetailsResponse400.from_dict(
            response.json()
        )

        return response_400

    if response.status_code == 401:
        response_401 = GetApiV1CalendarPromotionsDetailsResponse401.from_dict(
            response.json()
        )

        return response_401

    if response.status_code == 429:
        response_429 = GetApiV1CalendarPromotionsDetailsResponse429.from_dict(
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
    GetApiV1CalendarPromotionsDetailsResponse200
    | GetApiV1CalendarPromotionsDetailsResponse400
    | GetApiV1CalendarPromotionsDetailsResponse401
    | GetApiV1CalendarPromotionsDetailsResponse429
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
    promotion_i_ds: str,
) -> Response[
    GetApiV1CalendarPromotionsDetailsResponse200
    | GetApiV1CalendarPromotionsDetailsResponse400
    | GetApiV1CalendarPromotionsDetailsResponse401
    | GetApiV1CalendarPromotionsDetailsResponse429
]:
    r"""Detal'naja informatsija ob aktsijah

     Metod vozvraschaet podrobnuju informatsiju ob [aktsii](/openapi/promotion#tag/Kalendar-
    akcij/paths/~1api~1v1~1calendar~1promotions~1details/get) po ID.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov kategorii <strong>Kalendar' aktsij</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 6 sekund | 10 zaprosov | 600 millisekund | 5 zaprosov |

    </div>

    Args:
        promotion_i_ds (str):  Example: [1, 3, 64].

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetApiV1CalendarPromotionsDetailsResponse200 | GetApiV1CalendarPromotionsDetailsResponse400 | GetApiV1CalendarPromotionsDetailsResponse401 | GetApiV1CalendarPromotionsDetailsResponse429]
    """

    kwargs = _get_kwargs(
        promotion_i_ds=promotion_i_ds,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    promotion_i_ds: str,
) -> (
    GetApiV1CalendarPromotionsDetailsResponse200
    | GetApiV1CalendarPromotionsDetailsResponse400
    | GetApiV1CalendarPromotionsDetailsResponse401
    | GetApiV1CalendarPromotionsDetailsResponse429
    | None
):
    r"""Detal'naja informatsija ob aktsijah

     Metod vozvraschaet podrobnuju informatsiju ob [aktsii](/openapi/promotion#tag/Kalendar-
    akcij/paths/~1api~1v1~1calendar~1promotions~1details/get) po ID.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov kategorii <strong>Kalendar' aktsij</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 6 sekund | 10 zaprosov | 600 millisekund | 5 zaprosov |

    </div>

    Args:
        promotion_i_ds (str):  Example: [1, 3, 64].

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetApiV1CalendarPromotionsDetailsResponse200 | GetApiV1CalendarPromotionsDetailsResponse400 | GetApiV1CalendarPromotionsDetailsResponse401 | GetApiV1CalendarPromotionsDetailsResponse429
    """

    return sync_detailed(
        client=client,
        promotion_i_ds=promotion_i_ds,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    promotion_i_ds: str,
) -> Response[
    GetApiV1CalendarPromotionsDetailsResponse200
    | GetApiV1CalendarPromotionsDetailsResponse400
    | GetApiV1CalendarPromotionsDetailsResponse401
    | GetApiV1CalendarPromotionsDetailsResponse429
]:
    r"""Detal'naja informatsija ob aktsijah

     Metod vozvraschaet podrobnuju informatsiju ob [aktsii](/openapi/promotion#tag/Kalendar-
    akcij/paths/~1api~1v1~1calendar~1promotions~1details/get) po ID.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov kategorii <strong>Kalendar' aktsij</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 6 sekund | 10 zaprosov | 600 millisekund | 5 zaprosov |

    </div>

    Args:
        promotion_i_ds (str):  Example: [1, 3, 64].

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetApiV1CalendarPromotionsDetailsResponse200 | GetApiV1CalendarPromotionsDetailsResponse400 | GetApiV1CalendarPromotionsDetailsResponse401 | GetApiV1CalendarPromotionsDetailsResponse429]
    """

    kwargs = _get_kwargs(
        promotion_i_ds=promotion_i_ds,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    promotion_i_ds: str,
) -> (
    GetApiV1CalendarPromotionsDetailsResponse200
    | GetApiV1CalendarPromotionsDetailsResponse400
    | GetApiV1CalendarPromotionsDetailsResponse401
    | GetApiV1CalendarPromotionsDetailsResponse429
    | None
):
    r"""Detal'naja informatsija ob aktsijah

     Metod vozvraschaet podrobnuju informatsiju ob [aktsii](/openapi/promotion#tag/Kalendar-
    akcij/paths/~1api~1v1~1calendar~1promotions~1details/get) po ID.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov kategorii <strong>Kalendar' aktsij</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 6 sekund | 10 zaprosov | 600 millisekund | 5 zaprosov |

    </div>

    Args:
        promotion_i_ds (str):  Example: [1, 3, 64].

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetApiV1CalendarPromotionsDetailsResponse200 | GetApiV1CalendarPromotionsDetailsResponse400 | GetApiV1CalendarPromotionsDetailsResponse401 | GetApiV1CalendarPromotionsDetailsResponse429
    """

    return (
        await asyncio_detailed(
            client=client,
            promotion_i_ds=promotion_i_ds,
        )
    ).parsed
