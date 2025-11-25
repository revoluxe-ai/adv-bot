from http import HTTPStatus
from typing import Any, Dict, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.nm_report_retry_report_request import NmReportRetryReportRequest
from ...models.nm_report_retry_report_response import NmReportRetryReportResponse
from ...models.post_api_v2_nm_report_downloads_retry_response_400 import PostApiV2NmReportDownloadsRetryResponse400
from ...models.post_api_v2_nm_report_downloads_retry_response_403 import PostApiV2NmReportDownloadsRetryResponse403
from ...types import Response


def _get_kwargs(
    *,
    body: NmReportRetryReportRequest,
) -> Dict[str, Any]:
    headers: Dict[str, Any] = {}

    _kwargs: Dict[str, Any] = {
        "method": "post",
        "url": "/api/v2/nm-report/downloads/retry",
    }

    _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[
    Union[
        Any,
        NmReportRetryReportResponse,
        PostApiV2NmReportDownloadsRetryResponse400,
        PostApiV2NmReportDownloadsRetryResponse403,
    ]
]:
    if response.status_code == HTTPStatus.OK:
        response_200 = NmReportRetryReportResponse.from_dict(response.json())

        return response_200
    if response.status_code == HTTPStatus.BAD_REQUEST:
        response_400 = PostApiV2NmReportDownloadsRetryResponse400.from_dict(response.json())

        return response_400
    if response.status_code == HTTPStatus.UNAUTHORIZED:
        response_401 = cast(Any, None)
        return response_401
    if response.status_code == HTTPStatus.FORBIDDEN:
        response_403 = PostApiV2NmReportDownloadsRetryResponse403.from_dict(response.json())

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
) -> Response[
    Union[
        Any,
        NmReportRetryReportResponse,
        PostApiV2NmReportDownloadsRetryResponse400,
        PostApiV2NmReportDownloadsRetryResponse403,
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
    client: AuthenticatedClient,
    body: NmReportRetryReportRequest,
) -> Response[
    Union[
        Any,
        NmReportRetryReportResponse,
        PostApiV2NmReportDownloadsRetryResponse400,
        PostApiV2NmReportDownloadsRetryResponse403,
    ]
]:
    r"""Sgenerirovat' otchet povtorno

     Metod sozdaet povtornoe [zadanie na generatsiju](/openapi/analytics#tag/Analitika-prodavca-
    CSV/paths/~1api~1v2~1nm-report~1downloads/post) otcheta s rasshirennoj analitikoj prodavtsa.
    Neobhodimo, esli pri generatsii otcheta vy [poluchili status](/openapi/analytics#tag/Analitika-
    prodavca-CSV/paths/~1api~1v2~1nm-report~1downloads/get) `FAILED`.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 3 zaprosa | 20 sekund | 3 zaprosa |
    </div>

    Args:
        body (NmReportRetryReportRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, NmReportRetryReportResponse, PostApiV2NmReportDownloadsRetryResponse400, PostApiV2NmReportDownloadsRetryResponse403]]
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
    body: NmReportRetryReportRequest,
) -> Optional[
    Union[
        Any,
        NmReportRetryReportResponse,
        PostApiV2NmReportDownloadsRetryResponse400,
        PostApiV2NmReportDownloadsRetryResponse403,
    ]
]:
    r"""Sgenerirovat' otchet povtorno

     Metod sozdaet povtornoe [zadanie na generatsiju](/openapi/analytics#tag/Analitika-prodavca-
    CSV/paths/~1api~1v2~1nm-report~1downloads/post) otcheta s rasshirennoj analitikoj prodavtsa.
    Neobhodimo, esli pri generatsii otcheta vy [poluchili status](/openapi/analytics#tag/Analitika-
    prodavca-CSV/paths/~1api~1v2~1nm-report~1downloads/get) `FAILED`.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 3 zaprosa | 20 sekund | 3 zaprosa |
    </div>

    Args:
        body (NmReportRetryReportRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, NmReportRetryReportResponse, PostApiV2NmReportDownloadsRetryResponse400, PostApiV2NmReportDownloadsRetryResponse403]
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: NmReportRetryReportRequest,
) -> Response[
    Union[
        Any,
        NmReportRetryReportResponse,
        PostApiV2NmReportDownloadsRetryResponse400,
        PostApiV2NmReportDownloadsRetryResponse403,
    ]
]:
    r"""Sgenerirovat' otchet povtorno

     Metod sozdaet povtornoe [zadanie na generatsiju](/openapi/analytics#tag/Analitika-prodavca-
    CSV/paths/~1api~1v2~1nm-report~1downloads/post) otcheta s rasshirennoj analitikoj prodavtsa.
    Neobhodimo, esli pri generatsii otcheta vy [poluchili status](/openapi/analytics#tag/Analitika-
    prodavca-CSV/paths/~1api~1v2~1nm-report~1downloads/get) `FAILED`.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 3 zaprosa | 20 sekund | 3 zaprosa |
    </div>

    Args:
        body (NmReportRetryReportRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, NmReportRetryReportResponse, PostApiV2NmReportDownloadsRetryResponse400, PostApiV2NmReportDownloadsRetryResponse403]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: NmReportRetryReportRequest,
) -> Optional[
    Union[
        Any,
        NmReportRetryReportResponse,
        PostApiV2NmReportDownloadsRetryResponse400,
        PostApiV2NmReportDownloadsRetryResponse403,
    ]
]:
    r"""Sgenerirovat' otchet povtorno

     Metod sozdaet povtornoe [zadanie na generatsiju](/openapi/analytics#tag/Analitika-prodavca-
    CSV/paths/~1api~1v2~1nm-report~1downloads/post) otcheta s rasshirennoj analitikoj prodavtsa.
    Neobhodimo, esli pri generatsii otcheta vy [poluchili status](/openapi/analytics#tag/Analitika-
    prodavca-CSV/paths/~1api~1v2~1nm-report~1downloads/get) `FAILED`.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 3 zaprosa | 20 sekund | 3 zaprosa |
    </div>

    Args:
        body (NmReportRetryReportRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, NmReportRetryReportResponse, PostApiV2NmReportDownloadsRetryResponse400, PostApiV2NmReportDownloadsRetryResponse403]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
