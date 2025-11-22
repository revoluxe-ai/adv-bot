from http import HTTPStatus
from typing import Any, Dict, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.nm_report_detail_request import NmReportDetailRequest
from ...models.nm_report_detail_response import NmReportDetailResponse
from ...models.response_error_type_0 import ResponseErrorType0
from ...types import Response


def _get_kwargs(
    *,
    body: NmReportDetailRequest,
) -> Dict[str, Any]:
    headers: Dict[str, Any] = {}

    _kwargs: Dict[str, Any] = {
        "method": "post",
        "url": "/api/v2/nm-report/detail",
    }

    _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[Any, NmReportDetailResponse, Union["ResponseErrorType0", None]]]:
    if response.status_code == HTTPStatus.OK:
        response_200 = NmReportDetailResponse.from_dict(response.json())

        return response_200
    if response.status_code == HTTPStatus.BAD_REQUEST:

        def _parse_response_400(data: object) -> Union["ResponseErrorType0", None]:
            if data is None:
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemasresponse_error_type_0 = ResponseErrorType0.from_dict(data)

                return componentsschemasresponse_error_type_0
            except:  # noqa: E722
                pass
            return cast(Union["ResponseErrorType0", None], data)

        response_400 = _parse_response_400(response.json())

        return response_400
    if response.status_code == HTTPStatus.UNAUTHORIZED:
        response_401 = cast(Any, None)
        return response_401
    if response.status_code == HTTPStatus.FORBIDDEN:

        def _parse_response_403(data: object) -> Union["ResponseErrorType0", None]:
            if data is None:
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemasresponse_error_type_0 = ResponseErrorType0.from_dict(data)

                return componentsschemasresponse_error_type_0
            except:  # noqa: E722
                pass
            return cast(Union["ResponseErrorType0", None], data)

        response_403 = _parse_response_403(response.json())

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
) -> Response[Union[Any, NmReportDetailResponse, Union["ResponseErrorType0", None]]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: NmReportDetailRequest,
) -> Response[Union[Any, NmReportDetailResponse, Union["ResponseErrorType0", None]]]:
    r"""Statistika kartochek tovarov za period

     Dannyj metod ustarel. On budet udalen [9 dekabrja](https://dev.wildberries.ru/release-notes?id=355)

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 3 zaprosa | 20 sekund | 3 zaprosa |
    </div>

    Args:
        body (NmReportDetailRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, NmReportDetailResponse, Union['ResponseErrorType0', None]]]
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
    body: NmReportDetailRequest,
) -> Optional[Union[Any, NmReportDetailResponse, Union["ResponseErrorType0", None]]]:
    r"""Statistika kartochek tovarov za period

     Dannyj metod ustarel. On budet udalen [9 dekabrja](https://dev.wildberries.ru/release-notes?id=355)

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 3 zaprosa | 20 sekund | 3 zaprosa |
    </div>

    Args:
        body (NmReportDetailRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, NmReportDetailResponse, Union['ResponseErrorType0', None]]
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: NmReportDetailRequest,
) -> Response[Union[Any, NmReportDetailResponse, Union["ResponseErrorType0", None]]]:
    r"""Statistika kartochek tovarov za period

     Dannyj metod ustarel. On budet udalen [9 dekabrja](https://dev.wildberries.ru/release-notes?id=355)

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 3 zaprosa | 20 sekund | 3 zaprosa |
    </div>

    Args:
        body (NmReportDetailRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, NmReportDetailResponse, Union['ResponseErrorType0', None]]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    body: NmReportDetailRequest,
) -> Optional[Union[Any, NmReportDetailResponse, Union["ResponseErrorType0", None]]]:
    r"""Statistika kartochek tovarov za period

     Dannyj metod ustarel. On budet udalen [9 dekabrja](https://dev.wildberries.ru/release-notes?id=355)

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 3 zaprosa | 20 sekund | 3 zaprosa |
    </div>

    Args:
        body (NmReportDetailRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, NmReportDetailResponse, Union['ResponseErrorType0', None]]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
