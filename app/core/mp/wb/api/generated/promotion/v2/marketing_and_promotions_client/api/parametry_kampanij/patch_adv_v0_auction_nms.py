from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.patch_adv_v0_auction_nms_body import PatchAdvV0AuctionNmsBody
from ...models.patch_adv_v0_auction_nms_response_200 import (
    PatchAdvV0AuctionNmsResponse200,
)
from ...models.patch_adv_v0_auction_nms_response_401 import (
    PatchAdvV0AuctionNmsResponse401,
)
from ...models.patch_adv_v0_auction_nms_response_429 import (
    PatchAdvV0AuctionNmsResponse429,
)
from ...models.response_400 import Response400
from ...types import Response


def _get_kwargs(
    *,
    body: PatchAdvV0AuctionNmsBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "patch",
        "url": "/adv/v0/auction/nms",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    PatchAdvV0AuctionNmsResponse200
    | PatchAdvV0AuctionNmsResponse401
    | PatchAdvV0AuctionNmsResponse429
    | Response400
    | None
):
    if response.status_code == 200:
        response_200 = PatchAdvV0AuctionNmsResponse200.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = Response400.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = PatchAdvV0AuctionNmsResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 429:
        response_429 = PatchAdvV0AuctionNmsResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    PatchAdvV0AuctionNmsResponse200
    | PatchAdvV0AuctionNmsResponse401
    | PatchAdvV0AuctionNmsResponse429
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
    body: PatchAdvV0AuctionNmsBody,
) -> Response[
    PatchAdvV0AuctionNmsResponse200
    | PatchAdvV0AuctionNmsResponse401
    | PatchAdvV0AuctionNmsResponse429
    | Response400
]:
    r"""Izmenenie spiska kartochek tovarov v kampanijah

     Metod dobavljaet i udaljaet kartochki tovarov v kampanijah.
    <br><br>
    Dlja kampanij v statusah `4`, `9` i `11`.
    <br><br>
    Dlja dobavljaemyh tovarov ustanavlivaetsja tekuschaja minimal'naja stavka.

     <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 1 zapros | 1 sekunda | 1 zapros |
    </div>

    Args:
        body (PatchAdvV0AuctionNmsBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PatchAdvV0AuctionNmsResponse200 | PatchAdvV0AuctionNmsResponse401 | PatchAdvV0AuctionNmsResponse429 | Response400]
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
    body: PatchAdvV0AuctionNmsBody,
) -> (
    PatchAdvV0AuctionNmsResponse200
    | PatchAdvV0AuctionNmsResponse401
    | PatchAdvV0AuctionNmsResponse429
    | Response400
    | None
):
    r"""Izmenenie spiska kartochek tovarov v kampanijah

     Metod dobavljaet i udaljaet kartochki tovarov v kampanijah.
    <br><br>
    Dlja kampanij v statusah `4`, `9` i `11`.
    <br><br>
    Dlja dobavljaemyh tovarov ustanavlivaetsja tekuschaja minimal'naja stavka.

     <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 1 zapros | 1 sekunda | 1 zapros |
    </div>

    Args:
        body (PatchAdvV0AuctionNmsBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PatchAdvV0AuctionNmsResponse200 | PatchAdvV0AuctionNmsResponse401 | PatchAdvV0AuctionNmsResponse429 | Response400
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: PatchAdvV0AuctionNmsBody,
) -> Response[
    PatchAdvV0AuctionNmsResponse200
    | PatchAdvV0AuctionNmsResponse401
    | PatchAdvV0AuctionNmsResponse429
    | Response400
]:
    r"""Izmenenie spiska kartochek tovarov v kampanijah

     Metod dobavljaet i udaljaet kartochki tovarov v kampanijah.
    <br><br>
    Dlja kampanij v statusah `4`, `9` i `11`.
    <br><br>
    Dlja dobavljaemyh tovarov ustanavlivaetsja tekuschaja minimal'naja stavka.

     <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 1 zapros | 1 sekunda | 1 zapros |
    </div>

    Args:
        body (PatchAdvV0AuctionNmsBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PatchAdvV0AuctionNmsResponse200 | PatchAdvV0AuctionNmsResponse401 | PatchAdvV0AuctionNmsResponse429 | Response400]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: PatchAdvV0AuctionNmsBody,
) -> (
    PatchAdvV0AuctionNmsResponse200
    | PatchAdvV0AuctionNmsResponse401
    | PatchAdvV0AuctionNmsResponse429
    | Response400
    | None
):
    r"""Izmenenie spiska kartochek tovarov v kampanijah

     Metod dobavljaet i udaljaet kartochki tovarov v kampanijah.
    <br><br>
    Dlja kampanij v statusah `4`, `9` i `11`.
    <br><br>
    Dlja dobavljaemyh tovarov ustanavlivaetsja tekuschaja minimal'naja stavka.

     <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 1 zapros | 1 sekunda | 1 zapros |
    </div>

    Args:
        body (PatchAdvV0AuctionNmsBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PatchAdvV0AuctionNmsResponse200 | PatchAdvV0AuctionNmsResponse401 | PatchAdvV0AuctionNmsResponse429 | Response400
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
