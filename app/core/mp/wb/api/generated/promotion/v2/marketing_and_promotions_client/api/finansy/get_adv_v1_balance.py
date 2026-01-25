from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_adv_v1_balance_response_200 import GetAdvV1BalanceResponse200
from ...models.get_adv_v1_balance_response_401 import GetAdvV1BalanceResponse401
from ...models.get_adv_v1_balance_response_429 import GetAdvV1BalanceResponse429
from ...types import Response


def _get_kwargs() -> dict[str, Any]:
    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/adv/v1/balance",
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    GetAdvV1BalanceResponse200
    | GetAdvV1BalanceResponse401
    | GetAdvV1BalanceResponse429
    | str
    | None
):
    if response.status_code == 200:
        response_200 = GetAdvV1BalanceResponse200.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = cast(str, response.json())
        return response_400

    if response.status_code == 401:
        response_401 = GetAdvV1BalanceResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 429:
        response_429 = GetAdvV1BalanceResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    GetAdvV1BalanceResponse200
    | GetAdvV1BalanceResponse401
    | GetAdvV1BalanceResponse429
    | str
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
) -> Response[
    GetAdvV1BalanceResponse200
    | GetAdvV1BalanceResponse401
    | GetAdvV1BalanceResponse429
    | str
]:
    r"""Balans

     Metod vozvraschaet informatsiju o:
      - schete kabineta Prodvizhenija WB. Ego popolnjaet prodavets.
      - balanse — maksimal'noj summe dlja oplaty kampanii po vzaimoraschetu: uderzhanii sredstv iz
    buduschih prodazh. Balans popolnit' nel'zja, on rasschityvaetsja avtomaticheski na osnove otchetov
    po prodvizheniju.
      - bonusnyh nachislenijah WB.

    Informatsiju o bjudzhete kampanij mozhno poluchit' v [otdel'nom
    metode](/openapi/promotion#tag/Finansy/paths/~1adv~1v1~1budget/get).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 1 zapros | 1 sekunda | 5 zaprosov |
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetAdvV1BalanceResponse200 | GetAdvV1BalanceResponse401 | GetAdvV1BalanceResponse429 | str]
    """

    kwargs = _get_kwargs()

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
) -> (
    GetAdvV1BalanceResponse200
    | GetAdvV1BalanceResponse401
    | GetAdvV1BalanceResponse429
    | str
    | None
):
    r"""Balans

     Metod vozvraschaet informatsiju o:
      - schete kabineta Prodvizhenija WB. Ego popolnjaet prodavets.
      - balanse — maksimal'noj summe dlja oplaty kampanii po vzaimoraschetu: uderzhanii sredstv iz
    buduschih prodazh. Balans popolnit' nel'zja, on rasschityvaetsja avtomaticheski na osnove otchetov
    po prodvizheniju.
      - bonusnyh nachislenijah WB.

    Informatsiju o bjudzhete kampanij mozhno poluchit' v [otdel'nom
    metode](/openapi/promotion#tag/Finansy/paths/~1adv~1v1~1budget/get).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 1 zapros | 1 sekunda | 5 zaprosov |
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetAdvV1BalanceResponse200 | GetAdvV1BalanceResponse401 | GetAdvV1BalanceResponse429 | str
    """

    return sync_detailed(
        client=client,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
) -> Response[
    GetAdvV1BalanceResponse200
    | GetAdvV1BalanceResponse401
    | GetAdvV1BalanceResponse429
    | str
]:
    r"""Balans

     Metod vozvraschaet informatsiju o:
      - schete kabineta Prodvizhenija WB. Ego popolnjaet prodavets.
      - balanse — maksimal'noj summe dlja oplaty kampanii po vzaimoraschetu: uderzhanii sredstv iz
    buduschih prodazh. Balans popolnit' nel'zja, on rasschityvaetsja avtomaticheski na osnove otchetov
    po prodvizheniju.
      - bonusnyh nachislenijah WB.

    Informatsiju o bjudzhete kampanij mozhno poluchit' v [otdel'nom
    metode](/openapi/promotion#tag/Finansy/paths/~1adv~1v1~1budget/get).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 1 zapros | 1 sekunda | 5 zaprosov |
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetAdvV1BalanceResponse200 | GetAdvV1BalanceResponse401 | GetAdvV1BalanceResponse429 | str]
    """

    kwargs = _get_kwargs()

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
) -> (
    GetAdvV1BalanceResponse200
    | GetAdvV1BalanceResponse401
    | GetAdvV1BalanceResponse429
    | str
    | None
):
    r"""Balans

     Metod vozvraschaet informatsiju o:
      - schete kabineta Prodvizhenija WB. Ego popolnjaet prodavets.
      - balanse — maksimal'noj summe dlja oplaty kampanii po vzaimoraschetu: uderzhanii sredstv iz
    buduschih prodazh. Balans popolnit' nel'zja, on rasschityvaetsja avtomaticheski na osnove otchetov
    po prodvizheniju.
      - bonusnyh nachislenijah WB.

    Informatsiju o bjudzhete kampanij mozhno poluchit' v [otdel'nom
    metode](/openapi/promotion#tag/Finansy/paths/~1adv~1v1~1budget/get).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 1 zapros | 1 sekunda | 5 zaprosov |
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetAdvV1BalanceResponse200 | GetAdvV1BalanceResponse401 | GetAdvV1BalanceResponse429 | str
    """

    return (
        await asyncio_detailed(
            client=client,
        )
    ).parsed
