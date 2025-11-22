from http import HTTPStatus
from typing import Any, Dict, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_api_v2_nm_report_downloads_file_download_id_response_400 import (
    GetApiV2NmReportDownloadsFileDownloadIdResponse400,
)
from ...models.get_api_v2_nm_report_downloads_file_download_id_response_403 import (
    GetApiV2NmReportDownloadsFileDownloadIdResponse403,
)
from ...types import Response


def _get_kwargs(
    download_id: str,
) -> Dict[str, Any]:
    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": "/api/v2/nm-report/downloads/file/{downloadId}".format(
            downloadId=download_id,
        ),
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[
    Union[Any, GetApiV2NmReportDownloadsFileDownloadIdResponse400, GetApiV2NmReportDownloadsFileDownloadIdResponse403]
]:
    if response.status_code == HTTPStatus.BAD_REQUEST:
        response_400 = GetApiV2NmReportDownloadsFileDownloadIdResponse400.from_dict(response.json())

        return response_400
    if response.status_code == HTTPStatus.UNAUTHORIZED:
        response_401 = cast(Any, None)
        return response_401
    if response.status_code == HTTPStatus.FORBIDDEN:
        response_403 = GetApiV2NmReportDownloadsFileDownloadIdResponse403.from_dict(response.json())

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
    Union[Any, GetApiV2NmReportDownloadsFileDownloadIdResponse400, GetApiV2NmReportDownloadsFileDownloadIdResponse403]
]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    download_id: str,
    *,
    client: AuthenticatedClient,
) -> Response[
    Union[Any, GetApiV2NmReportDownloadsFileDownloadIdResponse400, GetApiV2NmReportDownloadsFileDownloadIdResponse403]
]:
    r"""Poluchit' otchet

     Metod vozvraschaet otchet s rasshirennoj analitikoj prodavtsa po ID [zadanija na
    generatsiju](/openapi/analytics#tag/Analitika-prodavca-CSV/paths/~1api~1v2~1nm-
    report~1downloads/post).
    <br><br>
    Mozhno poluchit' otchet, kotoryj sgenerirovan za poslednie 48 chasov.<br>Otchet budet zagruzhen
    vnutri arhiva ZIP v formate CSV.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 3 zaprosa | 20 sekund | 3 zaprosa |
    </div>

    Args:
        download_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, GetApiV2NmReportDownloadsFileDownloadIdResponse400, GetApiV2NmReportDownloadsFileDownloadIdResponse403]]
    """

    kwargs = _get_kwargs(
        download_id=download_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    download_id: str,
    *,
    client: AuthenticatedClient,
) -> Optional[
    Union[Any, GetApiV2NmReportDownloadsFileDownloadIdResponse400, GetApiV2NmReportDownloadsFileDownloadIdResponse403]
]:
    r"""Poluchit' otchet

     Metod vozvraschaet otchet s rasshirennoj analitikoj prodavtsa po ID [zadanija na
    generatsiju](/openapi/analytics#tag/Analitika-prodavca-CSV/paths/~1api~1v2~1nm-
    report~1downloads/post).
    <br><br>
    Mozhno poluchit' otchet, kotoryj sgenerirovan za poslednie 48 chasov.<br>Otchet budet zagruzhen
    vnutri arhiva ZIP v formate CSV.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 3 zaprosa | 20 sekund | 3 zaprosa |
    </div>

    Args:
        download_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, GetApiV2NmReportDownloadsFileDownloadIdResponse400, GetApiV2NmReportDownloadsFileDownloadIdResponse403]
    """

    return sync_detailed(
        download_id=download_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    download_id: str,
    *,
    client: AuthenticatedClient,
) -> Response[
    Union[Any, GetApiV2NmReportDownloadsFileDownloadIdResponse400, GetApiV2NmReportDownloadsFileDownloadIdResponse403]
]:
    r"""Poluchit' otchet

     Metod vozvraschaet otchet s rasshirennoj analitikoj prodavtsa po ID [zadanija na
    generatsiju](/openapi/analytics#tag/Analitika-prodavca-CSV/paths/~1api~1v2~1nm-
    report~1downloads/post).
    <br><br>
    Mozhno poluchit' otchet, kotoryj sgenerirovan za poslednie 48 chasov.<br>Otchet budet zagruzhen
    vnutri arhiva ZIP v formate CSV.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 3 zaprosa | 20 sekund | 3 zaprosa |
    </div>

    Args:
        download_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, GetApiV2NmReportDownloadsFileDownloadIdResponse400, GetApiV2NmReportDownloadsFileDownloadIdResponse403]]
    """

    kwargs = _get_kwargs(
        download_id=download_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    download_id: str,
    *,
    client: AuthenticatedClient,
) -> Optional[
    Union[Any, GetApiV2NmReportDownloadsFileDownloadIdResponse400, GetApiV2NmReportDownloadsFileDownloadIdResponse403]
]:
    r"""Poluchit' otchet

     Metod vozvraschaet otchet s rasshirennoj analitikoj prodavtsa po ID [zadanija na
    generatsiju](/openapi/analytics#tag/Analitika-prodavca-CSV/paths/~1api~1v2~1nm-
    report~1downloads/post).
    <br><br>
    Mozhno poluchit' otchet, kotoryj sgenerirovan za poslednie 48 chasov.<br>Otchet budet zagruzhen
    vnutri arhiva ZIP v formate CSV.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 3 zaprosa | 20 sekund | 3 zaprosa |
    </div>

    Args:
        download_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, GetApiV2NmReportDownloadsFileDownloadIdResponse400, GetApiV2NmReportDownloadsFileDownloadIdResponse403]
    """

    return (
        await asyncio_detailed(
            download_id=download_id,
            client=client,
        )
    ).parsed
