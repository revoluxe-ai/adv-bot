from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.field_400_response import Field400Response
from ...models.get_adv_v0_start_response_401 import GetAdvV0StartResponse401
from ...models.get_adv_v0_start_response_429 import GetAdvV0StartResponse429
from ...types import UNSET, Response


def _get_kwargs(
    *,
    id: int,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["id"] = id

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/adv/v0/start",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    Any
    | Field400Response
    | GetAdvV0StartResponse401
    | GetAdvV0StartResponse429
    | str
    | None
):
    if response.status_code == 200:
        response_200 = cast(Any, None)
        return response_200

    if response.status_code == 400:
        response_400 = Field400Response.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = GetAdvV0StartResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 422:
        response_422 = response.text
        return response_422

    if response.status_code == 429:
        response_429 = GetAdvV0StartResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    Any | Field400Response | GetAdvV0StartResponse401 | GetAdvV0StartResponse429 | str
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
    id: int,
) -> Response[
    Any | Field400Response | GetAdvV0StartResponse401 | GetAdvV0StartResponse429 | str
]:
    r"""Zapusk kampanii

     Metod zapuskaet [kampanii](/openapi/promotion#tag/Kampanii/paths/~1api~1advert~1v2~1adverts/get) v
    statusah `4` — gotovo k zapusku — ili `11` — pauza.

    Chtoby zapustit' kampaniju so statusom `4`, neobhodimo vypolnit' dva uslovija:
      1. Posle sozdanija kampanii v kabinete **WB. Prodvizhenie** nazhat' knopku **Primenit'
    izmenenija**.
      2. Ustanovit' bjudzhet — maksimal'nuju summu zatrat na kampaniju.

    Chtoby zapustit' kampaniju so statusom `11`, prover'te ee bjudzhet. Esli bjudzheta nedostatochno,
    [popolnite ego](/openapi/promotion#tag/Finansy/paths/~1adv~1v1~1budget~1deposit/post).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 5 zaprosov |
    </div>

    Args:
        id (int):  Example: 1234.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | Field400Response | GetAdvV0StartResponse401 | GetAdvV0StartResponse429 | str]
    """

    kwargs = _get_kwargs(
        id=id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    id: int,
) -> (
    Any
    | Field400Response
    | GetAdvV0StartResponse401
    | GetAdvV0StartResponse429
    | str
    | None
):
    r"""Zapusk kampanii

     Metod zapuskaet [kampanii](/openapi/promotion#tag/Kampanii/paths/~1api~1advert~1v2~1adverts/get) v
    statusah `4` — gotovo k zapusku — ili `11` — pauza.

    Chtoby zapustit' kampaniju so statusom `4`, neobhodimo vypolnit' dva uslovija:
      1. Posle sozdanija kampanii v kabinete **WB. Prodvizhenie** nazhat' knopku **Primenit'
    izmenenija**.
      2. Ustanovit' bjudzhet — maksimal'nuju summu zatrat na kampaniju.

    Chtoby zapustit' kampaniju so statusom `11`, prover'te ee bjudzhet. Esli bjudzheta nedostatochno,
    [popolnite ego](/openapi/promotion#tag/Finansy/paths/~1adv~1v1~1budget~1deposit/post).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 5 zaprosov |
    </div>

    Args:
        id (int):  Example: 1234.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | Field400Response | GetAdvV0StartResponse401 | GetAdvV0StartResponse429 | str
    """

    return sync_detailed(
        client=client,
        id=id,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    id: int,
) -> Response[
    Any | Field400Response | GetAdvV0StartResponse401 | GetAdvV0StartResponse429 | str
]:
    r"""Zapusk kampanii

     Metod zapuskaet [kampanii](/openapi/promotion#tag/Kampanii/paths/~1api~1advert~1v2~1adverts/get) v
    statusah `4` — gotovo k zapusku — ili `11` — pauza.

    Chtoby zapustit' kampaniju so statusom `4`, neobhodimo vypolnit' dva uslovija:
      1. Posle sozdanija kampanii v kabinete **WB. Prodvizhenie** nazhat' knopku **Primenit'
    izmenenija**.
      2. Ustanovit' bjudzhet — maksimal'nuju summu zatrat na kampaniju.

    Chtoby zapustit' kampaniju so statusom `11`, prover'te ee bjudzhet. Esli bjudzheta nedostatochno,
    [popolnite ego](/openapi/promotion#tag/Finansy/paths/~1adv~1v1~1budget~1deposit/post).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 5 zaprosov |
    </div>

    Args:
        id (int):  Example: 1234.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | Field400Response | GetAdvV0StartResponse401 | GetAdvV0StartResponse429 | str]
    """

    kwargs = _get_kwargs(
        id=id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    id: int,
) -> (
    Any
    | Field400Response
    | GetAdvV0StartResponse401
    | GetAdvV0StartResponse429
    | str
    | None
):
    r"""Zapusk kampanii

     Metod zapuskaet [kampanii](/openapi/promotion#tag/Kampanii/paths/~1api~1advert~1v2~1adverts/get) v
    statusah `4` — gotovo k zapusku — ili `11` — pauza.

    Chtoby zapustit' kampaniju so statusom `4`, neobhodimo vypolnit' dva uslovija:
      1. Posle sozdanija kampanii v kabinete **WB. Prodvizhenie** nazhat' knopku **Primenit'
    izmenenija**.
      2. Ustanovit' bjudzhet — maksimal'nuju summu zatrat na kampaniju.

    Chtoby zapustit' kampaniju so statusom `11`, prover'te ee bjudzhet. Esli bjudzheta nedostatochno,
    [popolnite ego](/openapi/promotion#tag/Finansy/paths/~1adv~1v1~1budget~1deposit/post).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 5 zaprosov |
    </div>

    Args:
        id (int):  Example: 1234.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | Field400Response | GetAdvV0StartResponse401 | GetAdvV0StartResponse429 | str
    """

    return (
        await asyncio_detailed(
            client=client,
            id=id,
        )
    ).parsed
