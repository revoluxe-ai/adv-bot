from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.patch_adv_v0_bids_body import PatchAdvV0BidsBody
from ...models.patch_adv_v0_bids_response_400 import PatchAdvV0BidsResponse400
from ...models.patch_adv_v0_bids_response_401 import PatchAdvV0BidsResponse401
from ...models.patch_adv_v0_bids_response_429 import PatchAdvV0BidsResponse429
from ...types import Response


def _get_kwargs(
    *,
    body: PatchAdvV0BidsBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "patch",
        "url": "/adv/v0/bids",
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
        PatchAdvV0BidsResponse400,
        PatchAdvV0BidsResponse401,
        PatchAdvV0BidsResponse429,
    ]
]:
    if response.status_code == 204:
        response_204 = cast(Any, None)
        return response_204

    if response.status_code == 400:
        response_400 = PatchAdvV0BidsResponse400.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = PatchAdvV0BidsResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 429:
        response_429 = PatchAdvV0BidsResponse429.from_dict(response.json())

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
        PatchAdvV0BidsResponse400,
        PatchAdvV0BidsResponse401,
        PatchAdvV0BidsResponse429,
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
    client: Union[AuthenticatedClient, Client],
    body: PatchAdvV0BidsBody,
) -> Response[
    Union[
        Any,
        PatchAdvV0BidsResponse400,
        PatchAdvV0BidsResponse401,
        PatchAdvV0BidsResponse429,
    ]
]:
    r"""Izmenenie stavok

     Metod menjaet stavki kartochek tovarov po artikulam WB v kampanijah s edinoj stavkoj.
    <br><br>
    Dlja kampanij v statusah `4`, `9` i `11`.
    <br><br>
    Dlja izmenenija stavok v kampanijah s ruchnoj stavkoj ispol'zujte [otdel'nyj
    metod](/openapi/promotion#tag/Upravlenie-kampaniyami/paths/~1adv~1v0~1auction~1bids/patch).
    <br><br>
    Minimal'no dopustimye stavki vy mozhete poluchit' v otvete metoda [poluchenija minimal'nyh stavok
    dlja kartochek tovarov](/openapi/promotion#tag/Sozdanie-kampanij/paths/~1adv~1v0~1bids~1min/post).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 5 zaprosov |
    </div>

    Args:
        body (PatchAdvV0BidsBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, PatchAdvV0BidsResponse400, PatchAdvV0BidsResponse401, PatchAdvV0BidsResponse429]]
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
    client: Union[AuthenticatedClient, Client],
    body: PatchAdvV0BidsBody,
) -> Optional[
    Union[
        Any,
        PatchAdvV0BidsResponse400,
        PatchAdvV0BidsResponse401,
        PatchAdvV0BidsResponse429,
    ]
]:
    r"""Izmenenie stavok

     Metod menjaet stavki kartochek tovarov po artikulam WB v kampanijah s edinoj stavkoj.
    <br><br>
    Dlja kampanij v statusah `4`, `9` i `11`.
    <br><br>
    Dlja izmenenija stavok v kampanijah s ruchnoj stavkoj ispol'zujte [otdel'nyj
    metod](/openapi/promotion#tag/Upravlenie-kampaniyami/paths/~1adv~1v0~1auction~1bids/patch).
    <br><br>
    Minimal'no dopustimye stavki vy mozhete poluchit' v otvete metoda [poluchenija minimal'nyh stavok
    dlja kartochek tovarov](/openapi/promotion#tag/Sozdanie-kampanij/paths/~1adv~1v0~1bids~1min/post).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 5 zaprosov |
    </div>

    Args:
        body (PatchAdvV0BidsBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, PatchAdvV0BidsResponse400, PatchAdvV0BidsResponse401, PatchAdvV0BidsResponse429]
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: PatchAdvV0BidsBody,
) -> Response[
    Union[
        Any,
        PatchAdvV0BidsResponse400,
        PatchAdvV0BidsResponse401,
        PatchAdvV0BidsResponse429,
    ]
]:
    r"""Izmenenie stavok

     Metod menjaet stavki kartochek tovarov po artikulam WB v kampanijah s edinoj stavkoj.
    <br><br>
    Dlja kampanij v statusah `4`, `9` i `11`.
    <br><br>
    Dlja izmenenija stavok v kampanijah s ruchnoj stavkoj ispol'zujte [otdel'nyj
    metod](/openapi/promotion#tag/Upravlenie-kampaniyami/paths/~1adv~1v0~1auction~1bids/patch).
    <br><br>
    Minimal'no dopustimye stavki vy mozhete poluchit' v otvete metoda [poluchenija minimal'nyh stavok
    dlja kartochek tovarov](/openapi/promotion#tag/Sozdanie-kampanij/paths/~1adv~1v0~1bids~1min/post).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 5 zaprosov |
    </div>

    Args:
        body (PatchAdvV0BidsBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, PatchAdvV0BidsResponse400, PatchAdvV0BidsResponse401, PatchAdvV0BidsResponse429]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    body: PatchAdvV0BidsBody,
) -> Optional[
    Union[
        Any,
        PatchAdvV0BidsResponse400,
        PatchAdvV0BidsResponse401,
        PatchAdvV0BidsResponse429,
    ]
]:
    r"""Izmenenie stavok

     Metod menjaet stavki kartochek tovarov po artikulam WB v kampanijah s edinoj stavkoj.
    <br><br>
    Dlja kampanij v statusah `4`, `9` i `11`.
    <br><br>
    Dlja izmenenija stavok v kampanijah s ruchnoj stavkoj ispol'zujte [otdel'nyj
    metod](/openapi/promotion#tag/Upravlenie-kampaniyami/paths/~1adv~1v0~1auction~1bids/patch).
    <br><br>
    Minimal'no dopustimye stavki vy mozhete poluchit' v otvete metoda [poluchenija minimal'nyh stavok
    dlja kartochek tovarov](/openapi/promotion#tag/Sozdanie-kampanij/paths/~1adv~1v0~1bids~1min/post).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 5 zaprosov |
    </div>

    Args:
        body (PatchAdvV0BidsBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, PatchAdvV0BidsResponse400, PatchAdvV0BidsResponse401, PatchAdvV0BidsResponse429]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
