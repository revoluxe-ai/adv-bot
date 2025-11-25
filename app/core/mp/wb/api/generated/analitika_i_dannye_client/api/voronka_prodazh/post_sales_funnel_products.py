from http import HTTPStatus
from typing import Any, Dict, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_sales_funnel_products_response_200 import PostSalesFunnelProductsResponse200
from ...models.products_request import ProductsRequest
from ...types import Response


def _get_kwargs(
    *,
    body: ProductsRequest,
) -> Dict[str, Any]:
    headers: Dict[str, Any] = {}

    _kwargs: Dict[str, Any] = {
        "method": "post",
        "url": "/api/analytics/v3/sales-funnel/products",
    }

    _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[Any, PostSalesFunnelProductsResponse200]]:
    if response.status_code == HTTPStatus.OK:
        response_200 = PostSalesFunnelProductsResponse200.from_dict(response.json())

        return response_200
    if response.status_code == HTTPStatus.BAD_REQUEST:
        response_400 = cast(Any, None)
        return response_400
    if response.status_code == HTTPStatus.UNAUTHORIZED:
        response_401 = cast(Any, None)
        return response_401
    if response.status_code == HTTPStatus.FORBIDDEN:
        response_403 = cast(Any, None)
        return response_403
    if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
        response_429 = cast(Any, None)
        return response_429
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[Union[Any, PostSalesFunnelProductsResponse200]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: ProductsRequest,
) -> Response[Union[Any, PostSalesFunnelProductsResponse200]]:
    r"""Statistika kartochek tovarov za period

     Metod formiruet otchet o tovarah, sravnivaja kljuchevye pokazateli — naprimer, dobavlenija v
    korzinu, zakazy i perehody v kartochku tovara — za tekuschij period s analogichnym proshlym.<br><br>

    Parametry `brandNames`,`subjectIds`, `tagIds`, `nmIds` mogut byt' pustymi `[]`, togda v otvete
    vozvraschajutsja vse kartochki prodavtsa.<br><br>

    Esli vy ukazali neskol'ko parametrov, v otvete budut kartochki, v kotoryh est' odnovremenno vse eti
    parametry. Esli kartochki ne podhodjat po parametram zaprosa, vernetsja pustoj otvet `[]`.<br><br>

    Mozhno poluchit' otchet maksimum za poslednie 365 dnej.<br><br>

    V dannyh predyduschego perioda:
      * Dannye v `pastPeriod` ukazany za takoj zhe period, chto i v `selectedPeriod`
      * Esli data nachala  `pastPeriod` ran'she, chem god nazad ot tekuschej daty, ona budet privedena k
    vidu: `pastPeriod.start = tekuschaja data — 365 dnej`

    Mozhno ispol'zovat' paginatsiju.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 3 zaprosa | 20 sekund | 3 zaprosa |
    </div>

    Args:
        body (ProductsRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, PostSalesFunnelProductsResponse200]]
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
    body: ProductsRequest,
) -> Optional[Union[Any, PostSalesFunnelProductsResponse200]]:
    r"""Statistika kartochek tovarov za period

     Metod formiruet otchet o tovarah, sravnivaja kljuchevye pokazateli — naprimer, dobavlenija v
    korzinu, zakazy i perehody v kartochku tovara — za tekuschij period s analogichnym proshlym.<br><br>

    Parametry `brandNames`,`subjectIds`, `tagIds`, `nmIds` mogut byt' pustymi `[]`, togda v otvete
    vozvraschajutsja vse kartochki prodavtsa.<br><br>

    Esli vy ukazali neskol'ko parametrov, v otvete budut kartochki, v kotoryh est' odnovremenno vse eti
    parametry. Esli kartochki ne podhodjat po parametram zaprosa, vernetsja pustoj otvet `[]`.<br><br>

    Mozhno poluchit' otchet maksimum za poslednie 365 dnej.<br><br>

    V dannyh predyduschego perioda:
      * Dannye v `pastPeriod` ukazany za takoj zhe period, chto i v `selectedPeriod`
      * Esli data nachala  `pastPeriod` ran'she, chem god nazad ot tekuschej daty, ona budet privedena k
    vidu: `pastPeriod.start = tekuschaja data — 365 dnej`

    Mozhno ispol'zovat' paginatsiju.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 3 zaprosa | 20 sekund | 3 zaprosa |
    </div>

    Args:
        body (ProductsRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, PostSalesFunnelProductsResponse200]
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: ProductsRequest,
) -> Response[Union[Any, PostSalesFunnelProductsResponse200]]:
    r"""Statistika kartochek tovarov za period

     Metod formiruet otchet o tovarah, sravnivaja kljuchevye pokazateli — naprimer, dobavlenija v
    korzinu, zakazy i perehody v kartochku tovara — za tekuschij period s analogichnym proshlym.<br><br>

    Parametry `brandNames`,`subjectIds`, `tagIds`, `nmIds` mogut byt' pustymi `[]`, togda v otvete
    vozvraschajutsja vse kartochki prodavtsa.<br><br>

    Esli vy ukazali neskol'ko parametrov, v otvete budut kartochki, v kotoryh est' odnovremenno vse eti
    parametry. Esli kartochki ne podhodjat po parametram zaprosa, vernetsja pustoj otvet `[]`.<br><br>

    Mozhno poluchit' otchet maksimum za poslednie 365 dnej.<br><br>

    V dannyh predyduschego perioda:
      * Dannye v `pastPeriod` ukazany za takoj zhe period, chto i v `selectedPeriod`
      * Esli data nachala  `pastPeriod` ran'she, chem god nazad ot tekuschej daty, ona budet privedena k
    vidu: `pastPeriod.start = tekuschaja data — 365 dnej`

    Mozhno ispol'zovat' paginatsiju.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 3 zaprosa | 20 sekund | 3 zaprosa |
    </div>

    Args:
        body (ProductsRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, PostSalesFunnelProductsResponse200]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    body: ProductsRequest,
) -> Optional[Union[Any, PostSalesFunnelProductsResponse200]]:
    r"""Statistika kartochek tovarov za period

     Metod formiruet otchet o tovarah, sravnivaja kljuchevye pokazateli — naprimer, dobavlenija v
    korzinu, zakazy i perehody v kartochku tovara — za tekuschij period s analogichnym proshlym.<br><br>

    Parametry `brandNames`,`subjectIds`, `tagIds`, `nmIds` mogut byt' pustymi `[]`, togda v otvete
    vozvraschajutsja vse kartochki prodavtsa.<br><br>

    Esli vy ukazali neskol'ko parametrov, v otvete budut kartochki, v kotoryh est' odnovremenno vse eti
    parametry. Esli kartochki ne podhodjat po parametram zaprosa, vernetsja pustoj otvet `[]`.<br><br>

    Mozhno poluchit' otchet maksimum za poslednie 365 dnej.<br><br>

    V dannyh predyduschego perioda:
      * Dannye v `pastPeriod` ukazany za takoj zhe period, chto i v `selectedPeriod`
      * Esli data nachala  `pastPeriod` ran'she, chem god nazad ot tekuschej daty, ona budet privedena k
    vidu: `pastPeriod.start = tekuschaja data — 365 dnej`

    Mozhno ispol'zovat' paginatsiju.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 3 zaprosa | 20 sekund | 3 zaprosa |
    </div>

    Args:
        body (ProductsRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, PostSalesFunnelProductsResponse200]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
