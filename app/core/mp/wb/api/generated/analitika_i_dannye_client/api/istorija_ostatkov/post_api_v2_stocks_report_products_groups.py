from http import HTTPStatus
from typing import Any, Dict, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_object_400 import ErrorObject400
from ...models.error_object_403 import ErrorObject403
from ...models.post_api_v2_stocks_report_products_groups_response_200 import (
    PostApiV2StocksReportProductsGroupsResponse200,
)
from ...models.table_group_request_st import TableGroupRequestSt
from ...types import Response


def _get_kwargs(
    *,
    body: TableGroupRequestSt,
) -> Dict[str, Any]:
    headers: Dict[str, Any] = {}

    _kwargs: Dict[str, Any] = {
        "method": "post",
        "url": "/api/v2/stocks-report/products/groups",
    }

    _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[Any, ErrorObject400, ErrorObject403, PostApiV2StocksReportProductsGroupsResponse200]]:
    if response.status_code == HTTPStatus.OK:
        response_200 = PostApiV2StocksReportProductsGroupsResponse200.from_dict(response.json())

        return response_200
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
) -> Response[Union[Any, ErrorObject400, ErrorObject403, PostApiV2StocksReportProductsGroupsResponse200]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: TableGroupRequestSt,
) -> Response[Union[Any, ErrorObject400, ErrorObject403, PostApiV2StocksReportProductsGroupsResponse200]]:
    r"""Dannye po gruppam

     Metod formiruet nabor dannyh ob ostatkah po gruppam tovarov.
    <br><br>
    Gruppa tovarov opisyvaetsja kortezhem `subjectID, brandName, tagID`.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 3 zaprosa | 20 sekund | 3 zaprosa |
    </div>

    Args:
        body (TableGroupRequestSt):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, ErrorObject400, ErrorObject403, PostApiV2StocksReportProductsGroupsResponse200]]
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
    body: TableGroupRequestSt,
) -> Optional[Union[Any, ErrorObject400, ErrorObject403, PostApiV2StocksReportProductsGroupsResponse200]]:
    r"""Dannye po gruppam

     Metod formiruet nabor dannyh ob ostatkah po gruppam tovarov.
    <br><br>
    Gruppa tovarov opisyvaetsja kortezhem `subjectID, brandName, tagID`.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 3 zaprosa | 20 sekund | 3 zaprosa |
    </div>

    Args:
        body (TableGroupRequestSt):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, ErrorObject400, ErrorObject403, PostApiV2StocksReportProductsGroupsResponse200]
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: TableGroupRequestSt,
) -> Response[Union[Any, ErrorObject400, ErrorObject403, PostApiV2StocksReportProductsGroupsResponse200]]:
    r"""Dannye po gruppam

     Metod formiruet nabor dannyh ob ostatkah po gruppam tovarov.
    <br><br>
    Gruppa tovarov opisyvaetsja kortezhem `subjectID, brandName, tagID`.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 3 zaprosa | 20 sekund | 3 zaprosa |
    </div>

    Args:
        body (TableGroupRequestSt):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, ErrorObject400, ErrorObject403, PostApiV2StocksReportProductsGroupsResponse200]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    body: TableGroupRequestSt,
) -> Optional[Union[Any, ErrorObject400, ErrorObject403, PostApiV2StocksReportProductsGroupsResponse200]]:
    r"""Dannye po gruppam

     Metod formiruet nabor dannyh ob ostatkah po gruppam tovarov.
    <br><br>
    Gruppa tovarov opisyvaetsja kortezhem `subjectID, brandName, tagID`.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 3 zaprosa | 20 sekund | 3 zaprosa |
    </div>

    Args:
        body (TableGroupRequestSt):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, ErrorObject400, ErrorObject403, PostApiV2StocksReportProductsGroupsResponse200]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
