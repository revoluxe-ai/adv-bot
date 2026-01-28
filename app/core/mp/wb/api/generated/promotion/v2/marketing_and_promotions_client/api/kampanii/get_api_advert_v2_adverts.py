from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_adverts import GetAdverts
from ...models.get_api_advert_v2_adverts_payment_type import (
    GetApiAdvertV2AdvertsPaymentType,
)
from ...models.get_api_advert_v2_adverts_response_401 import (
    GetApiAdvertV2AdvertsResponse401,
)
from ...models.get_api_advert_v2_adverts_response_429 import (
    GetApiAdvertV2AdvertsResponse429,
)
from ...models.get_api_advert_v2_adverts_statuses import GetApiAdvertV2AdvertsStatuses
from ...models.response_400 import Response400
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    ids: str | Unset = UNSET,
    statuses: GetApiAdvertV2AdvertsStatuses | Unset = UNSET,
    payment_type: GetApiAdvertV2AdvertsPaymentType | Unset = UNSET,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["ids"] = ids

    json_statuses: str | Unset = UNSET
    if not isinstance(statuses, Unset):
        json_statuses = statuses.value

    params["statuses"] = json_statuses

    json_payment_type: str | Unset = UNSET
    if not isinstance(payment_type, Unset):
        json_payment_type = payment_type.value

    params["payment_type"] = json_payment_type

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/advert/v2/adverts",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    GetAdverts
    | GetApiAdvertV2AdvertsResponse401
    | GetApiAdvertV2AdvertsResponse429
    | Response400
    | None
):
    if response.status_code == 200:
        response_200 = GetAdverts.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = Response400.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = GetApiAdvertV2AdvertsResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 429:
        response_429 = GetApiAdvertV2AdvertsResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    GetAdverts
    | GetApiAdvertV2AdvertsResponse401
    | GetApiAdvertV2AdvertsResponse429
    | Response400
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
    ids: str | Unset = UNSET,
    statuses: GetApiAdvertV2AdvertsStatuses | Unset = UNSET,
    payment_type: GetApiAdvertV2AdvertsPaymentType | Unset = UNSET,
) -> Response[
    GetAdverts
    | GetApiAdvertV2AdvertsResponse401
    | GetApiAdvertV2AdvertsResponse429
    | Response400
]:
    r"""Informatsija o kampanijah

     Metod vozvraschaet informatsiju o reklamnyh kampanijah s edinoj ili ruchnoj stavkoj po ih statusam,
    tipam oplaty i ID.

     <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 5 zaprosov |
    </div>

    Args:
        ids (str | Unset):  Example: 12345,23456,34567,45678,56789.
        statuses (GetApiAdvertV2AdvertsStatuses | Unset):  Example: -1,4,8.
        payment_type (GetApiAdvertV2AdvertsPaymentType | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetAdverts | GetApiAdvertV2AdvertsResponse401 | GetApiAdvertV2AdvertsResponse429 | Response400]
    """

    kwargs = _get_kwargs(
        ids=ids,
        statuses=statuses,
        payment_type=payment_type,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    ids: str | Unset = UNSET,
    statuses: GetApiAdvertV2AdvertsStatuses | Unset = UNSET,
    payment_type: GetApiAdvertV2AdvertsPaymentType | Unset = UNSET,
) -> (
    GetAdverts
    | GetApiAdvertV2AdvertsResponse401
    | GetApiAdvertV2AdvertsResponse429
    | Response400
    | None
):
    r"""Informatsija o kampanijah

     Metod vozvraschaet informatsiju o reklamnyh kampanijah s edinoj ili ruchnoj stavkoj po ih statusam,
    tipam oplaty i ID.

     <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 5 zaprosov |
    </div>

    Args:
        ids (str | Unset):  Example: 12345,23456,34567,45678,56789.
        statuses (GetApiAdvertV2AdvertsStatuses | Unset):  Example: -1,4,8.
        payment_type (GetApiAdvertV2AdvertsPaymentType | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetAdverts | GetApiAdvertV2AdvertsResponse401 | GetApiAdvertV2AdvertsResponse429 | Response400
    """

    return sync_detailed(
        client=client,
        ids=ids,
        statuses=statuses,
        payment_type=payment_type,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    ids: str | Unset = UNSET,
    statuses: GetApiAdvertV2AdvertsStatuses | Unset = UNSET,
    payment_type: GetApiAdvertV2AdvertsPaymentType | Unset = UNSET,
) -> Response[
    GetAdverts
    | GetApiAdvertV2AdvertsResponse401
    | GetApiAdvertV2AdvertsResponse429
    | Response400
]:
    r"""Informatsija o kampanijah

     Metod vozvraschaet informatsiju o reklamnyh kampanijah s edinoj ili ruchnoj stavkoj po ih statusam,
    tipam oplaty i ID.

     <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 5 zaprosov |
    </div>

    Args:
        ids (str | Unset):  Example: 12345,23456,34567,45678,56789.
        statuses (GetApiAdvertV2AdvertsStatuses | Unset):  Example: -1,4,8.
        payment_type (GetApiAdvertV2AdvertsPaymentType | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetAdverts | GetApiAdvertV2AdvertsResponse401 | GetApiAdvertV2AdvertsResponse429 | Response400]
    """

    kwargs = _get_kwargs(
        ids=ids,
        statuses=statuses,
        payment_type=payment_type,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    ids: str | Unset = UNSET,
    statuses: GetApiAdvertV2AdvertsStatuses | Unset = UNSET,
    payment_type: GetApiAdvertV2AdvertsPaymentType | Unset = UNSET,
) -> (
    GetAdverts
    | GetApiAdvertV2AdvertsResponse401
    | GetApiAdvertV2AdvertsResponse429
    | Response400
    | None
):
    r"""Informatsija o kampanijah

     Metod vozvraschaet informatsiju o reklamnyh kampanijah s edinoj ili ruchnoj stavkoj po ih statusam,
    tipam oplaty i ID.

     <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 5 zaprosov |
    </div>

    Args:
        ids (str | Unset):  Example: 12345,23456,34567,45678,56789.
        statuses (GetApiAdvertV2AdvertsStatuses | Unset):  Example: -1,4,8.
        payment_type (GetApiAdvertV2AdvertsPaymentType | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetAdverts | GetApiAdvertV2AdvertsResponse401 | GetApiAdvertV2AdvertsResponse429 | Response400
    """

    return (
        await asyncio_detailed(
            client=client,
            ids=ids,
            statuses=statuses,
            payment_type=payment_type,
        )
    ).parsed
