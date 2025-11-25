from http import HTTPStatus
from typing import Any, Dict, List, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_api_v2_nm_report_downloads_response_400 import GetApiV2NmReportDownloadsResponse400
from ...models.get_api_v2_nm_report_downloads_response_403 import GetApiV2NmReportDownloadsResponse403
from ...models.nm_report_get_reports_response import NmReportGetReportsResponse
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    filterdownload_ids: Union[Unset, List[str]] = UNSET,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {}

    json_filterdownload_ids: Union[Unset, List[str]] = UNSET
    if not isinstance(filterdownload_ids, Unset):
        json_filterdownload_ids = filterdownload_ids

    params["filter[downloadIds]"] = json_filterdownload_ids

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": "/api/v2/nm-report/downloads",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[
    Union[Any, GetApiV2NmReportDownloadsResponse400, GetApiV2NmReportDownloadsResponse403, NmReportGetReportsResponse]
]:
    if response.status_code == HTTPStatus.OK:
        response_200 = NmReportGetReportsResponse.from_dict(response.json())

        return response_200
    if response.status_code == HTTPStatus.BAD_REQUEST:
        response_400 = GetApiV2NmReportDownloadsResponse400.from_dict(response.json())

        return response_400
    if response.status_code == HTTPStatus.UNAUTHORIZED:
        response_401 = cast(Any, None)
        return response_401
    if response.status_code == HTTPStatus.FORBIDDEN:
        response_403 = GetApiV2NmReportDownloadsResponse403.from_dict(response.json())

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
    Union[Any, GetApiV2NmReportDownloadsResponse400, GetApiV2NmReportDownloadsResponse403, NmReportGetReportsResponse]
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
    filterdownload_ids: Union[Unset, List[str]] = UNSET,
) -> Response[
    Union[Any, GetApiV2NmReportDownloadsResponse400, GetApiV2NmReportDownloadsResponse403, NmReportGetReportsResponse]
]:
    r"""Poluchit' spisok otchetov

     Metod vozvraschaet spisok otchetov s rasshirennoj analitikoj prodavtsa. Otvet soderzhit ID
    [sozdannyh otchetov](/openapi/analytics#tag/Analitika-prodavca-CSV/paths/~1api~1v2~1nm-
    report~1downloads/post) i statusy generatsii.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 3 zaprosa | 20 sekund | 3 zaprosa |
    </div>

    Args:
        filterdownload_ids (Union[Unset, List[str]]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, GetApiV2NmReportDownloadsResponse400, GetApiV2NmReportDownloadsResponse403, NmReportGetReportsResponse]]
    """

    kwargs = _get_kwargs(
        filterdownload_ids=filterdownload_ids,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    filterdownload_ids: Union[Unset, List[str]] = UNSET,
) -> Optional[
    Union[Any, GetApiV2NmReportDownloadsResponse400, GetApiV2NmReportDownloadsResponse403, NmReportGetReportsResponse]
]:
    r"""Poluchit' spisok otchetov

     Metod vozvraschaet spisok otchetov s rasshirennoj analitikoj prodavtsa. Otvet soderzhit ID
    [sozdannyh otchetov](/openapi/analytics#tag/Analitika-prodavca-CSV/paths/~1api~1v2~1nm-
    report~1downloads/post) i statusy generatsii.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 3 zaprosa | 20 sekund | 3 zaprosa |
    </div>

    Args:
        filterdownload_ids (Union[Unset, List[str]]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, GetApiV2NmReportDownloadsResponse400, GetApiV2NmReportDownloadsResponse403, NmReportGetReportsResponse]
    """

    return sync_detailed(
        client=client,
        filterdownload_ids=filterdownload_ids,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    filterdownload_ids: Union[Unset, List[str]] = UNSET,
) -> Response[
    Union[Any, GetApiV2NmReportDownloadsResponse400, GetApiV2NmReportDownloadsResponse403, NmReportGetReportsResponse]
]:
    r"""Poluchit' spisok otchetov

     Metod vozvraschaet spisok otchetov s rasshirennoj analitikoj prodavtsa. Otvet soderzhit ID
    [sozdannyh otchetov](/openapi/analytics#tag/Analitika-prodavca-CSV/paths/~1api~1v2~1nm-
    report~1downloads/post) i statusy generatsii.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 3 zaprosa | 20 sekund | 3 zaprosa |
    </div>

    Args:
        filterdownload_ids (Union[Unset, List[str]]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, GetApiV2NmReportDownloadsResponse400, GetApiV2NmReportDownloadsResponse403, NmReportGetReportsResponse]]
    """

    kwargs = _get_kwargs(
        filterdownload_ids=filterdownload_ids,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    filterdownload_ids: Union[Unset, List[str]] = UNSET,
) -> Optional[
    Union[Any, GetApiV2NmReportDownloadsResponse400, GetApiV2NmReportDownloadsResponse403, NmReportGetReportsResponse]
]:
    r"""Poluchit' spisok otchetov

     Metod vozvraschaet spisok otchetov s rasshirennoj analitikoj prodavtsa. Otvet soderzhit ID
    [sozdannyh otchetov](/openapi/analytics#tag/Analitika-prodavca-CSV/paths/~1api~1v2~1nm-
    report~1downloads/post) i statusy generatsii.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 3 zaprosa | 20 sekund | 3 zaprosa |
    </div>

    Args:
        filterdownload_ids (Union[Unset, List[str]]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, GetApiV2NmReportDownloadsResponse400, GetApiV2NmReportDownloadsResponse403, NmReportGetReportsResponse]
    """

    return (
        await asyncio_detailed(
            client=client,
            filterdownload_ids=filterdownload_ids,
        )
    ).parsed
