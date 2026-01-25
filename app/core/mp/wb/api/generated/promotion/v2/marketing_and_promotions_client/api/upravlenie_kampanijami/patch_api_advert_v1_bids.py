from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.patch_api_advert_v1_bids_body import PatchApiAdvertV1BidsBody
from ...models.patch_api_advert_v1_bids_response_200 import (
    PatchApiAdvertV1BidsResponse200,
)
from ...models.patch_api_advert_v1_bids_response_401 import (
    PatchApiAdvertV1BidsResponse401,
)
from ...models.patch_api_advert_v1_bids_response_429 import (
    PatchApiAdvertV1BidsResponse429,
)
from ...models.response_400 import Response400
from ...types import Response


def _get_kwargs(
    *,
    body: PatchApiAdvertV1BidsBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "patch",
        "url": "/api/advert/v1/bids",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    PatchApiAdvertV1BidsResponse200
    | PatchApiAdvertV1BidsResponse401
    | PatchApiAdvertV1BidsResponse429
    | Response400
    | None
):
    if response.status_code == 200:
        response_200 = PatchApiAdvertV1BidsResponse200.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = Response400.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = PatchApiAdvertV1BidsResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 429:
        response_429 = PatchApiAdvertV1BidsResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    PatchApiAdvertV1BidsResponse200
    | PatchApiAdvertV1BidsResponse401
    | PatchApiAdvertV1BidsResponse429
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
    body: PatchApiAdvertV1BidsBody,
) -> Response[
    PatchApiAdvertV1BidsResponse200
    | PatchApiAdvertV1BidsResponse401
    | PatchApiAdvertV1BidsResponse429
    | Response400
]:
    r"""Izmenenie stavok v kampanijah

     Metod menjaet stavki kartochek tovarov po artikulam WB v kampanijah s edinoj ili ruchnoj stavkoj.
    <br><br>
    Dlja kampanij v statusah `4`, `9` i `11`.
    <br><br>
    V zaprose ukazhite mesto razmeschenija v parametre `placement`:
      - `combined` — v poiske i rekomendatsijah dlja kampanij s edinoj stavkoj
      - `search `ili `recommendations` — v poiske ili rekomendatsijah dlja kampanij s ruchnoj stavkoj

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 5 zaprosov |
    </div>

    Args:
        body (PatchApiAdvertV1BidsBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PatchApiAdvertV1BidsResponse200 | PatchApiAdvertV1BidsResponse401 | PatchApiAdvertV1BidsResponse429 | Response400]
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
    body: PatchApiAdvertV1BidsBody,
) -> (
    PatchApiAdvertV1BidsResponse200
    | PatchApiAdvertV1BidsResponse401
    | PatchApiAdvertV1BidsResponse429
    | Response400
    | None
):
    r"""Izmenenie stavok v kampanijah

     Metod menjaet stavki kartochek tovarov po artikulam WB v kampanijah s edinoj ili ruchnoj stavkoj.
    <br><br>
    Dlja kampanij v statusah `4`, `9` i `11`.
    <br><br>
    V zaprose ukazhite mesto razmeschenija v parametre `placement`:
      - `combined` — v poiske i rekomendatsijah dlja kampanij s edinoj stavkoj
      - `search `ili `recommendations` — v poiske ili rekomendatsijah dlja kampanij s ruchnoj stavkoj

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 5 zaprosov |
    </div>

    Args:
        body (PatchApiAdvertV1BidsBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PatchApiAdvertV1BidsResponse200 | PatchApiAdvertV1BidsResponse401 | PatchApiAdvertV1BidsResponse429 | Response400
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: PatchApiAdvertV1BidsBody,
) -> Response[
    PatchApiAdvertV1BidsResponse200
    | PatchApiAdvertV1BidsResponse401
    | PatchApiAdvertV1BidsResponse429
    | Response400
]:
    r"""Izmenenie stavok v kampanijah

     Metod menjaet stavki kartochek tovarov po artikulam WB v kampanijah s edinoj ili ruchnoj stavkoj.
    <br><br>
    Dlja kampanij v statusah `4`, `9` i `11`.
    <br><br>
    V zaprose ukazhite mesto razmeschenija v parametre `placement`:
      - `combined` — v poiske i rekomendatsijah dlja kampanij s edinoj stavkoj
      - `search `ili `recommendations` — v poiske ili rekomendatsijah dlja kampanij s ruchnoj stavkoj

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 5 zaprosov |
    </div>

    Args:
        body (PatchApiAdvertV1BidsBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PatchApiAdvertV1BidsResponse200 | PatchApiAdvertV1BidsResponse401 | PatchApiAdvertV1BidsResponse429 | Response400]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: PatchApiAdvertV1BidsBody,
) -> (
    PatchApiAdvertV1BidsResponse200
    | PatchApiAdvertV1BidsResponse401
    | PatchApiAdvertV1BidsResponse429
    | Response400
    | None
):
    r"""Izmenenie stavok v kampanijah

     Metod menjaet stavki kartochek tovarov po artikulam WB v kampanijah s edinoj ili ruchnoj stavkoj.
    <br><br>
    Dlja kampanij v statusah `4`, `9` i `11`.
    <br><br>
    V zaprose ukazhite mesto razmeschenija v parametre `placement`:
      - `combined` — v poiske i rekomendatsijah dlja kampanij s edinoj stavkoj
      - `search `ili `recommendations` — v poiske ili rekomendatsijah dlja kampanij s ruchnoj stavkoj

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 5 zaprosov |
    </div>

    Args:
        body (PatchApiAdvertV1BidsBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PatchApiAdvertV1BidsResponse200 | PatchApiAdvertV1BidsResponse401 | PatchApiAdvertV1BidsResponse429 | Response400
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
