import datetime
from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_api_v1_calendar_promotions_response_200 import (
    GetApiV1CalendarPromotionsResponse200,
)
from ...models.get_api_v1_calendar_promotions_response_400 import (
    GetApiV1CalendarPromotionsResponse400,
)
from ...models.get_api_v1_calendar_promotions_response_401 import (
    GetApiV1CalendarPromotionsResponse401,
)
from ...models.get_api_v1_calendar_promotions_response_429 import (
    GetApiV1CalendarPromotionsResponse429,
)
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    start_date_time: datetime.datetime,
    end_date_time: datetime.datetime,
    all_promo: bool = False,
    limit: int | Unset = UNSET,
    offset: int | Unset = UNSET,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    json_start_date_time = start_date_time.isoformat()
    params["startDateTime"] = json_start_date_time

    json_end_date_time = end_date_time.isoformat()
    params["endDateTime"] = json_end_date_time

    params["allPromo"] = all_promo

    params["limit"] = limit

    params["offset"] = offset

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/calendar/promotions",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    GetApiV1CalendarPromotionsResponse200
    | GetApiV1CalendarPromotionsResponse400
    | GetApiV1CalendarPromotionsResponse401
    | GetApiV1CalendarPromotionsResponse429
    | None
):
    if response.status_code == 200:
        response_200 = GetApiV1CalendarPromotionsResponse200.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = GetApiV1CalendarPromotionsResponse400.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = GetApiV1CalendarPromotionsResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 429:
        response_429 = GetApiV1CalendarPromotionsResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    GetApiV1CalendarPromotionsResponse200
    | GetApiV1CalendarPromotionsResponse400
    | GetApiV1CalendarPromotionsResponse401
    | GetApiV1CalendarPromotionsResponse429
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
    start_date_time: datetime.datetime,
    end_date_time: datetime.datetime,
    all_promo: bool = False,
    limit: int | Unset = UNSET,
    offset: int | Unset = UNSET,
) -> Response[
    GetApiV1CalendarPromotionsResponse200
    | GetApiV1CalendarPromotionsResponse400
    | GetApiV1CalendarPromotionsResponse401
    | GetApiV1CalendarPromotionsResponse429
]:
    r"""Spisok aktsij

     Metod vozvraschaet spisok [aktsij](/openapi/promotion#tag/Kalendar-
    akcij/paths/~1api~1v1~1calendar~1promotions~1details/get) v WB s datami i vremenem provedenija.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov kategorii <strong>Kalendar' aktsij</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 6 sekund | 10 zaprosov | 600 millisekund | 5 zaprosov |

    </div>

    Args:
        start_date_time (datetime.datetime):  Example: 2023-09-01T00:00:00Z.
        end_date_time (datetime.datetime):  Example: 2024-08-01T23:59:59Z.
        all_promo (bool):  Default: False.
        limit (int | Unset):  Example: 10.
        offset (int | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetApiV1CalendarPromotionsResponse200 | GetApiV1CalendarPromotionsResponse400 | GetApiV1CalendarPromotionsResponse401 | GetApiV1CalendarPromotionsResponse429]
    """

    kwargs = _get_kwargs(
        start_date_time=start_date_time,
        end_date_time=end_date_time,
        all_promo=all_promo,
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
    start_date_time: datetime.datetime,
    end_date_time: datetime.datetime,
    all_promo: bool = False,
    limit: int | Unset = UNSET,
    offset: int | Unset = UNSET,
) -> (
    GetApiV1CalendarPromotionsResponse200
    | GetApiV1CalendarPromotionsResponse400
    | GetApiV1CalendarPromotionsResponse401
    | GetApiV1CalendarPromotionsResponse429
    | None
):
    r"""Spisok aktsij

     Metod vozvraschaet spisok [aktsij](/openapi/promotion#tag/Kalendar-
    akcij/paths/~1api~1v1~1calendar~1promotions~1details/get) v WB s datami i vremenem provedenija.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov kategorii <strong>Kalendar' aktsij</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 6 sekund | 10 zaprosov | 600 millisekund | 5 zaprosov |

    </div>

    Args:
        start_date_time (datetime.datetime):  Example: 2023-09-01T00:00:00Z.
        end_date_time (datetime.datetime):  Example: 2024-08-01T23:59:59Z.
        all_promo (bool):  Default: False.
        limit (int | Unset):  Example: 10.
        offset (int | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetApiV1CalendarPromotionsResponse200 | GetApiV1CalendarPromotionsResponse400 | GetApiV1CalendarPromotionsResponse401 | GetApiV1CalendarPromotionsResponse429
    """

    return sync_detailed(
        client=client,
        start_date_time=start_date_time,
        end_date_time=end_date_time,
        all_promo=all_promo,
        limit=limit,
        offset=offset,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    start_date_time: datetime.datetime,
    end_date_time: datetime.datetime,
    all_promo: bool = False,
    limit: int | Unset = UNSET,
    offset: int | Unset = UNSET,
) -> Response[
    GetApiV1CalendarPromotionsResponse200
    | GetApiV1CalendarPromotionsResponse400
    | GetApiV1CalendarPromotionsResponse401
    | GetApiV1CalendarPromotionsResponse429
]:
    r"""Spisok aktsij

     Metod vozvraschaet spisok [aktsij](/openapi/promotion#tag/Kalendar-
    akcij/paths/~1api~1v1~1calendar~1promotions~1details/get) v WB s datami i vremenem provedenija.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov kategorii <strong>Kalendar' aktsij</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 6 sekund | 10 zaprosov | 600 millisekund | 5 zaprosov |

    </div>

    Args:
        start_date_time (datetime.datetime):  Example: 2023-09-01T00:00:00Z.
        end_date_time (datetime.datetime):  Example: 2024-08-01T23:59:59Z.
        all_promo (bool):  Default: False.
        limit (int | Unset):  Example: 10.
        offset (int | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetApiV1CalendarPromotionsResponse200 | GetApiV1CalendarPromotionsResponse400 | GetApiV1CalendarPromotionsResponse401 | GetApiV1CalendarPromotionsResponse429]
    """

    kwargs = _get_kwargs(
        start_date_time=start_date_time,
        end_date_time=end_date_time,
        all_promo=all_promo,
        limit=limit,
        offset=offset,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    start_date_time: datetime.datetime,
    end_date_time: datetime.datetime,
    all_promo: bool = False,
    limit: int | Unset = UNSET,
    offset: int | Unset = UNSET,
) -> (
    GetApiV1CalendarPromotionsResponse200
    | GetApiV1CalendarPromotionsResponse400
    | GetApiV1CalendarPromotionsResponse401
    | GetApiV1CalendarPromotionsResponse429
    | None
):
    r"""Spisok aktsij

     Metod vozvraschaet spisok [aktsij](/openapi/promotion#tag/Kalendar-
    akcij/paths/~1api~1v1~1calendar~1promotions~1details/get) v WB s datami i vremenem provedenija.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov kategorii <strong>Kalendar' aktsij</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 6 sekund | 10 zaprosov | 600 millisekund | 5 zaprosov |

    </div>

    Args:
        start_date_time (datetime.datetime):  Example: 2023-09-01T00:00:00Z.
        end_date_time (datetime.datetime):  Example: 2024-08-01T23:59:59Z.
        all_promo (bool):  Default: False.
        limit (int | Unset):  Example: 10.
        offset (int | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetApiV1CalendarPromotionsResponse200 | GetApiV1CalendarPromotionsResponse400 | GetApiV1CalendarPromotionsResponse401 | GetApiV1CalendarPromotionsResponse429
    """

    return (
        await asyncio_detailed(
            client=client,
            start_date_time=start_date_time,
            end_date_time=end_date_time,
            all_promo=all_promo,
            limit=limit,
            offset=offset,
        )
    ).parsed
