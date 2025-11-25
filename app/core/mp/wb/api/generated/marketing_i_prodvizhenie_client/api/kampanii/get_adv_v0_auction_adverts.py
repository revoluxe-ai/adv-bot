from http import HTTPStatus
from typing import Any, Dict, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_adv_v0_auction_adverts_payment_type import GetAdvV0AuctionAdvertsPaymentType
from ...models.get_adv_v0_auction_adverts_statuses import GetAdvV0AuctionAdvertsStatuses
from ...models.get_auction_adverts import GetAuctionAdverts
from ...models.response_400 import Response400
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    ids: Union[Unset, str] = UNSET,
    statuses: Union[Unset, GetAdvV0AuctionAdvertsStatuses] = UNSET,
    payment_type: Union[Unset, GetAdvV0AuctionAdvertsPaymentType] = UNSET,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {}

    params["ids"] = ids

    json_statuses: Union[Unset, str] = UNSET
    if not isinstance(statuses, Unset):
        json_statuses = statuses.value

    params["statuses"] = json_statuses

    json_payment_type: Union[Unset, str] = UNSET
    if not isinstance(payment_type, Unset):
        json_payment_type = payment_type.value

    params["payment_type"] = json_payment_type

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": "/adv/v0/auction/adverts",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[Any, GetAuctionAdverts, Response400]]:
    if response.status_code == HTTPStatus.OK:
        response_200 = GetAuctionAdverts.from_dict(response.json())

        return response_200
    if response.status_code == HTTPStatus.BAD_REQUEST:
        response_400 = Response400.from_dict(response.json())

        return response_400
    if response.status_code == HTTPStatus.UNAUTHORIZED:
        response_401 = cast(Any, None)
        return response_401
    if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
        response_429 = cast(Any, None)
        return response_429
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[Union[Any, GetAuctionAdverts, Response400]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    ids: Union[Unset, str] = UNSET,
    statuses: Union[Unset, GetAdvV0AuctionAdvertsStatuses] = UNSET,
    payment_type: Union[Unset, GetAdvV0AuctionAdvertsPaymentType] = UNSET,
) -> Response[Union[Any, GetAuctionAdverts, Response400]]:
    r"""Informatsija o kampanijah s ruchnoj stavkoj

     Metod vozvraschaet informatsiju o reklamnyh kampanijah s ruchnoj stavkoj po ih statusam, tipam
    oplaty i ID.

     <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 5 zaprosov |
    </div>

    Args:
        ids (Union[Unset, str]):  Example: 12345,23456,34567,45678,56789.
        statuses (Union[Unset, GetAdvV0AuctionAdvertsStatuses]):  Example: -1,4,8.
        payment_type (Union[Unset, GetAdvV0AuctionAdvertsPaymentType]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, GetAuctionAdverts, Response400]]
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
    ids: Union[Unset, str] = UNSET,
    statuses: Union[Unset, GetAdvV0AuctionAdvertsStatuses] = UNSET,
    payment_type: Union[Unset, GetAdvV0AuctionAdvertsPaymentType] = UNSET,
) -> Optional[Union[Any, GetAuctionAdverts, Response400]]:
    r"""Informatsija o kampanijah s ruchnoj stavkoj

     Metod vozvraschaet informatsiju o reklamnyh kampanijah s ruchnoj stavkoj po ih statusam, tipam
    oplaty i ID.

     <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 5 zaprosov |
    </div>

    Args:
        ids (Union[Unset, str]):  Example: 12345,23456,34567,45678,56789.
        statuses (Union[Unset, GetAdvV0AuctionAdvertsStatuses]):  Example: -1,4,8.
        payment_type (Union[Unset, GetAdvV0AuctionAdvertsPaymentType]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, GetAuctionAdverts, Response400]
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
    ids: Union[Unset, str] = UNSET,
    statuses: Union[Unset, GetAdvV0AuctionAdvertsStatuses] = UNSET,
    payment_type: Union[Unset, GetAdvV0AuctionAdvertsPaymentType] = UNSET,
) -> Response[Union[Any, GetAuctionAdverts, Response400]]:
    r"""Informatsija o kampanijah s ruchnoj stavkoj

     Metod vozvraschaet informatsiju o reklamnyh kampanijah s ruchnoj stavkoj po ih statusam, tipam
    oplaty i ID.

     <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 5 zaprosov |
    </div>

    Args:
        ids (Union[Unset, str]):  Example: 12345,23456,34567,45678,56789.
        statuses (Union[Unset, GetAdvV0AuctionAdvertsStatuses]):  Example: -1,4,8.
        payment_type (Union[Unset, GetAdvV0AuctionAdvertsPaymentType]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, GetAuctionAdverts, Response400]]
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
    ids: Union[Unset, str] = UNSET,
    statuses: Union[Unset, GetAdvV0AuctionAdvertsStatuses] = UNSET,
    payment_type: Union[Unset, GetAdvV0AuctionAdvertsPaymentType] = UNSET,
) -> Optional[Union[Any, GetAuctionAdverts, Response400]]:
    r"""Informatsija o kampanijah s ruchnoj stavkoj

     Metod vozvraschaet informatsiju o reklamnyh kampanijah s ruchnoj stavkoj po ih statusam, tipam
    oplaty i ID.

     <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 5 zaprosov |
    </div>

    Args:
        ids (Union[Unset, str]):  Example: 12345,23456,34567,45678,56789.
        statuses (Union[Unset, GetAdvV0AuctionAdvertsStatuses]):  Example: -1,4,8.
        payment_type (Union[Unset, GetAdvV0AuctionAdvertsPaymentType]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, GetAuctionAdverts, Response400]
    """

    return (
        await asyncio_detailed(
            client=client,
            ids=ids,
            statuses=statuses,
            payment_type=payment_type,
        )
    ).parsed
