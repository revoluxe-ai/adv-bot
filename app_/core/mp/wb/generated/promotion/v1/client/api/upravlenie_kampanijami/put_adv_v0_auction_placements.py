from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.put_adv_v0_auction_placements_body import PutAdvV0AuctionPlacementsBody
from ...models.put_adv_v0_auction_placements_response_401 import (
    PutAdvV0AuctionPlacementsResponse401,
)
from ...models.put_adv_v0_auction_placements_response_429 import (
    PutAdvV0AuctionPlacementsResponse429,
)
from ...models.response_400 import Response400
from ...types import Response


def _get_kwargs(
    *,
    body: PutAdvV0AuctionPlacementsBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "put",
        "url": "/adv/v0/auction/placements",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[
    Union[
        Any,
        PutAdvV0AuctionPlacementsResponse401,
        PutAdvV0AuctionPlacementsResponse429,
        Response400,
    ]
]:
    if response.status_code == 204:
        response_204 = cast(Any, None)
        return response_204

    if response.status_code == 400:
        response_400 = Response400.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = PutAdvV0AuctionPlacementsResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 429:
        response_429 = PutAdvV0AuctionPlacementsResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[
    Union[
        Any,
        PutAdvV0AuctionPlacementsResponse401,
        PutAdvV0AuctionPlacementsResponse429,
        Response400,
    ]
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
    body: PutAdvV0AuctionPlacementsBody,
) -> Response[
    Union[
        Any,
        PutAdvV0AuctionPlacementsResponse401,
        PutAdvV0AuctionPlacementsResponse429,
        Response400,
    ]
]:
    r"""Izmenenie mest razmeschenija v kampanijah s ruchnoj stavkoj

     Metod menjaet mesta razmeschenija v kampanijah s ruchnoj stavkoj.
    <br><br>
    Dlja kampanij v statusah `4`, `9` i `11`.

     <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 1 zapros | 1 sekunda | 1 zapros |
    </div>

    Args:
        body (PutAdvV0AuctionPlacementsBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, PutAdvV0AuctionPlacementsResponse401, PutAdvV0AuctionPlacementsResponse429, Response400]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    body: PutAdvV0AuctionPlacementsBody,
) -> Optional[
    Union[
        Any,
        PutAdvV0AuctionPlacementsResponse401,
        PutAdvV0AuctionPlacementsResponse429,
        Response400,
    ]
]:
    r"""Izmenenie mest razmeschenija v kampanijah s ruchnoj stavkoj

     Metod menjaet mesta razmeschenija v kampanijah s ruchnoj stavkoj.
    <br><br>
    Dlja kampanij v statusah `4`, `9` i `11`.

     <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 1 zapros | 1 sekunda | 1 zapros |
    </div>

    Args:
        body (PutAdvV0AuctionPlacementsBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, PutAdvV0AuctionPlacementsResponse401, PutAdvV0AuctionPlacementsResponse429, Response400]
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: PutAdvV0AuctionPlacementsBody,
) -> Response[
    Union[
        Any,
        PutAdvV0AuctionPlacementsResponse401,
        PutAdvV0AuctionPlacementsResponse429,
        Response400,
    ]
]:
    r"""Izmenenie mest razmeschenija v kampanijah s ruchnoj stavkoj

     Metod menjaet mesta razmeschenija v kampanijah s ruchnoj stavkoj.
    <br><br>
    Dlja kampanij v statusah `4`, `9` i `11`.

     <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 1 zapros | 1 sekunda | 1 zapros |
    </div>

    Args:
        body (PutAdvV0AuctionPlacementsBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, PutAdvV0AuctionPlacementsResponse401, PutAdvV0AuctionPlacementsResponse429, Response400]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: PutAdvV0AuctionPlacementsBody,
) -> Optional[
    Union[
        Any,
        PutAdvV0AuctionPlacementsResponse401,
        PutAdvV0AuctionPlacementsResponse429,
        Response400,
    ]
]:
    r"""Izmenenie mest razmeschenija v kampanijah s ruchnoj stavkoj

     Metod menjaet mesta razmeschenija v kampanijah s ruchnoj stavkoj.
    <br><br>
    Dlja kampanij v statusah `4`, `9` i `11`.

     <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 1 zapros | 1 sekunda | 1 zapros |
    </div>

    Args:
        body (PutAdvV0AuctionPlacementsBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, PutAdvV0AuctionPlacementsResponse401, PutAdvV0AuctionPlacementsResponse429, Response400]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
