from http import HTTPStatus
from typing import Any, Dict, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_object_400 import ErrorObject400
from ...models.error_object_403 import ErrorObject403
from ...models.main_request import MainRequest
from ...types import Response


def _get_kwargs(
    *,
    body: MainRequest,
) -> Dict[str, Any]:
    headers: Dict[str, Any] = {}

    _kwargs: Dict[str, Any] = {
        "method": "post",
        "url": "/api/v2/search-report/report",
    }

    _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[Any, ErrorObject400, ErrorObject403]]:
    if response.status_code == HTTPStatus.BAD_REQUEST:
        response_400 = ErrorObject400.from_dict(response.json())

        return response_400
    if response.status_code == HTTPStatus.UNAUTHORIZED:
        response_401 = cast(Any, None)
        return response_401
    if response.status_code == HTTPStatus.FORBIDDEN:
        response_403 = ErrorObject403.from_dict(response.json())

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
) -> Response[Union[Any, ErrorObject400, ErrorObject403]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: MainRequest,
) -> Response[Union[Any, ErrorObject400, ErrorObject403]]:
    r"""Osnovnaja stranitsa

     Metod formiruet nabor dannyh dlja osnovnoj stranitsy otcheta po poiskovym zaprosam s:
     - obschej informatsiej
     - pozitsijami tovarov
     - dannymi po vidimosti i perehodam v kartochku
     - dannymi dlja tablitsy po gruppam

    Dlja poluchenija dopolnitel'nyh dannyh v tablitse ispol'zujte otdel'nyj zapros dlja:
     - [paginatsii po gruppam](/openapi/analytics#tag/Poiskovye-zaprosy-po-vashim-
    tovaram/paths/~1api~1v2~1search-report~1table~1groups/post)
     - [poluchenija po tovaram v gruppe](/openapi/analytics#tag/Poiskovye-zaprosy-po-vashim-
    tovaram/paths/~1api~1v2~1search-report~1table~1details/post)

    Dopolnitel'nyj parametr vybora spiska tovarov v tablitse:
     - `positionCluster` — srednjaja pozitsija v poiske

    Parametry `includeSubstitutedSKUs` i `includeSearchTexts` ne mogut odnovremenno imet' znachenie
    `false`.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 3 zaprosa | 20 sekund | 3 zaprosa |
    </div>

    Args:
        body (MainRequest): Parametry zaprosa dlja formirovanija glavnoj stranitsy:
              - `currentPeriod` — tekuschij period
              - `pastPeriod` — predyduschij period dlja sravnenija

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, ErrorObject400, ErrorObject403]]
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
    body: MainRequest,
) -> Optional[Union[Any, ErrorObject400, ErrorObject403]]:
    r"""Osnovnaja stranitsa

     Metod formiruet nabor dannyh dlja osnovnoj stranitsy otcheta po poiskovym zaprosam s:
     - obschej informatsiej
     - pozitsijami tovarov
     - dannymi po vidimosti i perehodam v kartochku
     - dannymi dlja tablitsy po gruppam

    Dlja poluchenija dopolnitel'nyh dannyh v tablitse ispol'zujte otdel'nyj zapros dlja:
     - [paginatsii po gruppam](/openapi/analytics#tag/Poiskovye-zaprosy-po-vashim-
    tovaram/paths/~1api~1v2~1search-report~1table~1groups/post)
     - [poluchenija po tovaram v gruppe](/openapi/analytics#tag/Poiskovye-zaprosy-po-vashim-
    tovaram/paths/~1api~1v2~1search-report~1table~1details/post)

    Dopolnitel'nyj parametr vybora spiska tovarov v tablitse:
     - `positionCluster` — srednjaja pozitsija v poiske

    Parametry `includeSubstitutedSKUs` i `includeSearchTexts` ne mogut odnovremenno imet' znachenie
    `false`.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 3 zaprosa | 20 sekund | 3 zaprosa |
    </div>

    Args:
        body (MainRequest): Parametry zaprosa dlja formirovanija glavnoj stranitsy:
              - `currentPeriod` — tekuschij period
              - `pastPeriod` — predyduschij period dlja sravnenija

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, ErrorObject400, ErrorObject403]
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: MainRequest,
) -> Response[Union[Any, ErrorObject400, ErrorObject403]]:
    r"""Osnovnaja stranitsa

     Metod formiruet nabor dannyh dlja osnovnoj stranitsy otcheta po poiskovym zaprosam s:
     - obschej informatsiej
     - pozitsijami tovarov
     - dannymi po vidimosti i perehodam v kartochku
     - dannymi dlja tablitsy po gruppam

    Dlja poluchenija dopolnitel'nyh dannyh v tablitse ispol'zujte otdel'nyj zapros dlja:
     - [paginatsii po gruppam](/openapi/analytics#tag/Poiskovye-zaprosy-po-vashim-
    tovaram/paths/~1api~1v2~1search-report~1table~1groups/post)
     - [poluchenija po tovaram v gruppe](/openapi/analytics#tag/Poiskovye-zaprosy-po-vashim-
    tovaram/paths/~1api~1v2~1search-report~1table~1details/post)

    Dopolnitel'nyj parametr vybora spiska tovarov v tablitse:
     - `positionCluster` — srednjaja pozitsija v poiske

    Parametry `includeSubstitutedSKUs` i `includeSearchTexts` ne mogut odnovremenno imet' znachenie
    `false`.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 3 zaprosa | 20 sekund | 3 zaprosa |
    </div>

    Args:
        body (MainRequest): Parametry zaprosa dlja formirovanija glavnoj stranitsy:
              - `currentPeriod` — tekuschij period
              - `pastPeriod` — predyduschij period dlja sravnenija

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, ErrorObject400, ErrorObject403]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    body: MainRequest,
) -> Optional[Union[Any, ErrorObject400, ErrorObject403]]:
    r"""Osnovnaja stranitsa

     Metod formiruet nabor dannyh dlja osnovnoj stranitsy otcheta po poiskovym zaprosam s:
     - obschej informatsiej
     - pozitsijami tovarov
     - dannymi po vidimosti i perehodam v kartochku
     - dannymi dlja tablitsy po gruppam

    Dlja poluchenija dopolnitel'nyh dannyh v tablitse ispol'zujte otdel'nyj zapros dlja:
     - [paginatsii po gruppam](/openapi/analytics#tag/Poiskovye-zaprosy-po-vashim-
    tovaram/paths/~1api~1v2~1search-report~1table~1groups/post)
     - [poluchenija po tovaram v gruppe](/openapi/analytics#tag/Poiskovye-zaprosy-po-vashim-
    tovaram/paths/~1api~1v2~1search-report~1table~1details/post)

    Dopolnitel'nyj parametr vybora spiska tovarov v tablitse:
     - `positionCluster` — srednjaja pozitsija v poiske

    Parametry `includeSubstitutedSKUs` i `includeSearchTexts` ne mogut odnovremenno imet' znachenie
    `false`.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 3 zaprosa | 20 sekund | 3 zaprosa |
    </div>

    Args:
        body (MainRequest): Parametry zaprosa dlja formirovanija glavnoj stranitsy:
              - `currentPeriod` — tekuschij period
              - `pastPeriod` — predyduschij period dlja sravnenija

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, ErrorObject400, ErrorObject403]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
