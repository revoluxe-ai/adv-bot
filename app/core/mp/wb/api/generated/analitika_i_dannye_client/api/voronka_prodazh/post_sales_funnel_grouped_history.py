from http import HTTPStatus
from typing import Any, Dict, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.grouped_history_request import GroupedHistoryRequest
from ...models.post_sales_funnel_grouped_history_response_200 import PostSalesFunnelGroupedHistoryResponse200
from ...types import Response


def _get_kwargs(
    *,
    body: GroupedHistoryRequest,
) -> Dict[str, Any]:
    headers: Dict[str, Any] = {}

    _kwargs: Dict[str, Any] = {
        "method": "post",
        "url": "/api/analytics/v3/sales-funnel/grouped/history",
    }

    _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[Any, PostSalesFunnelGroupedHistoryResponse200]]:
    if response.status_code == HTTPStatus.OK:
        response_200 = PostSalesFunnelGroupedHistoryResponse200.from_dict(response.json())

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
) -> Response[Union[Any, PostSalesFunnelGroupedHistoryResponse200]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: GroupedHistoryRequest,
) -> Response[Union[Any, PostSalesFunnelGroupedHistoryResponse200]]:
    r"""Statistika grupp kartochek tovarov po dnjam

     Metod vozvraschaet statistiku kartochek tovarov po dnjam ili nedeljam. Kartochki tovarov
    sgruppirovany po predmetam, brendam i jarlykam. Dostupny dannye po dobavlenijam v korzinu, zakazam,
    perehodam v kartochku tovara i tak dalee.<br><br>

    Parametry `brandNames`, `subjectIds`, `tagIds` mogut byt' pustymi `[]`, togda gruppirovka proishodit
    po vsem kartochkam prodavtsa.<br><br>

    Proizvedenie kolichestva predmetov, brendov, jarlykov v zaprose mozhet byt' ne bol'she 16. Naprimer,
    4 brenda i 4 predmeta ili 2 predmeta, 2 jarlyka i 4 brenda.<br><br>

    Mozhno poluchit' dannye maksimum za poslednjuju nedelju.

    <div class=\"description_important\">
      Chtoby poluchat' otchety za period do goda, ispol'zujte metody <a
    href=\"/openapi/analytics#tag/Analitika-prodavca-CSV\">Analitika prodavtsa CSV</a>. Eti metody
    dostupny tol'ko s podpiskoj na <a
    href='https://seller.wildberries.ru/monetization/jam'>rasshirennuju analitiku Dzhem</a>
    </div>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 3 zaprosa | 20 sekund | 3 zaprosa |
    </div>

    Args:
        body (GroupedHistoryRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, PostSalesFunnelGroupedHistoryResponse200]]
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
    body: GroupedHistoryRequest,
) -> Optional[Union[Any, PostSalesFunnelGroupedHistoryResponse200]]:
    r"""Statistika grupp kartochek tovarov po dnjam

     Metod vozvraschaet statistiku kartochek tovarov po dnjam ili nedeljam. Kartochki tovarov
    sgruppirovany po predmetam, brendam i jarlykam. Dostupny dannye po dobavlenijam v korzinu, zakazam,
    perehodam v kartochku tovara i tak dalee.<br><br>

    Parametry `brandNames`, `subjectIds`, `tagIds` mogut byt' pustymi `[]`, togda gruppirovka proishodit
    po vsem kartochkam prodavtsa.<br><br>

    Proizvedenie kolichestva predmetov, brendov, jarlykov v zaprose mozhet byt' ne bol'she 16. Naprimer,
    4 brenda i 4 predmeta ili 2 predmeta, 2 jarlyka i 4 brenda.<br><br>

    Mozhno poluchit' dannye maksimum za poslednjuju nedelju.

    <div class=\"description_important\">
      Chtoby poluchat' otchety za period do goda, ispol'zujte metody <a
    href=\"/openapi/analytics#tag/Analitika-prodavca-CSV\">Analitika prodavtsa CSV</a>. Eti metody
    dostupny tol'ko s podpiskoj na <a
    href='https://seller.wildberries.ru/monetization/jam'>rasshirennuju analitiku Dzhem</a>
    </div>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 3 zaprosa | 20 sekund | 3 zaprosa |
    </div>

    Args:
        body (GroupedHistoryRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, PostSalesFunnelGroupedHistoryResponse200]
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: GroupedHistoryRequest,
) -> Response[Union[Any, PostSalesFunnelGroupedHistoryResponse200]]:
    r"""Statistika grupp kartochek tovarov po dnjam

     Metod vozvraschaet statistiku kartochek tovarov po dnjam ili nedeljam. Kartochki tovarov
    sgruppirovany po predmetam, brendam i jarlykam. Dostupny dannye po dobavlenijam v korzinu, zakazam,
    perehodam v kartochku tovara i tak dalee.<br><br>

    Parametry `brandNames`, `subjectIds`, `tagIds` mogut byt' pustymi `[]`, togda gruppirovka proishodit
    po vsem kartochkam prodavtsa.<br><br>

    Proizvedenie kolichestva predmetov, brendov, jarlykov v zaprose mozhet byt' ne bol'she 16. Naprimer,
    4 brenda i 4 predmeta ili 2 predmeta, 2 jarlyka i 4 brenda.<br><br>

    Mozhno poluchit' dannye maksimum za poslednjuju nedelju.

    <div class=\"description_important\">
      Chtoby poluchat' otchety za period do goda, ispol'zujte metody <a
    href=\"/openapi/analytics#tag/Analitika-prodavca-CSV\">Analitika prodavtsa CSV</a>. Eti metody
    dostupny tol'ko s podpiskoj na <a
    href='https://seller.wildberries.ru/monetization/jam'>rasshirennuju analitiku Dzhem</a>
    </div>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 3 zaprosa | 20 sekund | 3 zaprosa |
    </div>

    Args:
        body (GroupedHistoryRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, PostSalesFunnelGroupedHistoryResponse200]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    body: GroupedHistoryRequest,
) -> Optional[Union[Any, PostSalesFunnelGroupedHistoryResponse200]]:
    r"""Statistika grupp kartochek tovarov po dnjam

     Metod vozvraschaet statistiku kartochek tovarov po dnjam ili nedeljam. Kartochki tovarov
    sgruppirovany po predmetam, brendam i jarlykam. Dostupny dannye po dobavlenijam v korzinu, zakazam,
    perehodam v kartochku tovara i tak dalee.<br><br>

    Parametry `brandNames`, `subjectIds`, `tagIds` mogut byt' pustymi `[]`, togda gruppirovka proishodit
    po vsem kartochkam prodavtsa.<br><br>

    Proizvedenie kolichestva predmetov, brendov, jarlykov v zaprose mozhet byt' ne bol'she 16. Naprimer,
    4 brenda i 4 predmeta ili 2 predmeta, 2 jarlyka i 4 brenda.<br><br>

    Mozhno poluchit' dannye maksimum za poslednjuju nedelju.

    <div class=\"description_important\">
      Chtoby poluchat' otchety za period do goda, ispol'zujte metody <a
    href=\"/openapi/analytics#tag/Analitika-prodavca-CSV\">Analitika prodavtsa CSV</a>. Eti metody
    dostupny tol'ko s podpiskoj na <a
    href='https://seller.wildberries.ru/monetization/jam'>rasshirennuju analitiku Dzhem</a>
    </div>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 3 zaprosa | 20 sekund | 3 zaprosa |
    </div>

    Args:
        body (GroupedHistoryRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, PostSalesFunnelGroupedHistoryResponse200]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
