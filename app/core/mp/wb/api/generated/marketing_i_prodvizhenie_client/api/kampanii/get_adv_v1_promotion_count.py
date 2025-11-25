from http import HTTPStatus
from typing import Any, Dict, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_adv_v1_promotion_count_response_200 import GetAdvV1PromotionCountResponse200
from ...types import Response


def _get_kwargs() -> Dict[str, Any]:
    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": "/adv/v1/promotion/count",
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[Any, GetAdvV1PromotionCountResponse200]]:
    if response.status_code == HTTPStatus.OK:
        response_200 = GetAdvV1PromotionCountResponse200.from_dict(response.json())

        return response_200
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
) -> Response[Union[Any, GetAdvV1PromotionCountResponse200]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
) -> Response[Union[Any, GetAdvV1PromotionCountResponse200]]:
    r"""Spiski kampanij

     Metod vozvraschaet spiski vseh [reklamnyh
    kampanij](/openapi/promotion#tag/Kampanii/paths/~1adv~1v1~1promotion~1adverts/post) prodavtsa s ih
    ID. Kampanii sgruppirovany po tipu i statusu, u kazhdoj ukazana data poslednego izmenenija.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 5 zaprosov |
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, GetAdvV1PromotionCountResponse200]]
    """

    kwargs = _get_kwargs()

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
) -> Optional[Union[Any, GetAdvV1PromotionCountResponse200]]:
    r"""Spiski kampanij

     Metod vozvraschaet spiski vseh [reklamnyh
    kampanij](/openapi/promotion#tag/Kampanii/paths/~1adv~1v1~1promotion~1adverts/post) prodavtsa s ih
    ID. Kampanii sgruppirovany po tipu i statusu, u kazhdoj ukazana data poslednego izmenenija.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 5 zaprosov |
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, GetAdvV1PromotionCountResponse200]
    """

    return sync_detailed(
        client=client,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
) -> Response[Union[Any, GetAdvV1PromotionCountResponse200]]:
    r"""Spiski kampanij

     Metod vozvraschaet spiski vseh [reklamnyh
    kampanij](/openapi/promotion#tag/Kampanii/paths/~1adv~1v1~1promotion~1adverts/post) prodavtsa s ih
    ID. Kampanii sgruppirovany po tipu i statusu, u kazhdoj ukazana data poslednego izmenenija.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 5 zaprosov |
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, GetAdvV1PromotionCountResponse200]]
    """

    kwargs = _get_kwargs()

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
) -> Optional[Union[Any, GetAdvV1PromotionCountResponse200]]:
    r"""Spiski kampanij

     Metod vozvraschaet spiski vseh [reklamnyh
    kampanij](/openapi/promotion#tag/Kampanii/paths/~1adv~1v1~1promotion~1adverts/post) prodavtsa s ih
    ID. Kampanii sgruppirovany po tipu i statusu, u kazhdoj ukazana data poslednego izmenenija.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 5 zaprosov |
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, GetAdvV1PromotionCountResponse200]
    """

    return (
        await asyncio_detailed(
            client=client,
        )
    ).parsed
